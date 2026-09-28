"""
Alpha-Guard — Truth Score (Credibility Index) Tests
====================================================
Each component in isolation, weight re-normalisation, and end-to-end
profiles of healthy vs troubled companies. No network access.
"""

import pytest

import truth_score as ts
from models import (
    CallSegmentMetrics,
    EarningsCallAnalysis,
    FinancialData,
    ForensicResult,
    LinguisticAnalysis,
    RedFlag,
    TruthScoreBreakdown,
    ZScoreComponents,
    ZScoreResult,
)


def _z(score: float, zone: str, safe=2.99, distress=1.81) -> ZScoreResult:
    return ZScoreResult(
        ticker="T", score=score, zone=zone, interpretation="",
        components=ZScoreComponents(
            x1_working_capital_to_total_assets=0, x2_retained_earnings_to_total_assets=0,
            x3_ebit_to_total_assets=0, x4_market_cap_to_total_liabilities=0, x5_revenue_to_total_assets=0,
        ),
        safe_threshold=safe, distress_threshold=distress,
    )


def _filing(sentiment="neutral", hedging_pen=0.0, evasion_pen=0.0, flag_pen=0.0, analysed=True, flags=()):
    return ForensicResult(
        linguistic_analysis=LinguisticAnalysis(
            hedging_score=15 + hedging_pen, evasion_score=2 + evasion_pen / 2,
            sentiment=sentiment if analysed else "unknown", sentiment_confidence=0,
        ),
        red_flags=list(flags),
        truth_score_breakdown=TruthScoreBreakdown(
            hedging_penalty=hedging_pen, evasion_penalty=evasion_pen, red_flag_penalty=flag_pen, basis="heuristic",
        ) if analysed else None,
    )


def _call(candor=100, sentiment="neutral", questions=10, deflection=0.0):
    seg = CallSegmentMetrics(words=3000, hedging_score=5, evasion_score=3, sentiment=sentiment, net_tone=0.2)
    return EarningsCallAnalysis(
        available=True, source="alpha_vantage", quarter="2026Q2", prepared=seg, qa=seg,
        analyst_questions=questions, deflection_rate=deflection, tone_shift=0.0, candor_score=candor,
    )


def _fin(ni=100.0, cfo=110.0, assets=1000.0) -> FinancialData:
    return FinancialData(
        ticker="T", total_assets=assets, current_assets=1, current_liabilities=1, retained_earnings=1,
        ebit=1, total_liabilities=1, revenue=1, net_income=ni, operating_cash_flow=cfo,
    )


class TestFinancialHealth:

    @pytest.mark.parametrize("score, zone, expected", [
        (9.10, "Safe", 100),      # AAPL-like: far above the threshold
        (2.99 + 1.5, "Safe", 85),
        (3.00, "Safe", 70),
        (2.40, "Gray", 55),       # mid-Gray
        (1.81, "Distress", 40),
        (0.79, "Distress", 23),   # Ford-like
        (-5.0, "Distress", 15),
    ])
    def test_scaling(self, score, zone, expected):
        assert ts.financial_health(_z(score, zone))[0] == expected

    def test_uses_model_thresholds(self):
        # Z'' thresholds: 2.60 / 1.10
        assert ts.financial_health(_z(2.60 + 3, "Safe", safe=2.60, distress=1.10))[0] == 100


class TestEarningsQuality:

    def test_cash_backed_earnings_score_100(self):
        assert ts.earnings_quality(_fin(ni=100, cfo=120))[0] == 100

    def test_high_accruals_penalised(self):
        # accruals (100 - 50) / 1000 = 5% of assets -> 100 - 20
        assert ts.earnings_quality(_fin(ni=100, cfo=50))[0] == 80

    def test_profit_while_burning_cash(self):
        assert ts.earnings_quality(_fin(ni=10, cfo=-5, assets=10_000))[0] == 30

    def test_missing_data(self):
        assert ts.earnings_quality(_fin(ni=None)) is None
        assert ts.earnings_quality(None) is None


class TestConsistency:

    def test_consistent_tone(self):
        score, _, critical = ts.narrative_consistency("Safe", _filing("bullish"), _call(sentiment="bullish"))
        assert score == 100 and critical is None

    def test_mild_optimism(self):
        score, detail, critical = ts.narrative_consistency("Gray", _filing("bullish"), None)
        assert score == 70 and critical is None and "Gray" in detail

    def test_bullish_call_in_distress_is_critical(self):
        score, detail, critical = ts.narrative_consistency("Distress", _filing("bearish"), _call(sentiment="bullish"))
        assert score == 20 and "earnings call" in detail and critical and "CRITICAL" in critical

    def test_needs_tone_and_zscore(self):
        assert ts.narrative_consistency(None, _filing("bullish"), None) is None
        assert ts.narrative_consistency("Safe", _filing(analysed=False), None) is None


class TestComposite:

    def test_healthy_company_scores_high(self):
        score, zone, comps, critical = ts.compute_credibility(_z(9.1, "Safe"), _filing("neutral"), _call(), _fin())
        assert score >= 95 and zone == "Credible" and critical is None
        assert len(comps) == 5
        assert abs(sum(c.effective_weight for c in comps) - 1) < 0.01

    def test_troubled_company_scores_low(self):
        flags = [RedFlag(sentence="x", category="evasion", severity=9, explanation="", verified=True)]
        score, zone, _, critical = ts.compute_credibility(
            _z(0.5, "Distress"),
            _filing("bullish", hedging_pen=20, evasion_pen=15, flag_pen=25, flags=flags),
            _call(candor=45, sentiment="bullish", deflection=0.4),
            _fin(ni=100, cfo=-20),
        )
        assert score < 40 and zone == "Deceptive" and critical

    def test_missing_components_are_rebalanced(self):
        score, _, comps, _ = ts.compute_credibility(_z(9.1, "Safe"), _filing(analysed=False), None, _fin())
        assert [c.key for c in comps] == ["financial_health", "earnings_quality"]
        assert [c.effective_weight for c in comps] == [0.667, 0.333]
        assert score == 100

    def test_single_component_is_limited_evidence(self):
        score, zone, comps, _ = ts.compute_credibility(_z(9.1, "Safe"), _filing(analysed=False), None, None)
        assert score == 100 and zone == "Credible" and len(comps) == 1
        assert ts.coverage_note(comps).startswith("Limited evidence")

    def test_no_evidence_gives_no_score(self):
        score, zone, comps, _ = ts.compute_credibility(None, _filing(analysed=False), None, None)
        assert score is None and zone is None and comps == []

    def test_press_release_has_no_candor_component(self):
        call = _call()
        call.candor_score = None
        _, _, comps, _ = ts.compute_credibility(_z(5, "Safe"), _filing(), call, None)
        assert "call_candor" not in [c.key for c in comps]

    def test_coverage_note(self):
        _, _, comps, _ = ts.compute_credibility(_z(9.1, "Safe"), _filing(analysed=False), None, _fin())
        note = ts.coverage_note(comps)
        assert note.startswith("Limited evidence") and "2 of 5" in note and "MD&A" in note
        _, _, full, _ = ts.compute_credibility(_z(9.1, "Safe"), _filing(), _call(), _fin())
        assert ts.coverage_note(full) is None

    @pytest.mark.parametrize("score, zone", [(70, "Credible"), (69, "Suspicious"), (40, "Suspicious"), (39, "Deceptive")])
    def test_zones(self, score, zone):
        assert ts.zone_for(score) == zone


class TestFinancialCompanies:
    """Banks/insurers: no Altman Z-Score, so capital strength stands in for it."""

    def _bank(self, equity=0.085, roa=0.013, **extra):
        assets = 4_000_000.0
        return _fin(ni=roa * assets, cfo=-50_000.0, assets=assets).model_copy(update={
            "total_liabilities": assets * (1 - equity), "sic_code": 6021, **extra,
        })

    def test_bank_health_scoring(self):
        score, detail, zone = ts.bank_health(self._bank())
        # capital 8.5% -> 73.75, ROA 1.3% -> 92 ; 0.6 x 73.75 + 0.4 x 92 = 81
        assert score == 81 and zone == "Safe"
        assert "equity 8.5%" in detail and "doesn't apply" in detail

    def test_thin_capital_is_distress(self):
        assert ts.bank_health(self._bank(equity=0.03, roa=-0.004))[2] == "Distress"

    def test_bank_is_scored_without_zscore(self):
        score, zone, comps, _ = ts.compute_credibility(None, _filing("neutral"), _call(), self._bank())
        keys = [c.key for c in comps]
        assert score is not None and zone == "Credible"
        assert keys == ["financial_health", "filing_language", "call_candor", "narrative_consistency"]
        assert "earnings_quality" not in keys   # accruals don't apply to banks

    def test_non_financial_without_zscore_has_no_health(self):
        assert ts.health_reading(None, _fin()) is None

    def test_press_release_language_source_in_detail(self):
        filing = _filing("neutral")
        filing.language_source = "Earnings press release (SEC 8-K, 2026-07-14)"
        assert ts.filing_language(filing)[1].startswith("Earnings press release")
