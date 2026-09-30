"""
Alpha-Guard — Forensic AI Analyzer
====================================
Intelligence layer using Google Gemini API to analyze 10-K filing text.

Capabilities:
  1. Hedging & Evasion Detection — whole-word lexicon density on the MD&A
  2. Sentiment & red-flag extraction via Gemini — quotes verified against the filing
  3. Sentiment Gap Detection — divergence between narrative and Z-Score
  4. Truth Score — 100 minus transparent penalties (see compute_truth_score)
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from config import GEMINI_MODEL, gemini_api_key
from models import (
    FinancialData,
    ForensicRequest,
    ForensicResult,
    ForensicAuditResponse,
    LinguisticAnalysis,
    RedFlag,
    TruthScoreBreakdown,
    ZScoreResult,
)
from security import rate_limit

router = APIRouter(prefix="/api/risk", tags=["Forensic AI Analysis"])

# Below this many MD&A words there is not enough narrative to judge credibility
MIN_WORDS_FOR_ANALYSIS = 300

INTERNATIONAL_CALL_NOTE = (
    "Earnings call transcripts are available for US-listed companies only "
    "(Alpha Vantage and SEC filings); this analysis is not available for this exchange."
)
# Same cap as a 10-K section, for the earnings-release fallback
MAX_LANGUAGE_CHARS = 40_000

# ──────────────────────────────────────────────
#  Hedging & Evasion Lexicon
# ──────────────────────────────────────────────
# "risk"/"risks" are deliberately absent: discussing risk is mandatory
# disclosure, not hedging.

HEDGING_WORDS = [
    "uncertain", "uncertainty", "might", "potentially", "could",
    "may", "approximately", "subject to", "possible", "possibly",
    "expected", "anticipate", "believe", "estimate", "intend",
    "likely", "unlikely", "probable", "contingent", "assume",
    "assumed", "cannot assure", "no assurance",
    "there can be no", "forward-looking", "cautionary",
]

EVASION_PHRASES = [
    "we believe", "management believes", "in our opinion",
    "to our knowledge", "as far as we know", "we expect",
    "we anticipate", "we are not aware", "we cannot predict",
    "results may vary", "past performance", "no guarantee",
    "subject to change", "among other things", "from time to time",
]


def _phrase_pattern(phrase: str) -> re.Pattern:
    """Whole-word, whitespace-tolerant, case-insensitive matcher."""
    words = [re.escape(w) for w in phrase.split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"\b", re.IGNORECASE)


_HEDGING_PATTERNS = [(w, _phrase_pattern(w)) for w in HEDGING_WORDS]
_EVASION_PATTERNS = [(p, _phrase_pattern(p)) for p in EVASION_PHRASES]


def _word_count(text: str) -> int:
    return len(text.split())


def _remove_evasion_phrases(text: str) -> str:
    """Blank out evasion phrases so their words are not also counted as hedging."""
    for _, pattern in _EVASION_PATTERNS:
        text = pattern.sub(" ", text)
    return text


def compute_hedging_score(text: str) -> tuple[float, list[str]]:
    """Analyze text for hedging language density.

    Evasion phrases ("we believe") are excluded first so each phrase is
    counted once, under evasion.

    Returns:
        Tuple of (hedging_score 0-100, list of hedging words found)
    """
    total_words = _word_count(text) or 1
    remaining = _remove_evasion_phrases(text)

    found_words = []
    hedge_count = 0
    for hedge, pattern in _HEDGING_PATTERNS:
        occurrences = len(pattern.findall(remaining))
        if occurrences > 0:
            hedge_count += occurrences
            found_words.append(f"{hedge} ({occurrences}x)")

    # Hedging density: normalize by total words, scale to 0-100
    # Typical MD&A has ~1-2% hedging density; 5% is extreme
    density = (hedge_count / total_words) * 100
    score = min(100, density * 20)  # Scale so 5% density = 100

    return round(score, 1), found_words


# Financial tone lexicon, a subset in the spirit of Loughran & McDonald (2011):
# words whose tone is unambiguous in 10-K prose.
POSITIVE_WORDS = """
able abundance achieve achieved achievement achievements advancement advancements advantage advantages
attractive beneficial benefit benefited best better boost boosted breakthrough efficient efficiencies enhance
enhanced enhancement excellent exceptional favorable favorably gain gained gains good great greater highest
improve improved improvement improvements improving innovative leading opportunities opportunity optimistic
outperform outperformed pleased positive profitable profitability progress rebound record strength strengthen
strengthened strong stronger strongest success successful successfully superior surpass tremendous upturn valuable
""".split()

NEGATIVE_WORDS = """
adverse adversely breach challenging closure closures costly damage damages decline declined declines
declining default defaults deficit delay delayed delays deteriorate deteriorated deterioration difficult difficulties
disruption disruptions downturn fail failed failure failures harm harmed impairment impairments impaired inability
insufficient investigation lawsuit lawsuits litigation loss losses negative negatively penalties penalty recall
recalls restructuring shortfall slowdown termination terminated unable unfavorable unprofitable volatility weak
weaker weakness weaknesses writedown writedowns
""".split()

_POSITIVE_RE = re.compile(r"\b(?:" + "|".join(POSITIVE_WORDS) + r")\b", re.IGNORECASE)
_NEGATIVE_RE = re.compile(r"\b(?:" + "|".join(NEGATIVE_WORDS) + r")\b", re.IGNORECASE)

# Calibrated on large-cap MD&As: net tone ranged from -0.55 (BA) and -0.34 (F)
# to +0.48 (TSLA, WMT), median about -0.05.
BULLISH_TONE = 0.30
BEARISH_TONE = -0.30


def compute_lexicon_tone(text: str) -> tuple[str, float | None]:
    """Sentiment from positive/negative financial word counts.

    Returns:
        (sentiment, net_tone) where net_tone = (pos - neg) / (pos + neg),
        or ("unknown", None) if the text has too few tone words to judge.
    """
    positive = len(_POSITIVE_RE.findall(text))
    negative = len(_NEGATIVE_RE.findall(text))
    if positive + negative < 10:
        return "unknown", None
    net = (positive - negative) / (positive + negative)
    if net >= BULLISH_TONE:
        sentiment = "bullish"
    elif net <= BEARISH_TONE:
        sentiment = "bearish"
    else:
        sentiment = "neutral"
    return sentiment, round(net, 3)


def compute_evasion_score(text: str) -> float:
    """Analyze text for evasive language patterns.

    Returns:
        Evasion score 0-100
    """
    total_words = _word_count(text) or 1
    evasion_count = sum(len(pattern.findall(text)) for _, pattern in _EVASION_PATTERNS)

    density = (evasion_count / total_words) * 100
    score = min(100, density * 30)

    return round(score, 1)


# ──────────────────────────────────────────────
#  Gemini API Integration
# ──────────────────────────────────────────────

GEMINI_ANALYSIS_PROMPT = """You are a forensic financial analyst AI. Analyze the following Management Discussion & Analysis (MD&A) text from a 10-K SEC filing.

Your task:
1. Determine the overall SENTIMENT of management's narrative: "bullish", "neutral", or "bearish"
2. Rate your confidence in this sentiment classification (0.0 to 1.0)
3. Identify up to 5 of the most suspicious or misleading sentences — those that:
   - Use excessive hedging or vague language to obscure bad news
   - Make optimistic claims not supported by typical financial fundamentals
   - Contradict common financial knowledge or seem evasive
   - Use complex language to hide simple negative facts
   If the text is plain and forthright, return fewer sentences or none. Do not invent issues.

For each suspicious sentence, provide:
- The exact sentence, copied verbatim from the text
- A category: "hedging", "evasion", "sentiment_gap", or "inconsistency"
- A severity rating (1-10, where 10 is most severe)
- A brief explanation of why it's suspicious

Respond ONLY with valid JSON in this exact format:
{
  "sentiment": "bullish" | "neutral" | "bearish",
  "confidence": 0.0-1.0,
  "suspicious_sentences": [
    {
      "sentence": "exact quote",
      "category": "hedging|evasion|sentiment_gap|inconsistency",
      "severity": 1-10,
      "explanation": "why this is suspicious"
    }
  ]
}

MD&A TEXT:
"""

GEMINI_TIMEOUT_SECONDS = 90
GEMINI_RETRY_DELAY_SECONDS = 3.0
GEMINI_FALLBACK_MODEL = "gemini-flash-lite-latest"
VALID_SENTIMENTS = {"bullish", "neutral", "bearish"}
VALID_CATEGORIES = {"hedging", "evasion", "sentiment_gap", "inconsistency"}


def _parse_gemini_json(response_text: str) -> dict:
    text = response_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Gemini response is not a JSON object")
    return data


def describe_gemini_error(error: Exception) -> str:
    """Turn a Gemini API exception into a short, actionable message."""
    text = str(error)
    code = getattr(error, "code", None)
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        if "'quota_limit_value': '0'" in text or '"quota_limit_value": "0"' in text:
            return (
                "Gemini quota for this API key's Google Cloud project is 0, so no request can succeed. "
                "Create a new key at https://aistudio.google.com/apikey (in a new project) and set GEMINI_API_KEY."
            )
        return f"Gemini rate limit reached for {GEMINI_MODEL}. Wait a minute and retry, or check your quota."
    if code in (401, 403) or "API_KEY_INVALID" in text or "PERMISSION_DENIED" in text:
        return "Gemini rejected the API key (invalid or lacks permission). Check GEMINI_API_KEY."
    if code == 503 or "UNAVAILABLE" in text:
        return "Gemini is temporarily overloaded (Google reported high demand). Try the analysis again shortly."
    if code == 404 or "NOT_FOUND" in text:
        return f"Gemini model '{GEMINI_MODEL}' was not found. Set GEMINI_MODEL to an available model."
    return f"Gemini API error ({GEMINI_MODEL}): {text[:200]}"


async def call_gemini_analysis(mda_text: str) -> tuple[dict | None, str | None]:
    """Call Gemini to analyze MD&A text for forensic insights.

    Returns:
        (parsed result, None) on success, or (None, reason) if the AI could not
        contribute. Callers must not treat a failure as an AI judgement.
    """
    api_key = gemini_api_key()
    if not api_key:
        return None, "GEMINI_API_KEY not configured — heuristic analysis only."

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return None, "google-genai package not installed. Run: pip install google-genai"

    client = genai.Client(api_key=api_key)
    # Truncate text to stay within a modest token budget (~30k chars ≈ ~8k tokens)
    prompt = GEMINI_ANALYSIS_PROMPT + mda_text[:30000]
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)

    # Google returns 503 "high demand" during load spikes: wait briefly and retry,
    # then fall back to the lighter Flash model before giving up.
    attempts = [(GEMINI_MODEL, 0.0), (GEMINI_MODEL, GEMINI_RETRY_DELAY_SECONDS)]
    if GEMINI_FALLBACK_MODEL != GEMINI_MODEL:
        attempts.append((GEMINI_FALLBACK_MODEL, 0.0))

    last_error = None
    for model, delay in attempts:
        if delay:
            await asyncio.sleep(delay)
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=prompt, config=config),
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
            return _parse_gemini_json(response.text or ""), None
        except asyncio.TimeoutError:
            return None, f"Gemini ({model}) timed out after {GEMINI_TIMEOUT_SECONDS}s."
        except (json.JSONDecodeError, ValueError) as e:
            return None, f"Gemini returned malformed JSON: {str(e)[:150]}"
        except Exception as e:
            last_error = e
            if not _is_transient_gemini_error(e):
                break
    return None, describe_gemini_error(last_error)


def _is_transient_gemini_error(error: Exception) -> bool:
    """Temporary overload (503 / UNAVAILABLE), worth retrying — unlike quota or key errors."""
    return getattr(error, "code", None) == 503 or "UNAVAILABLE" in str(error)


def _normalize_for_match(text: str) -> str:
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().strip('"').strip()


def quote_in_text(quote: str, normalized_source: str) -> bool:
    """True if the AI's quote (or its opening 80 chars) appears in the filing."""
    q = _normalize_for_match(quote).rstrip(".")
    if len(q) < 15:
        return False
    return q in normalized_source or q[:80] in normalized_source


def parse_red_flags(gemini_result: dict, source_text: str) -> list[RedFlag]:
    """Validate Gemini's suspicious sentences and verify each quote exists."""
    normalized_source = _normalize_for_match(source_text)
    red_flags: list[RedFlag] = []
    for item in gemini_result.get("suspicious_sentences") or []:
        if not isinstance(item, dict) or not item.get("sentence"):
            continue
        try:
            severity = int(float(item.get("severity", 5)))
        except (TypeError, ValueError):
            severity = 5
        category = str(item.get("category", "inconsistency")).lower()
        red_flags.append(RedFlag(
            sentence=str(item["sentence"]),
            category=category if category in VALID_CATEGORIES else "inconsistency",
            severity=max(1, min(10, severity)),
            explanation=str(item.get("explanation", "")),
            verified=quote_in_text(str(item["sentence"]), normalized_source),
        ))
    return red_flags


# ──────────────────────────────────────────────
#  Sentiment Gap & Deception Detection
# ──────────────────────────────────────────────

def detect_sentiment_gap(
    narrative_sentiment: str,
    z_score_zone: str,
) -> tuple[bool, str | None, float]:
    """Compare narrative sentiment against Z-Score financial reality.

    Returns:
        Tuple of (deception_alert, reason, gap_penalty)
    """
    # Sentiment-to-numeric mapping
    sentiment_map = {"bullish": 1, "neutral": 0, "bearish": -1}
    zone_sentiment_map = {"Safe": 1, "Gray": 0, "Distress": -1}

    if narrative_sentiment not in sentiment_map or z_score_zone not in zone_sentiment_map:
        return False, None, 0.0  # unknown tone or zone: nothing to compare

    narrative_val = sentiment_map[narrative_sentiment]
    financial_val = zone_sentiment_map[z_score_zone]

    gap = narrative_val - financial_val  # Positive = narrative more optimistic than reality

    if gap >= 2:
        # Management is bullish but company is in Distress
        return (
            True,
            f"CRITICAL: Management narrative is '{narrative_sentiment}' but financial analysis "
            f"shows the company is in the '{z_score_zone}' zone. This divergence suggests "
            f"potential misrepresentation of financial health in public filings.",
            40.0,
        )
    elif gap == 1:
        return (
            False,
            f"CAUTION: Mild optimism bias detected — management tone is '{narrative_sentiment}' "
            f"while financial zone is '{z_score_zone}'.",
            15.0,
        )
    else:
        return False, None, 0.0


# ──────────────────────────────────────────────
#  Truth Score Computation
# ──────────────────────────────────────────────

# Calibrated on large-cap 10-K MD&As (AAPL, KO, TSLA, F, MSFT...), where hedging
# scores ran ~13-27 and evasion ~2-5. Language up to the baseline is normal
# forward-looking prose; only the excess above it is penalised.
HEDGING_BASELINE = 15.0
EVASION_BASELINE = 2.0


def compute_truth_score(
    hedging_score: float,
    evasion_score: float,
    red_flags: list[RedFlag],
    gap_penalty: float,
    ai_used: bool,
) -> tuple[int, str, TruthScoreBreakdown]:
    """Truth Score = 100 minus penalties, clamped to 0-100.

    Penalties:
        hedging      (hedging_score - 15) × 1.0 above the normal baseline, max 30
        evasion      (evasion_score - 2) × 2.0 above the normal baseline, max 25
        red flags    0.75 × total severity of AI flags whose quotes were found
                     verbatim in the filing, max 30 (hallucinated quotes don't count)
        sentiment    15 for mild optimism bias, 40 for bullish-while-distressed

    Returns:
        (score, zone, breakdown)
    """
    hedging_penalty = min(30.0, max(0.0, hedging_score - HEDGING_BASELINE) * 1.0)
    evasion_penalty = min(25.0, max(0.0, evasion_score - EVASION_BASELINE) * 2.0)
    flag_severity = sum(f.severity for f in red_flags if f.verified)
    red_flag_penalty = min(30.0, flag_severity * 0.75)

    total_penalty = hedging_penalty + evasion_penalty + red_flag_penalty + gap_penalty
    score = int(round(max(0.0, min(100.0, 100.0 - total_penalty))))

    if score >= 70:
        zone = "Credible"
    elif score >= 40:
        zone = "Suspicious"
    else:
        zone = "Deceptive"

    breakdown = TruthScoreBreakdown(
        hedging_penalty=round(hedging_penalty, 1),
        evasion_penalty=round(evasion_penalty, 1),
        red_flag_penalty=round(red_flag_penalty, 1),
        sentiment_gap_penalty=round(gap_penalty, 1),
        basis="ai+heuristic" if ai_used else "heuristic",
    )
    return score, zone, breakdown


# ──────────────────────────────────────────────
#  Main Analysis Pipeline
# ──────────────────────────────────────────────

async def analyze_filing_text(
    mda_text: str,
    risk_factors_text: str,
    z_score_result: ZScoreResult | None = None,
) -> tuple[ForensicResult, str | None]:
    """Full forensic analysis pipeline.

    Steps:
        1. Compute hedging & evasion scores from the MD&A (management's own voice;
           Risk Factors are required to be cautious, so they are not scored)
        2. Call Gemini for MD&A sentiment and red flags, verifying every quote
        3. Detect sentiment gap vs Z-Score zone (only if both are known)
        4. Compute the composite Truth Score
        5. Merge all findings into ForensicResult

    Returns:
        (result, ai_error) — ai_error explains why Gemini did not contribute.
    """
    mda_words = _word_count(mda_text)
    total_words = mda_words + _word_count(risk_factors_text)

    if mda_words < MIN_WORDS_FOR_ANALYSIS:
        # Not enough narrative to judge — don't send placeholders to the AI
        # or report a score that would look meaningful.
        note = (
            f"MD&A text unavailable or too short ({mda_words} words; "
            f"{MIN_WORDS_FOR_ANALYSIS} needed). Truth Score not computed."
        )
        return ForensicResult(
            truth_score=None,
            truth_zone=None,
            linguistic_analysis=LinguisticAnalysis(
                hedging_score=0,
                evasion_score=0,
                sentiment="unknown",
                sentiment_confidence=0,
                total_words_analyzed=total_words,
            ),
            z_score_result=z_score_result,
            analysis_note=note,
        ), "Skipped: no filing text to analyze."

    # 1. Heuristics on the MD&A
    hedging_score, hedging_words = compute_hedging_score(mda_text)
    evasion_score = compute_evasion_score(mda_text)
    lexicon_sentiment, net_tone = compute_lexicon_tone(mda_text)

    # 2. Gemini AI analysis on MD&A
    gemini_result, ai_error = await call_gemini_analysis(mda_text)
    ai_used = gemini_result is not None

    red_flags: list[RedFlag] = []
    # Lexicon tone is the fallback so the sentiment-gap check still runs without AI
    sentiment = lexicon_sentiment
    sentiment_source = "lexicon"
    confidence = 0.0
    if ai_used:
        sentiment_source = "ai"
        raw_sentiment = str(gemini_result.get("sentiment", "neutral")).lower()
        sentiment = raw_sentiment if raw_sentiment in VALID_SENTIMENTS else "neutral"
        try:
            confidence = max(0.0, min(1.0, float(gemini_result.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        red_flags = parse_red_flags(gemini_result, mda_text)

    # 3. Sentiment gap detection — needs a Z-Score to compare against
    deception_alert, deception_reason, gap_penalty = False, None, 0.0
    if z_score_result is not None:
        deception_alert, deception_reason, gap_penalty = detect_sentiment_gap(
            sentiment, z_score_result.zone,
        )
        if deception_reason and sentiment_source == "lexicon":
            deception_reason += " (Tone measured with the financial word lexicon.)"

    # 4. Truth Score (computed before the alert flag is added so it isn't double-counted)
    truth_score, truth_zone, breakdown = compute_truth_score(
        hedging_score, evasion_score, red_flags, gap_penalty, ai_used,
    )

    # If deception alert triggered, surface it as a critical red flag
    if deception_alert and deception_reason:
        red_flags.insert(0, RedFlag(
            sentence=deception_reason,
            category="sentiment_gap",
            severity=10,
            explanation="Management narrative significantly diverges from quantitative financial reality.",
        ))

    note = None
    if not ai_used:
        note = (
            "AI analysis unavailable; Truth Score uses hedging, evasion and lexicon-tone "
            "heuristics only (no AI red flags)."
        )
    elif z_score_result is None:
        note = "Z-Score unavailable; sentiment-gap check skipped."

    # 5. Assemble result
    linguistic = LinguisticAnalysis(
        hedging_score=hedging_score,
        evasion_score=evasion_score,
        sentiment=sentiment,
        sentiment_confidence=confidence,
        sentiment_source=sentiment_source,
        net_tone=net_tone,
        hedging_words_found=hedging_words,
        suspicious_sentences=red_flags,
        total_words_analyzed=total_words,
    )

    return ForensicResult(
        truth_score=truth_score,
        truth_zone=truth_zone,
        linguistic_analysis=linguistic,
        red_flags=red_flags,
        deception_alert=deception_alert,
        deception_reason=deception_reason,
        z_score_result=z_score_result,
        ai_confidence_score=confidence if ai_used else None,
        truth_score_breakdown=breakdown,
        analysis_note=note,
    ), ai_error


async def run_forensic_pipeline(ticker: str) -> tuple[ForensicAuditResponse, FinancialData | None]:
    """Fetch data, score it and analyze the filing. Shared by the audit and PDF endpoints."""
    from scraper import (
        fetch_financial_data_auto,
        fetch_10k_text_sections,
        get_company_name,
        is_international_ticker,
    )
    from risk_engine import ZScoreNotApplicable, calculate_altman_z_score
    from earnings_call import build_call_analysis, fetch_call_material, fetch_earnings_release
    from truth_score import health_reading

    ticker = ticker.upper().strip()
    data_sources: list[str] = []
    international = is_international_ticker(ticker)

    # Steps 1-3 are independent network work; run them concurrently
    async def _financials():
        try:
            return await fetch_financial_data_auto(ticker), None
        except Exception as e:
            return None, e

    async def _sections():
        if international:
            return None, None
        try:
            return await fetch_10k_text_sections(ticker), None
        except Exception as e:
            return None, e

    async def _call_material():
        if international:
            # Alpha Vantage transcripts and SEC releases cover US-listed companies only;
            # asking anyway spends 3-4 of the 25 daily requests on a guaranteed miss.
            return {"error": INTERNATIONAL_CALL_NOTE}
        try:
            return await fetch_call_material(ticker)
        except Exception as e:
            return {"error": f"Earnings call lookup failed: {str(e)[:120]}"}

    company_name, (fin, fin_err), (sections, text_err), call_material = await asyncio.gather(
        get_company_name(ticker), _financials(), _sections(), _call_material(),
    )

    # Z-Score
    financial_data: FinancialData | None = None
    z_score_result = None
    if fin is not None:
        financial_data, source = fin
        data_sources.append(f"{source} — Financial Data (FY ending {financial_data.fiscal_period_end or 'n/a'})")
        try:
            z_score_result = calculate_altman_z_score(financial_data)
        except ValueError as e:
            data_sources.append(f"Z-Score not computed: {str(e)[:150]}")
    elif isinstance(fin_err, ZScoreNotApplicable):
        data_sources.append(f"Z-Score not computed: {str(fin_err)[:200]}")
    else:
        detail = getattr(fin_err, "detail", None) or str(fin_err)
        data_sources.append(f"Financial data unavailable: {str(detail)[:150]}")

    # Filing text (SEC filings are US-only)
    mda_text = ""
    risk_factors_text = ""
    if international:
        data_sources.append("International ticker — 10-K text not available (SEC filings are US-only)")
    elif sections is not None:
        mda_text = sections.get("mda", "")
        risk_factors_text = sections.get("risk_factors", "")
        if mda_text or risk_factors_text:
            data_sources.append("SEC EDGAR — 10-K Filing Text")
        else:
            data_sources.append("SEC EDGAR — 10-K sections could not be located in the filing")
    else:
        detail = getattr(text_err, "detail", None) or str(text_err)
        data_sources.append(f"SEC EDGAR — Filing text unavailable: {str(detail)[:100]}")

    # Financial health zone (Z-Score, or bank capital strength) for the call's tone check
    health = health_reading(z_score_result, financial_data)
    earnings_call = build_call_analysis(call_material, health[2] if health else None)
    if earnings_call.available:
        data_sources.append(earnings_call.source_label)

    # Some 10-Ks (JPM, BAC, IBM, GE...) don't use the standard Item 7 layout. Their
    # SEC earnings press release is management's own prose too, so use it instead.
    language_source = "10-K MD&A"
    if not international and _word_count(mda_text) < MIN_WORDS_FOR_ANALYSIS:
        release = call_material.get("release")
        if release is None:
            try:
                release, _ = await fetch_earnings_release(ticker)
            except Exception:
                release = None
        if release and _word_count(release["text"]) >= MIN_WORDS_FOR_ANALYSIS:
            mda_text = release["text"][:MAX_LANGUAGE_CHARS]
            language_source = f"Earnings press release (SEC 8-K, {release['date']})"
            data_sources.append(f"{language_source} — used for filing language (10-K MD&A not located)")

    forensic_result, ai_error = await analyze_filing_text(mda_text, risk_factors_text, z_score_result)
    if forensic_result.truth_score_breakdown is not None:
        forensic_result.language_source = language_source
    gemini_active = ai_error is None
    if gemini_active:
        data_sources.append(f"Google Gemini ({GEMINI_MODEL}) — AI Analysis")

    apply_credibility_index(forensic_result, z_score_result, earnings_call, financial_data, gemini_active)

    from conviction import compute_conviction
    from risk_register import build_risk_register
    conviction = compute_conviction(z_score_result, forensic_result, earnings_call, financial_data)
    monte_carlo = company_stress_test(ticker, financial_data)
    risk_register = build_risk_register(z_score_result, forensic_result, earnings_call, conviction, monte_carlo)

    response = ForensicAuditResponse(
        ticker=ticker,
        company_name=company_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        forensic=forensic_result,
        data_sources=data_sources,
        gemini_active=gemini_active,
        ai_error=ai_error,
        earnings_call=earnings_call,
        conviction=conviction,
        financials=financial_data,
        monte_carlo=monte_carlo,
        risk_register=risk_register,
    )
    return response, financial_data


def company_stress_test(
    ticker: str,
    financial_data: FinancialData | None,
    num_simulations: int = 1000,
    time_horizon_years: int = 5,
):
    """Monte Carlo revenue stress test using the company's own growth history.

    Seeded from the ticker so the report page and the PDF show the same numbers.
    """
    from models import MonteCarloInput
    from risk_engine import growth_parameters_from_history, run_monte_carlo_simulation

    if financial_data is None or financial_data.revenue <= 0:
        return None
    drift, volatility, source = growth_parameters_from_history(financial_data.history)
    seed = int.from_bytes(hashlib.sha256(ticker.upper().encode()).digest()[:4], "big")
    return run_monte_carlo_simulation(MonteCarloInput(
        ticker=ticker,
        num_simulations=num_simulations,
        time_horizon_years=time_horizon_years,
        initial_revenue=financial_data.revenue,
        revenue_growth_mean=drift,
        revenue_growth_std=volatility,
        seed=seed,
        parameter_source=source,
    ))


def apply_credibility_index(
    result: ForensicResult,
    z_score_result: ZScoreResult | None,
    earnings_call,
    financial_data: FinancialData | None,
    ai_used: bool,
) -> None:
    """Replace the filing-only score with the five-component Credibility Index (in place)."""
    from truth_score import compute_credibility, coverage_note

    score, zone, components, critical = compute_credibility(
        z_score_result, result, earnings_call, financial_data,
    )
    filing = result.truth_score_breakdown
    result.truth_score = score
    result.truth_zone = zone
    result.truth_score_breakdown = TruthScoreBreakdown(
        components=components,
        hedging_penalty=filing.hedging_penalty if filing else 0.0,
        evasion_penalty=filing.evasion_penalty if filing else 0.0,
        red_flag_penalty=filing.red_flag_penalty if filing else 0.0,
        sentiment_gap_penalty=filing.sentiment_gap_penalty if filing else 0.0,
        basis="ai+heuristic" if ai_used else "heuristic",
    )

    # An upbeat earnings call from a Distress-zone company is as serious as an upbeat filing
    if critical and not result.deception_alert:
        result.deception_alert = True
        result.deception_reason = critical
        result.red_flags.insert(0, RedFlag(
            sentence=critical,
            category="sentiment_gap",
            severity=10,
            explanation="Management narrative significantly diverges from quantitative financial reality.",
        ))

    result.analysis_note = coverage_note(components)


# ──────────────────────────────────────────────
#  API Endpoint
# ──────────────────────────────────────────────

@router.post(
    "/forensic-audit",
    response_model=ForensicAuditResponse,
    summary="Run Forensic AI Audit",
    description=(
        "Full forensic audit pipeline: fetches 10-K filing text, runs Altman Z-Score, "
        "and performs AI-powered linguistic analysis to compute a Truth Score and detect deception. "
        "Merges quantitative financial analysis with qualitative narrative forensics."
    ),
    dependencies=[Depends(rate_limit)],
)
async def api_forensic_audit(request: ForensicRequest) -> ForensicAuditResponse:
    """Orchestrate the complete forensic audit pipeline."""
    response, _ = await run_forensic_pipeline(request.ticker)
    return response
