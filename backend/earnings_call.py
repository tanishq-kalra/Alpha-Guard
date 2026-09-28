"""
Alpha-Guard — Earnings Call Analysis
=====================================
Analyses what management says on the quarterly earnings conference call.

Sources:
  1. Alpha Vantage EARNINGS_CALL_TRANSCRIPT (primary) — full call, speaker by
     speaker, including the unscripted analyst Q&A. Needs ALPHAVANTAGE_API_KEY
     (free tier: 25 requests/day), so transcripts are cached on disk.
  2. SEC 8-K Item 2.02 earnings press release, exhibit 99.1 (fallback, US only,
     no key) — management's prepared commentary, without Q&A.

Signals follow the conference-call deception literature (Larcker &
Zakolyukina, 2012, "Detecting Deceptive Discussions in Conference Calls"):
unscripted answers are harder to manage than prepared remarks, so evasive
answers and a tone drop from script to Q&A are the key indicators.
"""

import asyncio
import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path

import httpx

from config import alphavantage_api_key
from forensic_analyzer import (
    _phrase_pattern,
    compute_evasion_score,
    compute_hedging_score,
    compute_lexicon_tone,
)
from models import CallExchange, CallSegmentMetrics, EarningsCallAnalysis

ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
CACHE_DIR = Path(__file__).parent / ".cache" / "transcripts"
TRANSCRIPT_TTL_SECONDS = 7 * 24 * 3600      # a published call never changes
MISS_TTL_SECONDS = 12 * 3600                # "no transcript" is re-checked twice a day

# Phrases executives use to decline answering an analyst's question. Referring
# back ("as I said") is deliberately excluded: it is normal when answers build
# on each other and produced false positives on real calls.
DEFLECTION_PHRASES = [
    "we don't break out", "we do not break out", "we don't disclose", "we do not disclose",
    "we don't provide", "we do not provide", "we don't comment", "we do not comment",
    "not going to comment", "can't comment", "cannot comment", "won't comment",
    "not going to get into", "not going to speculate", "don't want to speculate",
    "too early to say", "too early to tell", "too soon to say", "too soon to tell",
    "not in a position to", "i'd rather not", "i would rather not",
    "we'll share more", "we will share more", "more to come on that",
    "i'm not going to", "we're not going to", "we are not going to",
    "we haven't given", "we have not given", "we're not guiding", "we are not guiding",
]
_DEFLECTION_PATTERNS = [(p, _phrase_pattern(p)) for p in DEFLECTION_PHRASES]

EXECUTIVE_TITLE = re.compile(
    r"\b(ceo|cfo|coo|cto|chief|president|chair|officer|vice president|vp|evp|svp|head|director|"
    r"treasurer|controller|founder|investor relations|ir)\b",
    re.IGNORECASE,
)

# Answers shorter than this are counted as brush-offs
BRIEF_ANSWER_WORDS = 40


# ──────────────────────────────────────────────
#  Caching
# ──────────────────────────────────────────────

_misses: dict[str, float] = {}
_av_exhausted_until = 0.0


def _cache_path(ticker: str) -> Path:
    safe = re.sub(r"[^A-Z0-9.\-]", "_", ticker.upper())
    return CACHE_DIR / f"{safe}.json"


def _read_cache(ticker: str) -> dict | None:
    path = _cache_path(ticker)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if time.time() - data.get("fetched_at", 0) > TRANSCRIPT_TTL_SECONDS:
        return None
    return data


def _write_cache(ticker: str, payload: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(ticker).write_text(json.dumps({**payload, "fetched_at": time.time()}), encoding="utf-8")
    except OSError:
        pass  # caching is best-effort (e.g. read-only filesystem)


def clear_caches() -> None:
    global _av_exhausted_until
    _misses.clear()
    _av_exhausted_until = 0.0


# ──────────────────────────────────────────────
#  Alpha Vantage transcripts
# ──────────────────────────────────────────────

def candidate_quarters(today: date | None = None) -> list[str]:
    """Quarters to try, most likely first.

    Calls happen a few weeks after quarter end. Alpha Vantage labels some
    companies by fiscal quarter (e.g. Apple's June quarter is fiscal Q3), so
    the current calendar quarter is tried too.
    """
    today = today or date.today()
    q = (today.month - 1) // 3 + 1
    prev = (today.year, q - 1) if q > 1 else (today.year - 1, 4)
    prev2 = (prev[0], prev[1] - 1) if prev[1] > 1 else (prev[0] - 1, 4)
    ordered = [prev, (today.year, q), prev2]
    return [f"{y}Q{n}" for y, n in ordered]


# Free keys allow 1 request/second and 25/day. Requests are serialised and spaced.
AV_MIN_INTERVAL_SECONDS = 1.2
AV_BURST_RETRIES = 2
_av_lock: asyncio.Lock | None = None
_av_last_request = 0.0


class AlphaVantageExhausted(Exception):
    """The daily request quota is used up."""


async def _av_request(client: httpx.AsyncClient, params: dict) -> dict:
    """One Alpha Vantage call, spaced from the previous one and retried on the per-second limit.

    Raises:
        AlphaVantageExhausted: when the daily quota is used up.
    """
    global _av_lock, _av_last_request, _av_exhausted_until
    if _av_lock is None:
        _av_lock = asyncio.Lock()

    async with _av_lock:
        for attempt in range(AV_BURST_RETRIES + 1):
            wait = AV_MIN_INTERVAL_SECONDS - (time.monotonic() - _av_last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            resp = await client.get(ALPHAVANTAGE_URL, params=params, timeout=30.0)
            _av_last_request = time.monotonic()
            resp.raise_for_status()
            data = resp.json()

            message = str(data.get("Information") or data.get("Note") or "").lower()
            if not message:
                return data
            # The per-second message also mentions "25 requests per day", so check it first
            if "per second" in message or "sparingly" in message:
                await asyncio.sleep(AV_MIN_INTERVAL_SECONDS * (attempt + 1))
                continue
            if "per day" in message or "rate limit" in message or "premium" in message:
                _av_exhausted_until = time.time() + 3600
                raise AlphaVantageExhausted(message)
            return data
    raise AlphaVantageExhausted("Alpha Vantage kept asking to slow down")


async def _alpha_vantage_transcript(client: httpx.AsyncClient, ticker: str, quarter: str, key: str) -> list[dict] | None:
    """Transcript turns, [] if none exists for the quarter, None if the quota is exhausted."""
    try:
        data = await _av_request(
            client, {"function": "EARNINGS_CALL_TRANSCRIPT", "symbol": ticker, "quarter": quarter, "apikey": key},
        )
    except AlphaVantageExhausted:
        return None
    return data.get("transcript") or []


def _period_month(iso_date: str) -> tuple[int, int]:
    """(year, month) of a period end; dates in the first week count as the prior month
    (52/53-week fiscal years such as a year ending 2026-01-03)."""
    d = date.fromisoformat(iso_date)
    if d.day <= 7:
        return (d.year - 1, 12) if d.month == 1 else (d.year, d.month - 1)
    return d.year, d.month


def fiscal_year_end_month(annual: list[dict]) -> int | None:
    """Most common month among annual period ends. The first entry is a trailing
    twelve months and is skipped."""
    months = []
    for row in annual[1:7]:
        try:
            months.append(_period_month(row["fiscalDateEnding"])[1])
        except (KeyError, ValueError):
            continue
    return Counter(months).most_common(1)[0][0] if months else None


def fiscal_quarter_label(period_end: str, fy_end_month: int) -> str:
    """Alpha Vantage transcript label for a quarter, e.g. Apple's June quarter -> '2026Q3'.

    Fiscal years are named after the calendar year they end in.
    """
    year, month = _period_month(period_end)
    months_after_fy_end = (month - fy_end_month - 1) % 12   # 0..11 within the fiscal year
    quarter = months_after_fy_end // 3 + 1
    fiscal_year = year if month <= fy_end_month else year + 1
    return f"{fiscal_year}Q{quarter}"


async def latest_call_quarters(client: httpx.AsyncClient, ticker: str, key: str, limit: int = 2) -> list[str]:
    """Transcript labels of the most recently reported quarters, newest first ([] if unknown).

    Raises:
        AlphaVantageExhausted: when the daily quota is used up.
    """
    data = await _av_request(client, {"function": "EARNINGS", "symbol": ticker, "apikey": key})
    fy_end = fiscal_year_end_month(data.get("annualEarnings") or [])
    if fy_end is None:
        return []
    today = date.today().isoformat()
    labels = []
    for row in data.get("quarterlyEarnings") or []:
        reported = row.get("reportedDate") or ""
        if not reported or reported > today or row.get("reportedEPS") in (None, "None"):
            continue
        try:
            label = fiscal_quarter_label(row["fiscalDateEnding"], fy_end)
        except (KeyError, ValueError):
            continue
        if label not in labels:
            labels.append(label)
        if len(labels) == limit:
            break
    return labels


async def fetch_transcript(ticker: str) -> tuple[dict | None, str | None]:
    """Latest earnings call transcript for a ticker.

    Returns:
        ({"quarter", "turns"}, None) or (None, reason it is unavailable).
    """
    ticker = ticker.upper()
    cached = _read_cache(ticker)
    if cached:
        return cached, None
    if time.time() - _misses.get(ticker, 0) < MISS_TTL_SECONDS:
        return None, "No recent earnings call transcript found (checked recently)."

    key = alphavantage_api_key()
    if not key:
        if ticker != "IBM":
            return None, "ALPHAVANTAGE_API_KEY not set — transcripts unavailable (IBM works with the public demo key)."
        key, quarters = "demo", ["2024Q1"]  # the only call the public demo key serves
    else:
        quarters = candidate_quarters()

    if time.time() < _av_exhausted_until:
        return None, "Alpha Vantage daily request limit reached; try again later."

    try:
        async with httpx.AsyncClient() as client:
            if key != "demo":
                try:
                    # Exact fiscal labels from the reporting calendar; calendar guesses as a fallback
                    quarters = await latest_call_quarters(client, ticker, key) or quarters
                except AlphaVantageExhausted:
                    return None, "Alpha Vantage daily request limit reached; try again later."
            for quarter in quarters:
                turns = await _alpha_vantage_transcript(client, ticker, quarter, key)
                if turns is None:
                    return None, "Alpha Vantage daily request limit reached; try again later."
                if turns:
                    payload = {"source": "alpha_vantage", "quarter": quarter, "turns": turns}
                    _write_cache(ticker, payload)
                    return payload, None
    except (httpx.HTTPError, ValueError) as e:
        return None, f"Alpha Vantage request failed: {str(e)[:120]}"

    _misses[ticker] = time.time()
    return None, f"No earnings call transcript found for {', '.join(quarters)}."


# ──────────────────────────────────────────────
#  SEC 8-K earnings release (fallback)
# ──────────────────────────────────────────────

_EXHIBIT_99 = re.compile(r"ex[-_]?99|exhibit[-_]?99|earnings[-_]?release|press[-_]?release|pressrelease", re.IGNORECASE)
_SEC_INDEX_PAGE = re.compile(r"-index(-headers)?\.html?$|^R\d+\.htm$", re.IGNORECASE)
_QUOTED = re.compile(r"[“\"]([^”\"]{60,4000})[”\"]")

# Older releases describe a different business situation; don't fall back that far
MAX_RELEASE_AGE_DAYS = 460


def pick_release_document(items: list[dict], primary_document: str) -> str | None:
    """The press-release exhibit in an 8-K filing index.

    Named exhibits (ex99, exhibit99, earningsrelease...) win; otherwise the
    largest attached HTML document that isn't the 8-K cover page or one of
    the SEC's own index/viewer pages.
    """
    html = [
        it for it in items
        if it.get("name", "").lower().endswith((".htm", ".html"))
        and not _SEC_INDEX_PAGE.search(it["name"])
        and it["name"] != primary_document
    ]
    named = [it["name"] for it in html if _EXHIBIT_99.search(it["name"])]
    if named:
        return named[0]

    def size(it: dict) -> int:
        try:
            return int(it.get("size") or 0)
        except ValueError:
            return 0

    largest = max(html, key=size, default=None)
    return largest["name"] if largest and size(largest) > 0 else None


async def fetch_earnings_release(ticker: str) -> tuple[dict | None, str | None]:
    """Latest 8-K Item 2.02 earnings press release (exhibit 99.1)."""
    import scraper

    try:
        cik, _ = await scraper.resolve_ticker_to_cik(ticker)
        submissions = await scraper.get_submissions(cik)
    except Exception as e:
        return None, f"SEC lookup failed: {getattr(e, 'detail', str(e))[:120]}"

    recent = submissions.get("filings", {}).get("recent", {})
    for i, form in enumerate(recent.get("form", [])):
        items = (recent.get("items") or [""] * (i + 1))[i] or ""
        if form != "8-K" or "2.02" not in items:
            continue
        filed = recent["filingDate"][i]
        try:
            if (date.today() - date.fromisoformat(filed)).days > MAX_RELEASE_AGE_DAYS:
                break  # filings are newest first; everything after this is older still
        except ValueError:
            continue
        acc = recent["accessionNumber"][i].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
        try:
            index = (await scraper._sec_get(f"{base}/index.json")).json()
            primary = (recent.get("primaryDocument") or [""] * (i + 1))[i]
            exhibit = pick_release_document(index.get("directory", {}).get("item", []), primary)
            if not exhibit:
                continue
            raw = scraper._decode_filing((await scraper._sec_get(f"{base}/{exhibit}", timeout=45.0)).content)
        except Exception:
            continue
        text = re.sub(r"\s+", " ", scraper._strip_html_tags(raw)).strip()
        return {
            "source": "sec_8k",
            "date": recent["filingDate"][i],
            "url": f"{base}/{exhibit}",
            "text": text,
        }, None
    return None, "No 8-K earnings press release (Item 2.02) found."


# ──────────────────────────────────────────────
#  Analysis
# ──────────────────────────────────────────────

def _role(turn: dict) -> str:
    speaker = (turn.get("speaker") or "").strip().lower()
    title = (turn.get("title") or "").strip()
    if speaker == "operator" or title.lower() == "operator":
        return "operator"
    if title.lower() == "analyst" or not EXECUTIVE_TITLE.search(title):
        return "analyst"
    return "executive"


def _segment_metrics(texts: list[str], provider_scores: list[float]) -> CallSegmentMetrics | None:
    text = " ".join(t for t in texts if t)
    words = len(text.split())
    if words == 0:
        return None
    hedging, _ = compute_hedging_score(text)
    sentiment, net_tone = compute_lexicon_tone(text)
    return CallSegmentMetrics(
        words=words,
        hedging_score=hedging,
        evasion_score=compute_evasion_score(text),
        sentiment=sentiment,
        net_tone=net_tone,
        provider_sentiment=round(sum(provider_scores) / len(provider_scores), 3) if provider_scores else None,
    )


def _deflection_phrase(text: str) -> str | None:
    for phrase, pattern in _DEFLECTION_PATTERNS:
        if pattern.search(text):
            return phrase
    return None


def _snippet_around(text: str, phrase: str, width: int = 220) -> str:
    match = _phrase_pattern(phrase).search(text)
    if not match:
        return text[:width]
    start = max(0, match.start() - width // 2)
    snippet = text[start:start + width].strip()
    return ("…" if start > 0 else "") + snippet + ("…" if start + width < len(text) else "")


def _provider_score(turn: dict) -> float | None:
    try:
        return float(turn.get("sentiment"))
    except (TypeError, ValueError):
        return None


# Analysts often ask without a question mark ("I'd love to get your take on..."),
# so questions are recognised by wording too. Anything else (thanks, congratulations)
# is a courtesy and doesn't start an exchange.
# Only phrases that ask something: "when"/"which" are often plain conjunctions, and
# "my question" must not match sign-offs like "thanks for taking my questions".
_QUESTION_CUES = re.compile(
    r"\b(my question|first question|one question|a question|follow-up question|question is|"
    r"question on|question about|ask about|ask on|to ask|could you|can you|would you|will you|"
    r"how|what|why|whether|color on|any color|curious|wondering|help us|talk about|walk us|"
    r"comment on|thoughts on|update on|love to|like to|elaborate|clarify|take on)\b",
    re.IGNORECASE,
)


def _is_courtesy(turn: dict) -> bool:
    content = turn.get("content") or ""
    return "?" not in content and not _QUESTION_CUES.search(content)


def _is_moderator(turn: dict) -> bool:
    """Investor Relations hosts run the Q&A ("Operator, next question please")."""
    return "investor relations" in (turn.get("title") or "").lower()


def analyze_transcript(turns: list[dict]) -> dict:
    """Split a call into prepared remarks and Q&A and measure each."""
    first_question = next((i for i, t in enumerate(turns) if _role(t) == "analyst"), len(turns))

    prepared_texts, prepared_scores = [], []
    for t in turns[:first_question]:
        # IR's opening is mostly the safe-harbor statement, which is hedged by law
        if _role(t) == "executive" and not _is_moderator(t):
            prepared_texts.append(t.get("content", ""))
            if (s := _provider_score(t)) is not None:
                prepared_scores.append(s)

    exchanges: list[CallExchange] = []
    answer_texts, answer_scores = [], []
    current: dict | None = None

    def close_exchange():
        if current and current["answers"]:
            answer = " ".join(current["answers"])
            phrase = _deflection_phrase(answer)
            words = len(answer.split())
            exchanges.append(CallExchange(
                analyst=current["analyst"],
                question=current["question"][:400],
                respondents=sorted(set(current["respondents"])),
                answer_excerpt=_snippet_around(answer, phrase) if phrase else answer[:260],
                answer_words=words,
                deflection_phrase=phrase,
                brief=words < BRIEF_ANSWER_WORDS,
            ))

    for t in turns[first_question:]:
        role = _role(t)
        if role == "analyst":
            close_exchange()
            if _is_courtesy(t):
                current = None  # "Thanks, guys." ends the exchange; it isn't a question
                continue
            current = {"analyst": t.get("speaker", "Analyst"), "question": t.get("content", ""),
                       "answers": [], "respondents": []}
        elif role == "executive" and _is_moderator(t):
            continue  # IR host handing over to the operator, not answering
        elif role == "executive" and current is not None:
            content = t.get("content", "")
            current["answers"].append(content)
            current["respondents"].append(f"{t.get('speaker', '')} ({t.get('title', '')})".strip())
            answer_texts.append(content)
            if (s := _provider_score(t)) is not None:
                answer_scores.append(s)
        elif role == "operator":
            close_exchange()
            current = None
    close_exchange()

    executives = sorted({
        f"{t.get('speaker', '').strip()} — {t.get('title', '').strip()}"
        for t in turns if _role(t) == "executive"
    })
    return {
        "prepared": _segment_metrics(prepared_texts, prepared_scores),
        "qa": _segment_metrics(answer_texts, answer_scores),
        "exchanges": exchanges,
        "executives": executives,
    }


# Below this, quoted management commentary is too short to measure tone
MIN_QUOTE_WORDS = 150


def analyze_press_release(text: str) -> dict:
    """Score management's quoted commentary, or the whole release if quotes are short."""
    quotes = [q.strip() for q in _QUOTED.findall(text)]
    use_quotes = sum(len(q.split()) for q in quotes) >= MIN_QUOTE_WORDS
    return {
        "prepared": _segment_metrics(quotes if use_quotes else [text], []),
        "qa": None,
        "exchanges": [],
        "executives": [],
        "scope": "management quotes" if use_quotes else "full release",
    }


def candor_assessment(
    prepared: CallSegmentMetrics | None,
    qa: CallSegmentMetrics | None,
    exchanges: list[CallExchange],
    z_zone: str | None,
) -> tuple[int | None, list[str], float | None, float]:
    """Call Candor Score (0-100), human-readable flags, tone shift and deflection rate."""
    flags: list[str] = []
    penalty = 0.0

    answered = len(exchanges)
    deflected = sum(1 for e in exchanges if e.deflection_phrase)
    brief = sum(1 for e in exchanges if e.brief)
    deflection_rate = round(deflected / answered, 3) if answered else 0.0

    if answered:
        if deflected:
            flags.append(f"Executives deflected {deflected} of {answered} analyst questions.")
        penalty += min(30.0, deflection_rate * 100 * 0.6)
        if brief:
            flags.append(f"{brief} answer(s) were under {BRIEF_ANSWER_WORDS} words.")
            penalty += min(10.0, brief / answered * 100 * 0.2)

    tone_shift = None
    if prepared and qa and prepared.net_tone is not None and qa.net_tone is not None:
        tone_shift = round(qa.net_tone - prepared.net_tone, 3)
        if tone_shift <= -0.25:
            flags.append(f"Tone drops from prepared remarks to Q&A ({tone_shift:+.2f}): the script is rosier than the answers.")
        penalty += min(25.0, max(0.0, -tone_shift - 0.1) * 50)

    for label, seg in (("prepared remarks", prepared), ("Q&A answers", qa)):
        if seg and seg.hedging_score > 30:
            flags.append(f"Heavy hedging in {label} (score {seg.hedging_score:.0f}).")
    worst_hedging = max((s.hedging_score for s in (prepared, qa) if s), default=0.0)
    penalty += min(15.0, max(0.0, worst_hedging - 20) * 0.75)

    call_sentiment = (qa or prepared).sentiment if (qa or prepared) else None
    if call_sentiment == "bullish" and z_zone == "Distress":
        flags.append("Upbeat call while the Z-Score is in the Distress zone.")
        penalty += 20.0

    if prepared is None and qa is None:
        return None, flags, tone_shift, deflection_rate
    return int(round(max(0.0, min(100.0, 100.0 - penalty)))), flags, tone_shift, deflection_rate


async def fetch_call_material(ticker: str, allow_sec: bool = True) -> dict:
    """Network step: the transcript, else the SEC earnings release, else the reasons neither exists."""
    transcript, transcript_error = await fetch_transcript(ticker)
    if transcript:
        return {"transcript": transcript}
    if allow_sec:
        release, release_error = await fetch_earnings_release(ticker)
        if release:
            return {"release": release, "transcript_error": transcript_error}
        transcript_error = f"{transcript_error} {release_error}".strip()
    return {"error": transcript_error}


def build_call_analysis(material: dict, z_zone: str | None = None) -> EarningsCallAnalysis:
    """Analysis step (no network): score the fetched call material."""
    transcript = material.get("transcript")
    if transcript:
        parts = analyze_transcript(transcript["turns"])
        score, flags, tone_shift, deflection_rate = candor_assessment(
            parts["prepared"], parts["qa"], parts["exchanges"], z_zone,
        )
        return EarningsCallAnalysis(
            available=True,
            source="alpha_vantage",
            source_label=f"Earnings call transcript — {transcript['quarter']} (Alpha Vantage)",
            quarter=transcript["quarter"],
            prepared=parts["prepared"],
            qa=parts["qa"],
            executives=parts["executives"],
            analyst_questions=len(parts["exchanges"]),
            deflection_rate=deflection_rate,
            tone_shift=tone_shift,
            candor_score=score,
            flags=flags,
            exchanges=sorted(parts["exchanges"], key=lambda e: (e.deflection_phrase is None, not e.brief))[:10],
        )

    release = material.get("release")
    if release:
        parts = analyze_press_release(release["text"])
        # Candor is about answering questions; a press release has none, so no score
        _, flags, _, _ = candor_assessment(parts["prepared"], None, [], z_zone)
        flags.append("Press release only — no analyst Q&A, so the Call Candor Score can't be measured.")
        transcript_error = material.get("transcript_error")
        return EarningsCallAnalysis(
            available=True,
            source="sec_8k",
            source_label=f"Earnings press release ({parts['scope']}) — SEC 8-K filed {release['date']}",
            date=release["date"],
            url=release["url"],
            prepared=parts["prepared"],
            candor_score=None,
            flags=flags,
            note=(f"{transcript_error} Showing the SEC earnings press release instead."
                  if transcript_error else None),
        )

    return EarningsCallAnalysis(available=False, note=material.get("error"))


async def analyze_earnings_call(ticker: str, z_zone: str | None = None, allow_sec: bool = True) -> EarningsCallAnalysis:
    """Fetch and analyse the latest earnings call, falling back to the press release."""
    return build_call_analysis(await fetch_call_material(ticker, allow_sec), z_zone)
