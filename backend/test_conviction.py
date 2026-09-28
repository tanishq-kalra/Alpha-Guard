"""
Alpha-Guard — Investment Conviction Tests
==========================================
Pillar scoring, re-weighting, the deception cap and verdicts. No network.
"""

import pytest

import conviction as cv
import scraper
from models import FinancialData, ForensicResult, LinguisticAnalysis, ZScoreComponents, ZScoreResult


def _z(score=9.1, zone="Safe") -> ZScoreResult:
    return ZScoreResult(
        ticker="T", score=score, zone=zone, interpretation="",
        components=ZScoreComponents(
            x1_working_capital_to_total_assets=0, x2_retained_earnings_to_total_assets=0,
            x3_ebit_to_total_assets=0, x4_market_cap_to_total_liabilities=0, x5_revenue_to_total_assets=0,
        ),
    )


def _forensic(truth=95, alert=False) -> ForensicResult:
    return ForensicResult(
        truth_score=truth, truth_zone="Credible" if truth and truth >= 70 else "Suspicious",
        deception_alert=alert,
        linguistic_analysis=LinguisticAnalysis(hedging_score=0, evasion_score=0, sentiment="neutral", sentiment_confidence=0),
    )


def _fin(**overrides) -> FinancialData:
    base = dict(
        ticker="T", total_assets=1000.0, current_assets=1, current_liabilities=1, retained_earnings=1, ebit=1,
        total_liabilities=500.0, revenue=800.0, revenue_prior_year=700.0, net_income=160.0,
        operating_cash_flow=180.0, market_cap=3200.0,
    )
    return FinancialData(**{**base, **overrides})


class TestPillars:

    def test_profitability(self):
        # margin 20% -> 100, ROA 16% -> 100
        assert cv.profitability(_fin())[0] == 100
        # margin 0%, ROA 0% -> 40
        assert cv.profitability(_fin(net_income=0.0))[0] == 40

    @pytest.mark.parametrize("prior, expected", [(640.0, 100), (700.0, 91), (800.0, 55), (1000.0, 15)])
    def test_growth(self, prior, expected):
        assert cv.growth(_fin(revenue_prior_year=prior))[0] == expected

    def test_growth_missing(self):
        assert cv.growth(_fin(revenue_prior_year=None)) is None

    @pytest.mark.parametrize("cap, expected, word", [(1600.0, 100, "attractive"), (4800.0, 65, "expensive"), (16000.0, 15, "very expensive")])
    def test_valuation(self, cap, expected, word):
        score, detail, metric = cv.valuation(_fin(market_cap=cap))
        assert score == expected and word in detail and metric.startswith("P/E")

    def test_loss_maker_valuation(self):
        assert cv.valuation(_fin(net_income=-10.0))[0] == 20

    def test_interpolation(self):
        pts = [(0, 0), (10, 100)]
        assert cv._interpolate(-5, pts) == 0 and cv._interpolate(5, pts) == 50 and cv._interpolate(50, pts) == 100


class TestComposite:

    def test_strong_company(self):
        c = cv.compute_conviction(_z(), _forensic(97), None, _fin())
        assert c.score >= 80 and c.verdict == "High conviction"
        assert len(c.pillars) == 6 and not c.concerns and c.strengths
        assert "convinced" in c.headline and "Not financial advice" in c.disclaimer
        assert abs(sum(p.effective_weight for p in c.pillars) - 1) < 0.01

    def test_weak_company(self):
        c = cv.compute_conviction(
            _z(0.5, "Distress"), _forensic(35),
            None, _fin(net_income=-50.0, operating_cash_flow=-80.0, revenue_prior_year=1000.0),
        )
        assert c.score < 50 and c.verdict == "Low conviction" and len(c.concerns) >= 3

    def test_deception_alert_caps_score(self):
        c = cv.compute_conviction(_z(), _forensic(90, alert=True), None, _fin())
        assert c.score == cv.DECEPTION_CAP and c.capped_reason
        assert c.concerns[0].startswith("Deception alert")

    def test_too_little_data(self):
        c = cv.compute_conviction(None, _forensic(None), None, None)
        assert c.score is None and c.verdict is None and "Not enough data" in c.headline

    @pytest.mark.parametrize("score, verdict", [
        (80, "High conviction"), (79, "Moderate conviction"), (65, "Moderate conviction"),
        (64, "Neutral — watch"), (50, "Neutral — watch"), (49, "Low conviction"),
    ])
    def test_verdicts(self, score, verdict):
        assert cv.verdict_for(score) == verdict


class TestPriorYearRevenue:

    def test_prior_fiscal_year_end(self):
        facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
            {"val": 1, "end": "2024-09-28", "form": "10-K", "filed": "2024-11-01"},
            {"val": 1, "end": "2025-09-27", "form": "10-K", "filed": "2025-11-01"},
            {"val": 1, "end": "2025-03-29", "form": "10-K", "filed": "2025-11-01"},  # not a year apart
        ]}}}}}
        assert scraper.prior_fiscal_year_end(facts, "2025-09-27") == "2024-09-28"
        assert scraper.prior_fiscal_year_end(facts, "2024-09-28") is None
