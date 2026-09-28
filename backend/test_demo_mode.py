"""
Alpha-Guard — Demo Truth Score Tests
=====================================
The simulated score must be identical for a ticker on every run.
"""

import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

import forensic_analyzer as fa
import scraper
import security
from main import app
from models import FinancialData

client = TestClient(app)

TICKERS = ["AAPL", "MSFT", "TSLA", "KO", "F", "BA", "WMT", "GE", "JPM", "RELIANCE.NS", "TCS.NS", "INFY.NS"]


class TestDemoScore:

    def test_same_ticker_same_score(self):
        assert fa.demo_truth_score("AAPL") == fa.demo_truth_score("AAPL")

    def test_case_and_whitespace_insensitive(self):
        assert fa.demo_truth_score(" aapl ") == fa.demo_truth_score("AAPL")

    def test_stable_across_processes(self):
        # Python's hash() is salted per process; the demo score must not be
        code = "import forensic_analyzer as fa; print([fa.demo_truth_score(t) for t in %r])" % TICKERS
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
        assert out.strip() == str([fa.demo_truth_score(t) for t in TICKERS])

    def test_range(self):
        for t in TICKERS:
            assert fa.DEMO_SCORE_MIN <= fa.demo_truth_score(t) <= fa.DEMO_SCORE_MAX

    def test_companies_get_different_scores(self):
        assert len({fa.demo_truth_score(t) for t in TICKERS}) > len(TICKERS) // 2

    def test_all_zones_reachable(self):
        zones = {fa.truth_zone_for(fa.demo_truth_score(f"T{i}")) for i in range(200)}
        assert zones == {"Credible", "Suspicious", "Deceptive"}


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setenv("TRUTH_SCORE_MODE", "demo")
    security.reset_rate_limits()

    async def fake_auto(ticker):
        return FinancialData(
            ticker=ticker, total_assets=1e6, current_assets=5e5, current_liabilities=2e5,
            retained_earnings=3e5, ebit=1.5e5, market_cap=2e6, total_liabilities=4e5,
            revenue=8e5, sic_code=3571,
        ), "SEC EDGAR"

    async def no_text(ticker):
        return {"mda": "", "risk_factors": ""}

    async def fake_name(ticker):
        return "Test Co"

    async def gemini_must_not_run(text):
        raise AssertionError("Gemini must not be called in demo mode")

    monkeypatch.setattr(scraper, "fetch_financial_data_auto", fake_auto)
    monkeypatch.setattr(scraper, "fetch_10k_text_sections", no_text)
    monkeypatch.setattr(scraper, "get_company_name", fake_name)
    monkeypatch.setattr(fa, "call_gemini_analysis", gemini_must_not_run)
    yield
    security.reset_rate_limits()


class TestDemoPipeline:

    def test_score_even_without_filing_text(self, demo_env):
        body = client.post("/api/risk/forensic-audit", json={"ticker": "GE"}).json()
        f = body["forensic"]
        assert body["truth_score_mode"] == "demo"
        assert f["truth_score"] == fa.demo_truth_score("GE")
        assert f["truth_zone"] == fa.truth_zone_for(f["truth_score"])
        assert f["truth_score_breakdown"]["basis"] == "demo"
        assert "not an analysis result" in f["analysis_note"]
        assert body["gemini_active"] is False and body["ai_error"] is None
        assert f["red_flags"] == [] and f["deception_alert"] is False

    def test_repeat_requests_identical(self, demo_env):
        scores = {client.post("/api/risk/forensic-audit", json={"ticker": "tsla"}).json()["forensic"]["truth_score"] for _ in range(3)}
        assert scores == {fa.demo_truth_score("TSLA")}

    def test_indian_ticker_with_and_without_suffix(self, demo_env):
        a = client.post("/api/risk/forensic-audit", json={"ticker": "RELIANCE"}).json()["forensic"]["truth_score"]
        b = client.post("/api/risk/forensic-audit", json={"ticker": "RELIANCE.NS"}).json()["forensic"]["truth_score"]
        assert a == b == fa.demo_truth_score("RELIANCE.NS")

    def test_pdf_in_demo_mode(self, demo_env):
        resp = client.post("/api/reports/generate-pdf", json={"ticker": "KO"})
        assert resp.status_code == 200 and resp.content.startswith(b"%PDF")
