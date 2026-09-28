"""
Alpha-Guard — Risk Register
============================
Collects every warning raised by the individual analyses into one ranked
list for the report, so a reader sees all issues in one place.
"""

from models import (
    EarningsCallAnalysis,
    ForensicResult,
    InvestmentConviction,
    MonteCarloResult,
    RiskItem,
    ZScoreResult,
)

_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_risk_register(
    z: ZScoreResult | None,
    forensic: ForensicResult,
    call: EarningsCallAnalysis | None,
    conviction: InvestmentConviction | None,
    monte_carlo: MonteCarloResult | None,
) -> list[RiskItem]:
    items: list[RiskItem] = []

    def add(severity: str, area: str, finding: str) -> None:
        if not any(i.finding == finding for i in items):
            items.append(RiskItem(severity=severity, area=area, finding=finding))

    # Deception / narrative
    if forensic.deception_alert and forensic.deception_reason:
        add("high", "Narrative consistency", forensic.deception_reason)

    # Financial health
    if z is not None:
        if z.zone == "Distress":
            add("high", "Financial health", f"Altman Z-Score {z.score:.2f} is in the Distress zone (elevated bankruptcy risk).")
        elif z.zone == "Gray":
            add("medium", "Financial health", f"Altman Z-Score {z.score:.2f} is in the Gray zone.")

    # Truth Score components
    breakdown = forensic.truth_score_breakdown
    for c in (breakdown.components if breakdown else []):
        if c.key == "financial_health" and z is not None:
            continue  # already covered by the Z-Score entries above
        if c.key == "narrative_consistency" and forensic.deception_alert:
            continue  # already covered by the deception alert
        if c.score < 50:
            add("high", c.label, c.detail)
        elif c.score < 70:
            add("medium", c.label, c.detail)

    # AI red flags with verified quotes
    for flag in forensic.red_flags:
        if flag.verified and flag.severity >= 7:
            add("high", "Filing language (AI)", f"{flag.explanation} — “{flag.sentence[:160]}”")
        elif flag.verified and flag.severity >= 4:
            add("medium", "Filing language (AI)", f"{flag.explanation} — “{flag.sentence[:160]}”")

    # Earnings call
    if call and call.available:
        answered = max(call.analyst_questions, 1)
        brief = sum(1 for e in call.exchanges if e.brief)
        for flag in call.flags:
            if flag.startswith("Press release only"):
                continue
            if "Distress" in flag:
                if forensic.deception_alert:
                    continue  # same contradiction as the deception alert
                severity = "high"
            elif flag.startswith("Executives deflected"):
                severity = "medium" if (call.deflection_rate or 0) >= 0.2 else "low"
            elif "under 40 words" in flag:
                severity = "medium" if brief / answered >= 0.25 else "low"
            else:
                severity = "medium"
            add(severity, "Earnings call", flag)

    # Investment case
    if conviction:
        for pillar in conviction.pillars:
            if pillar.key == "valuation" and pillar.score < 50:
                add("low", "Valuation", pillar.detail)
            elif pillar.key in {"profitability", "growth"} and pillar.score < 50:
                add("medium", pillar.label, pillar.detail)

    # Stress test
    if monte_carlo and monte_carlo.probability_of_decline is not None:
        p = monte_carlo.probability_of_decline
        if p >= 0.25:
            add("high" if p >= 0.4 else "medium", "Revenue stress test",
                f"{p:.0%} of simulated paths end with revenue more than 20% below today's.")

    # Evidence coverage
    if forensic.analysis_note and forensic.analysis_note.startswith("Limited evidence"):
        add("low", "Evidence coverage", forensic.analysis_note)

    return sorted(items, key=lambda i: _ORDER[i.severity])
