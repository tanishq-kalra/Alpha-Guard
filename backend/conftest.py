import pytest


@pytest.fixture(autouse=True)
def _no_live_earnings_calls(monkeypatch):
    """Keep pipeline tests offline; earnings-call tests patch their own sources."""
    import earnings_call

    async def offline(ticker, allow_sec=True):
        return {"error": "Earnings call lookup disabled in tests."}

    async def no_release(ticker):
        return None, "Earnings release lookup disabled in tests."

    monkeypatch.setattr(earnings_call, "fetch_call_material", offline)
    monkeypatch.setattr(earnings_call, "fetch_earnings_release", no_release)
    earnings_call.clear_caches()
