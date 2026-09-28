"""
Alpha-Guard — Truth Score (Credibility Index)
==============================================
Combines five independent pieces of evidence into one 0-100 score:

  Component               Weight  Evidence
  financial_health          30%   Altman Z-Score scaled within its zone; for banks and
                                  insurers (where Altman doesn't apply) capital strength
                                  (equity / assets) and return on assets
  filing_language           20%   Hedging, evasion and verified AI red flags in the 10-K
                                  MD&A, or the SEC earnings press release when no MD&A is found
  call_candor               20%   Earnings-call Candor Score (deflections, brief answers, tone drop)
  narrative_consistency     15%   Management's tone (filing + call) vs financial health
  earnings_quality          15%   Sloan accruals: are profits backed by operating cash flow?
                                  (not applied to financial companies)

Components without data are left out and the remaining weights are
re-normalised, so a company without an MD&A (non-standard 10-K) or without
a call transcript is still scored on what is known. With fewer than three
components the score is labelled as limited evidence.
"""

from forensic_analyzer import detect_sentiment_gap
from models import (
    EarningsCallAnalysis,
    FinancialData,
    ForensicResult,
    TruthComponent,
    ZScoreResult,
)
from risk_engine import is_financial_company

WEIGHTS = {
    "financial_health": 0.30,
    "filing_language": 0.20,
    "call_candor": 0.20,
    "narrative_consistency": 0.15,
    "earnings_quality": 0.15,
}
LABELS = {
    "financial_health": "Financial Health",
    "filing_language": "Filing Language",
    "call_candor": "Earnings Call Candor",
    "narrative_consistency": "Narrative Consistency",
    "earnings_quality": "Earnings Quality",
}
# One component is enough to give a score (e.g. an Indian bank with no SEC filings or
# call transcript); the coverage note then labels it as limited evidence.
MIN_COMPONENTS = 1


def zone_for(score: int) -> str:
    if score >= 70:
        return "Credible"
    if score >= 40:
        return "Suspicious"
    return "Deceptive"


def interpolate(x: float, points: list[tuple[float, float]]) -> float:
    """Piecewise-linear score from (x, score) points sorted by x; clamped at the ends."""
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def _money(v: float) -> str:
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e9:
        return f"{sign}${a / 1e9:.1f}B"
    if a >= 1e6:
        return f"{sign}${a / 1e6:.0f}M"
    return f"{sign}${a:,.0f}"


# ──────────────────────────────────────────────
#  Components
# ──────────────────────────────────────────────

def financial_health(z: ZScoreResult) -> tuple[int, str]:
    """Z-Score mapped onto 0-100 within its zone: Distress 15-40, Gray 40-70, Safe 70-100."""
    safe, distress = z.safe_threshold, z.distress_threshold
    if z.score > safe:
        # Full marks 3 points above the Safe threshold
        score = 70 + 30 * min(1.0, (z.score - safe) / 3.0)
    elif z.score > distress:
        score = 40 + 30 * (z.score - distress) / (safe - distress)
    else:
        floor = distress - 1.5
        score = 15 + 25 * max(0.0, (z.score - floor) / 1.5)
    return int(round(score)), f"Z-Score {z.score:.2f} ({z.zone} zone, {z.model_label.split(' —')[0]})."


def bank_health(fin: FinancialData) -> tuple[int, str, str] | None:
    """Financial health for banks/insurers, where the Altman Z-Score doesn't apply.

    Capital strength (equity / total assets — the idea behind bank leverage
    ratios, typically 6-12% for large banks) weighted 60%, return on assets
    (about 1% is good for a bank) 40%.

    Returns (score, detail, zone) — zone uses the Safe/Gray/Distress wording so
    the narrative-consistency check works the same way as for the Z-Score.
    """
    if fin.total_assets <= 0:
        return None
    equity_ratio = (fin.total_assets - fin.total_liabilities) / fin.total_assets
    capital = interpolate(equity_ratio, [(0.03, 20), (0.05, 45), (0.08, 70), (0.10, 85), (0.13, 100)])
    detail = f"Capital strength: equity {equity_ratio * 100:.1f}% of assets"
    if fin.net_income is not None:
        roa = fin.net_income / fin.total_assets
        returns = interpolate(roa, [(-0.005, 15), (0.0, 35), (0.005, 55), (0.01, 80), (0.015, 100)])
        score = 0.6 * capital + 0.4 * returns
        detail += f", return on assets {roa * 100:.2f}%"
    else:
        score = capital
    score = int(round(score))
    zone = "Safe" if score >= 70 else "Gray" if score >= 40 else "Distress"
    return score, detail + " (Altman Z-Score doesn't apply to financial companies).", zone


def filing_language(filing: ForensicResult) -> tuple[int, str] | None:
    """100 minus hedging, evasion and verified red-flag penalties from the filing text."""
    b = filing.truth_score_breakdown
    if b is None:
        return None
    penalty = b.hedging_penalty + b.evasion_penalty + b.red_flag_penalty
    la = filing.linguistic_analysis
    verified = sum(1 for f in filing.red_flags if f.verified)
    source = filing.language_source or "10-K MD&A"
    detail = f"{source}: hedging {la.hedging_score:.1f}, evasion {la.evasion_score:.1f}"
    detail += f", {verified} verified AI red flag(s)." if b.basis == "ai+heuristic" else "."
    return int(round(max(0.0, 100.0 - penalty))), detail


def call_candor(call: EarningsCallAnalysis | None) -> tuple[int, str] | None:
    if call is None or call.candor_score is None:
        return None
    rate = f"{(call.deflection_rate or 0) * 100:.0f}%"
    detail = f"{call.analyst_questions} analyst questions, {rate} deflected"
    if call.tone_shift is not None:
        detail += f", tone shift {call.tone_shift:+.2f}"
    return call.candor_score, detail + f" ({call.quarter or call.date} call)."


def narrative_consistency(
    zone: str | None, filing: ForensicResult, call: EarningsCallAnalysis | None,
) -> tuple[int, str, str | None] | None:
    """Does management's tone match the numbers? Worst gap across filing and call tone.

    `zone` is the Safe/Gray/Distress reading of financial health. Returns
    (score, detail, critical_reason) — critical_reason is set for a bullish
    narrative from a Distress-zone company.
    """
    if zone is None:
        return None
    tones: list[tuple[str, str]] = []
    if filing.linguistic_analysis.sentiment in {"bullish", "neutral", "bearish"}:
        tones.append((filing.language_source or "10-K MD&A", filing.linguistic_analysis.sentiment))
    if call and call.available and call.source == "alpha_vantage":
        seg = call.qa or call.prepared
        if seg and seg.sentiment in {"bullish", "neutral", "bearish"}:
            tones.append(("earnings call", seg.sentiment))
    if not tones:
        return None

    worst_penalty, worst_reason, critical = 0.0, None, None
    for source, sentiment in tones:
        alert, reason, penalty = detect_sentiment_gap(sentiment, zone)
        if penalty > worst_penalty:
            worst_penalty, worst_reason = penalty, f"{source} tone is {sentiment} while financial health is {zone}"
            if alert:
                critical = reason
    score = int(round(100 - 2 * worst_penalty))   # 100 consistent, 70 mild optimism, 20 contradiction
    described = ", ".join(f"{s} {t}" for s, t in tones)
    detail = f"Tone ({described}) vs {zone} financial health: " + (worst_reason + "." if worst_reason else "consistent.")
    return score, detail, critical


def earnings_quality(fin: FinancialData | None) -> tuple[int, str] | None:
    """Sloan (1996) accruals: (net income - operating cash flow) / total assets.

    Earnings far above cash generated are the classic warning sign of
    aggressive accounting. Cash flow at or above earnings scores 100.
    Not applied to banks/insurers, whose operating cash flow is dominated by
    lending and trading flows rather than earnings.
    """
    if fin is None or fin.net_income is None or fin.operating_cash_flow is None or fin.total_assets <= 0:
        return None
    if is_financial_company(fin):
        return None
    accruals = (fin.net_income - fin.operating_cash_flow) / fin.total_assets
    score = 100.0 if accruals <= 0 else max(10.0, 100.0 - accruals * 400)
    if fin.net_income > 0 and fin.operating_cash_flow < 0:
        score = min(score, 30.0)   # reported profit while burning cash
    detail = (
        f"Operating cash flow {_money(fin.operating_cash_flow)} vs net income {_money(fin.net_income)} "
        f"(accruals {accruals * 100:+.1f}% of assets)."
    )
    return int(round(score)), detail


def health_reading(z: ZScoreResult | None, fin: FinancialData | None) -> tuple[int, str, str] | None:
    """(score, detail, Safe/Gray/Distress zone) from the Z-Score, or bank capital for financials."""
    if z is not None:
        score, detail = financial_health(z)
        return score, detail, z.zone
    if fin is not None and is_financial_company(fin):
        return bank_health(fin)
    return None


# ──────────────────────────────────────────────
#  Composite
# ──────────────────────────────────────────────

def compute_credibility(
    z: ZScoreResult | None,
    filing: ForensicResult,
    call: EarningsCallAnalysis | None,
    fin: FinancialData | None,
) -> tuple[int | None, str | None, list[TruthComponent], str | None]:
    """Weighted Credibility Index.

    Returns:
        (score, zone, components, critical_reason). score/zone are None when
        fewer than MIN_COMPONENTS pieces of evidence are available.
    """
    raw: dict[str, tuple[int, str]] = {}
    zone = None
    if (health := health_reading(z, fin)) is not None:
        raw["financial_health"] = health[:2]
        zone = health[2]
    if (lang := filing_language(filing)) is not None:
        raw["filing_language"] = lang
    if (candor := call_candor(call)) is not None:
        raw["call_candor"] = candor
    critical = None
    if (consistency := narrative_consistency(zone, filing, call)) is not None:
        raw["narrative_consistency"] = consistency[:2]
        critical = consistency[2]
    if (quality := earnings_quality(fin)) is not None:
        raw["earnings_quality"] = quality

    total_weight = sum(WEIGHTS[k] for k in raw)
    components = [
        TruthComponent(
            key=key,
            label=LABELS[key],
            score=max(0, min(100, score)),
            weight=WEIGHTS[key],
            effective_weight=round(WEIGHTS[key] / total_weight, 3) if total_weight else 0.0,
            detail=detail,
        )
        for key, (score, detail) in raw.items()
    ]
    if len(components) < MIN_COMPONENTS:
        return None, None, components, critical

    score = int(round(sum(c.score * c.effective_weight for c in components)))
    return score, zone_for(score), components, critical


MISSING_REASONS = {
    "financial_health": "no financial data",
    "filing_language": "no 10-K MD&A or earnings release text",
    "call_candor": "no earnings call Q&A",
    "narrative_consistency": "no tone or financial health to compare",
    "earnings_quality": "no cash-flow data (or a financial company)",
}


def coverage_note(components: list[TruthComponent]) -> str | None:
    """Which evidence was missing, for display under the score."""
    present = {c.key for c in components}
    missing = [MISSING_REASONS[k] for k in WEIGHTS if k not in present]
    if not missing:
        return None
    if len(present) < MIN_COMPONENTS:
        return f"Not enough evidence for a Truth Score ({'; '.join(missing)})."
    if len(present) < 3:
        return (
            f"Limited evidence: scored on {len(present)} of 5 components only "
            f"({'; '.join(missing)}). Treat this score with caution."
        )
    return f"Scored on {len(present)} of 5 components ({'; '.join(missing)}); weights re-balanced."
