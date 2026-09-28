"""
Alpha-Guard — Research Report Tests
====================================
Multi-year history, company-specific stress-test assumptions, the risk
register and a full PDF build. No network access.
"""

import math

import pytest

import scraper
from forensic_analyzer import company_stress_test
from models import (
    EarningsCallAnalysis,
    FinancialData,
    ForensicAuditResponse,
    ForensicResult,
    HistoryPoint,
    InvestmentConviction,
    LinguisticAnalysis,
    MonteCarloResult,
    RiskItem,
    TruthComponent,
    TruthScoreBreakdown,
    ZScoreComponents,
    ZScoreResult,
)
from report_generator import generate_pdf_report
from risk_engine import DEFAULT_GROWTH_MEAN, growth_parameters_from_history
from risk_register import build_risk_register


def _fact(val, end, start=None):
    e = {"val": val, "end": end, "form": "10-K", "filed": "2026-01-01"}
    if start:
        e["start"] = start
    return e


def _history(revenues: list[float]) -> list[HistoryPoint]:
    """Newest first, one year apart."""
    return [HistoryPoint(fiscal_period_end=f"{2025 - i}-12-31", revenue=r) for i, r in enumerate(revenues)]


class TestHistory:

    def test_build_history_walks_back_fiscal_years(self):
        years = ["2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]
        facts = {"facts": {"us-gaap": {
            "Assets": {"units": {"USD": [_fact(1000 + i, y) for i, y in enumerate(years)]}},
            "Liabilities": {"units": {"USD": [_fact(500, y) for y in years]}},
            "Revenues": {"units": {"USD": [_fact(100 * (i + 1), y, start=f"{y[:4]}-01-01") for i, y in enumerate(years)]}},
            "NetIncomeLoss": {"units": {"USD": [_fact(10 * (i + 1), y, start=f"{y[:4]}-01-01") for i, y in enumerate(years)]}},
        }}}
        history = scraper.build_history(facts, "2025-12-31", ["Revenues"])
        assert [h.fiscal_period_end for h in history] == list(reversed(years))
        assert [h.revenue for h in history] == [500, 400, 300, 200, 100]
        assert history[0].net_income == 50 and history[0].total_liabilities == 500

    def test_history_stops_at_gap(self):
        facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [_fact(1, "2025-12-31"), _fact(1, "2022-12-31")]}}}}}
        assert len(scraper.build_history(facts, "2025-12-31", ["Revenues"])) == 1


class TestGrowthParameters:

    def test_steady_growth(self):
        drift, vol, source = growth_parameters_from_history(_history([121, 110, 100]))
        assert vol == 0.05   # zero observed volatility is floored
        assert math.isclose(drift, math.log(1.1) + 0.5 * 0.05 ** 2, rel_tol=1e-9)
        assert "3 years" in source and "FY2023–FY2025" in source

    def test_volatile_history(self):
        drift, vol, _ = growth_parameters_from_history(_history([100, 150, 90, 120]))
        assert 0.3 < vol <= 0.5

    def test_extreme_growth_is_capped(self):
        drift, vol, _ = growth_parameters_from_history(_history([1000, 100, 10]))
        assert drift <= 0.35 + 0.5 * vol ** 2 + 1e-9

    def test_no_history_uses_defaults(self):
        drift, vol, source = growth_parameters_from_history(_history([100]))
        assert drift == DEFAULT_GROWTH_MEAN and "Default" in source

    def test_company_stress_test_is_reproducible(self):
        fin = FinancialData(ticker="T", total_assets=1, total_liabilities=1, retained_earnings=0, ebit=0,
                            revenue=100.0, history=_history([100, 90, 85]))
        a, b = company_stress_test("T", fin), company_stress_test("T", fin)
        assert a.median_final_revenue == b.median_final_revenue
        assert a.parameter_source.startswith("Company history")


def _z(zone="Safe", score=5.0):
    return ZScoreResult(ticker="T", score=score, zone=zone, interpretation="", components=ZScoreComponents(
        x1_working_capital_to_total_assets=0.1, x2_retained_earnings_to_total_assets=0.2,
        x3_ebit_to_total_assets=0.1, x4_market_cap_to_total_liabilities=2, x5_revenue_to_total_assets=1,
    ), weights={"x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0})


def _forensic(alert=False, comps=()):
    return ForensicResult(
        truth_score=62, truth_zone="Suspicious", deception_alert=alert,
        deception_reason="CRITICAL: narrative bullish while Distress" if alert else None,
        linguistic_analysis=LinguisticAnalysis(hedging_score=20, evasion_score=3, sentiment="bullish",
                                               sentiment_confidence=0, total_words_analyzed=5000),
        truth_score_breakdown=TruthScoreBreakdown(basis="heuristic", components=list(comps)),
    )


class TestRiskRegister:

    def test_collects_and_ranks(self):
        comps = [TruthComponent(key="call_candor", label="Earnings Call Candor", score=45, weight=0.2, detail="Evasive call.")]
        call = EarningsCallAnalysis(available=True, source="alpha_vantage", deflection_rate=0.3,
                                    flags=["Executives deflected 3 of 10 analyst questions."])
        mc = MonteCarloResult(ticker="T", num_simulations=1000, time_horizon_years=5, probability_of_decline=0.45)
        items = build_risk_register(_z("Distress", 1.0), _forensic(True, comps), call, None, mc)
        assert [i.severity for i in items] == sorted([i.severity for i in items], key=["high", "medium", "low"].index)
        areas = [i.area for i in items]
        assert "Narrative consistency" in areas and "Financial health" in areas
        assert "Earnings Call Candor" in areas and "Revenue stress test" in areas
        assert next(i for i in items if i.area == "Earnings call").severity == "medium"

    def test_clean_company_has_empty_register(self):
        assert build_risk_register(_z(), _forensic(), None, None, None) == []

    def test_no_duplicates(self):
        comps = [TruthComponent(key="filing_language", label="Filing Language", score=30, weight=0.2, detail="Same.")] * 2
        items = build_risk_register(None, _forensic(False, comps), None, None, None)
        assert len(items) == 1


class TestPdf:

    def _audit(self, **overrides) -> ForensicAuditResponse:
        fin = FinancialData(
            ticker="TEST", total_assets=1000.0, current_assets=500, current_liabilities=200, retained_earnings=300,
            ebit=150, total_liabilities=400.0, revenue=800.0, net_income=120.0, operating_cash_flow=140.0,
            market_cap=2400.0, revenue_prior_year=700.0, fiscal_period_end="2025-12-31",
            history=_history([800, 700, 650, 600]),
        )
        base = dict(
            ticker="TEST", company_name="Test <Co> & Sons", timestamp="2026-01-01T00:00:00Z",
            forensic=_forensic(), data_sources=["SEC EDGAR — Financial Data"], financials=fin,
            monte_carlo=company_stress_test("TEST", fin),
            conviction=InvestmentConviction(score=81, verdict="High conviction", headline="We are 81% convinced."),
            risk_register=[RiskItem(severity="high", area="Test", finding="Something <bad> & worse")],
        )
        base["forensic"].z_score_result = _z()
        return ForensicAuditResponse(**{**base, **overrides})

    def test_full_report_builds(self):
        pdf = generate_pdf_report(self._audit())
        assert pdf.startswith(b"%PDF") and len(pdf) > 5000

    @pytest.mark.parametrize("overrides", [
        {"financials": None, "monte_carlo": None, "conviction": None, "risk_register": []},
        {"earnings_call": EarningsCallAnalysis(available=False, note="none")},
    ])
    def test_report_builds_with_missing_sections(self, overrides):
        assert generate_pdf_report(self._audit(**overrides)).startswith(b"%PDF")


class TestRiskRegisterDedup:

    def test_deception_reported_once(self):
        comps = [TruthComponent(key="narrative_consistency", label="Narrative Consistency", score=20, weight=0.15,
                                detail="Call tone bullish while Distress.")]
        call = EarningsCallAnalysis(available=True, source="alpha_vantage", analyst_questions=14,
                                    flags=["Upbeat call while the Z-Score is in the Distress zone.",
                                           "1 answer(s) were under 40 words."])
        items = build_risk_register(_z("Distress", 0.8), _forensic(True, comps), call, None, None)
        texts = " | ".join(i.finding for i in items)
        assert texts.count("Distress") == 2   # the deception alert + the Z-Score zone, nothing repeated
        assert next(i for i in items if "under 40 words" in i.finding).severity == "low"
