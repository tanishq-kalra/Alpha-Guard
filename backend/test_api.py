"""
Alpha-Guard — API Tests
========================
Endpoint behaviour with external data sources stubbed out.
"""

import pytest
from fastapi.testclient import TestClient

import forensic_analyzer as fa
import scraper
import security
from main import app
from models import FinancialData

client = TestClient(app)

MDA = " ".join(["Revenue increased twelve percent driven by higher unit sales in every region."] * 40)


def _financials(**overrides) -> FinancialData:
    return FinancialData(**{
        "ticker": "TEST",
        "total_assets": 1_000_000,
        "current_assets": 500_000,
        "current_liabilities": 200_000,
        "retained_earnings": 300_000,
        "ebit": 150_000,
        "market_cap": 2_000_000,
        "total_liabilities": 400_000,
        "revenue": 800_000,
        "sic_code": 3571,
        "fiscal_period_end": "2024-09-28",
        **overrides,
    })


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    security.reset_rate_limits()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield
    security.reset_rate_limits()


def _stub_sources(monkeypatch, financials=None, mda=MDA, fin_error=None):
    async def fake_auto(ticker):
        if fin_error:
            raise fin_error
        return financials or _financials(), "SEC EDGAR"

    async def fake_sections(ticker):
        return {"mda": mda, "risk_factors": ""}

    async def fake_name(ticker):
        return "Test Co"

    monkeypatch.setattr(scraper, "fetch_financial_data_auto", fake_auto)
    monkeypatch.setattr(scraper, "fetch_10k_text_sections", fake_sections)
    monkeypatch.setattr(scraper, "get_company_name", fake_name)


def test_health_reports_version():
    body = client.get("/").json()
    assert body["status"] == "operational"
    from config import VERSION
    assert body["version"] == VERSION


def test_z_score_endpoint_rejects_banks():
    payload = _financials(sic_code=6021).model_dump()
    resp = client.post("/api/risk/z-score", json=payload)
    assert resp.status_code == 422
    assert "financial institutions" in resp.json()["detail"]


def test_z_score_endpoint_accepts_missing_market_cap():
    payload = _financials(market_cap=None, sic_code=None).model_dump()
    resp = client.post("/api/risk/z-score", json=payload)
    assert resp.status_code == 200
    assert resp.json()["model"] == "z_double_prime"


def test_forensic_audit_without_ai_is_honest(monkeypatch):
    _stub_sources(monkeypatch)
    body = client.post("/api/risk/forensic-audit", json={"ticker": "test"}).json()
    assert body["ticker"] == "TEST"
    assert body["gemini_active"] is False
    assert "GEMINI_API_KEY" in body["ai_error"]
    f = body["forensic"]
    assert f["truth_score"] == 100
    assert f["truth_score_breakdown"]["basis"] == "heuristic"
    assert f["z_score_result"]["model"] == "original"


def test_forensic_audit_with_ai(monkeypatch):
    _stub_sources(monkeypatch)

    async def fake_gemini(text):
        return {"sentiment": "neutral", "confidence": 0.8, "suspicious_sentences": []}, None

    monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
    body = client.post("/api/risk/forensic-audit", json={"ticker": "TEST"}).json()
    assert body["gemini_active"] is True
    assert body["ai_error"] is None
    assert body["forensic"]["truth_score_breakdown"]["basis"] == "ai+heuristic"


def test_forensic_audit_without_text_has_no_score(monkeypatch):
    _stub_sources(monkeypatch, mda="")
    body = client.post("/api/risk/forensic-audit", json={"ticker": "TEST"}).json()
    assert body["forensic"]["truth_score"] is None
    assert body["gemini_active"] is False
    assert body["forensic"]["analysis_note"]


def test_forensic_audit_notes_bank(monkeypatch):
    from risk_engine import ZScoreNotApplicable
    _stub_sources(monkeypatch, fin_error=ZScoreNotApplicable("not applicable to financial institutions"))
    body = client.post("/api/risk/forensic-audit", json={"ticker": "BANK"}).json()
    assert body["forensic"]["z_score_result"] is None
    assert any(s.startswith("Z-Score not computed") and "not applicable" in s for s in body["data_sources"])


def test_rate_limit(monkeypatch):
    _stub_sources(monkeypatch)
    monkeypatch.setattr(security, "RATE_LIMIT_PER_MINUTE", 2)
    codes = [client.post("/api/risk/forensic-audit", json={"ticker": "TEST"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_pdf_with_null_truth_score(monkeypatch):
    _stub_sources(monkeypatch, mda="")
    resp = client.post("/api/reports/generate-pdf", json={"ticker": "TEST"})
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


def test_pdf_escapes_markup_in_ai_text(monkeypatch):
    _stub_sources(monkeypatch)

    async def fake_gemini(text):
        return {"sentiment": "bullish", "confidence": 0.9, "suspicious_sentences": [{
            "sentence": "Revenue increased twelve percent driven by higher unit sales in every region.",
            "category": "hedging", "severity": 5, "explanation": "Uses <b>unclosed & odd</i> markup",
        }]}, None

    monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
    resp = client.post("/api/reports/generate-pdf", json={"ticker": "TEST"})
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


def test_monte_carlo_endpoint():
    resp = client.post("/api/risk/monte-carlo", json={"ticker": "T", "num_simulations": 500, "seed": 1})
    assert resp.status_code == 200
    assert resp.json()["num_simulations"] == 500
