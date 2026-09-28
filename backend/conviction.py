"""
Alpha-Guard — Investment Conviction
====================================
"How convinced are we that this is a sound company to invest in?"

Six pillars, each 0-100, combined by weight:

  Pillar                  Weight  Evidence
  financial_strength        20%   Altman Z-Score (bankruptcy risk); capital strength for banks
  profitability             20%   Net margin and return on assets
  growth                    15%   Revenue growth vs the prior fiscal year
  credibility               20%   Truth Score (can management's story be trusted?)
  valuation                 15%   Price-to-earnings (are you overpaying?)
  earnings_quality          10%   Operating cash flow vs net income (accruals)

Missing pillars are left out and the rest re-weighted; at least three are
required. A deception alert caps conviction at 45: a company whose narrative
contradicts its numbers is not an investment case, however good the numbers.

Educational, rule-based output — not financial advice.
"""

from models import (
    ConvictionPillar,
    EarningsCallAnalysis,
    FinancialData,
    ForensicResult,
    InvestmentConviction,
    ZScoreResult,
)
from truth_score import earnings_quality, health_reading, interpolate as _interpolate

WEIGHTS = {
    "financial_strength": 0.20,
    "profitability": 0.20,
    "growth": 0.15,
    "credibility": 0.20,
    "valuation": 0.15,
    "earnings_quality": 0.10,
}
LABELS = {
    "financial_strength": "Financial Strength",
    "profitability": "Profitability",
    "growth": "Growth",
    "credibility": "Management Credibility",
    "valuation": "Valuation",
    "earnings_quality": "Earnings Quality",
}
MIN_PILLARS = 3
DECEPTION_CAP = 45


def verdict_for(score: int) -> str:
    if score >= 80:
        return "High conviction"
    if score >= 65:
        return "Moderate conviction"
    if score >= 50:
        return "Neutral — watch"
    return "Low conviction"


# ──────────────────────────────────────────────
#  Pillars
# ──────────────────────────────────────────────

def profitability(fin: FinancialData) -> tuple[int, str, str] | None:
    if fin.net_income is None or fin.revenue <= 0 or fin.total_assets <= 0:
        return None
    margin = fin.net_income / fin.revenue
    roa = fin.net_income / fin.total_assets
    margin_score = _interpolate(margin, [(-0.10, 10), (0.0, 40), (0.05, 60), (0.10, 80), (0.20, 100)])
    roa_score = _interpolate(roa, [(-0.05, 10), (0.0, 40), (0.05, 75), (0.10, 100)])
    score = int(round((margin_score + roa_score) / 2))
    return (
        score,
        f"Net margin {margin * 100:.1f}% and return on assets {roa * 100:.1f}%.",
        f"Net margin {margin * 100:.1f}%",
    )


def growth(fin: FinancialData) -> tuple[int, str, str] | None:
    if not fin.revenue_prior_year or fin.revenue_prior_year <= 0:
        return None
    g = fin.revenue / fin.revenue_prior_year - 1
    score = _interpolate(g, [(-0.15, 15), (-0.05, 40), (0.0, 55), (0.05, 70), (0.10, 85), (0.20, 100)])
    direction = "grew" if g >= 0 else "shrank"
    return int(round(score)), f"Revenue {direction} {abs(g) * 100:.1f}% year on year.", f"Revenue {g * 100:+.1f}%"


def valuation(fin: FinancialData) -> tuple[int, str, str] | None:
    if fin.market_cap is None or fin.net_income is None:
        return None
    if fin.net_income <= 0:
        return 20, "Loss-making, so there are no earnings to support the price.", "P/E n/a (loss)"
    pe = fin.market_cap / fin.net_income
    score = _interpolate(pe, [(10, 100), (20, 85), (30, 65), (45, 45), (70, 25), (100, 15)])
    view = "attractive" if pe < 20 else "fair" if pe < 30 else "expensive" if pe < 50 else "very expensive"
    return int(round(score)), f"Price-to-earnings of {pe:.1f}x looks {view}.", f"P/E {pe:.1f}x"


# ──────────────────────────────────────────────
#  Composite
# ──────────────────────────────────────────────

def compute_conviction(
    z: ZScoreResult | None,
    forensic: ForensicResult,
    call: EarningsCallAnalysis | None,
    fin: FinancialData | None,
) -> InvestmentConviction:
    raw: dict[str, tuple[int, str, str | None]] = {}

    if (health := health_reading(z, fin)) is not None:
        score, detail, _ = health
        metric = f"Z-Score {z.score:.2f}" if z is not None else "Bank capital"
        raw["financial_strength"] = (score, detail, metric)
    if fin is not None:
        for key, fn in (("profitability", profitability), ("growth", growth), ("valuation", valuation)):
            if (result := fn(fin)) is not None:
                raw[key] = result
        if (quality := earnings_quality(fin)) is not None:
            raw["earnings_quality"] = (quality[0], quality[1], None)
    if forensic.truth_score is not None:
        raw["credibility"] = (
            forensic.truth_score,
            f"Truth Score {forensic.truth_score} ({forensic.truth_zone}) across filings, calls and financials.",
            f"Truth Score {forensic.truth_score}",
        )

    total = sum(WEIGHTS[k] for k in raw)
    pillars = [
        ConvictionPillar(
            key=key, label=LABELS[key], score=max(0, min(100, s)), weight=WEIGHTS[key],
            effective_weight=round(WEIGHTS[key] / total, 3) if total else 0.0,
            detail=detail, metric=metric,
        )
        for key, (s, detail, metric) in raw.items()
    ]

    if len(pillars) < MIN_PILLARS:
        return InvestmentConviction(
            headline="Not enough data to form an investment view.",
            pillars=pillars,
        )

    score = int(round(sum(p.score * p.effective_weight for p in pillars)))
    capped_reason = None
    if forensic.deception_alert and score > DECEPTION_CAP:
        score = DECEPTION_CAP
        capped_reason = (
            "Capped at 45: management's narrative contradicts the financial numbers (deception alert)."
        )

    strengths = [f"{p.label}: {p.detail}" for p in sorted(pillars, key=lambda p: -p.score) if p.score >= 75]
    concerns = [f"{p.label}: {p.detail}" for p in sorted(pillars, key=lambda p: p.score) if p.score < 50]
    if forensic.deception_alert:
        concerns.insert(0, "Deception alert: management's tone contradicts the Z-Score.")
    if call and call.available and call.deflection_rate and call.deflection_rate >= 0.2:
        concerns.append(f"Executives deflected {call.deflection_rate * 100:.0f}% of analyst questions on the latest call.")

    verdict = verdict_for(score)
    headline = {
        "High conviction": f"We are {score}% convinced this is a fundamentally sound company to invest in.",
        "Moderate conviction": f"We are {score}% convinced — a solid company with some points to watch.",
        "Neutral — watch": f"We are {score}% convinced — mixed signals; wait for a clearer picture.",
        "Low conviction": f"We are only {score}% convinced — the risks outweigh the positives right now.",
    }[verdict]

    return InvestmentConviction(
        score=score,
        verdict=verdict,
        headline=headline,
        pillars=pillars,
        strengths=strengths,
        concerns=concerns,
        capped_reason=capped_reason,
    )
