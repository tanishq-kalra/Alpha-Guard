"""
Alpha-Guard — Fiscal Quarter Resolution & Alpha Vantage Throttling Tests
=========================================================================
Alpha Vantage labels transcripts by *fiscal* quarter, so the latest call's
label depends on each company's fiscal year end. No network access.
"""

import pytest

import earnings_call as ec


class TestFiscalQuarterLabel:

    @pytest.mark.parametrize("period_end, fy_end, expected", [
        ("2026-06-30", 9, "2026Q3"),    # Apple: FY ends September -> June quarter is Q3
        ("2026-06-30", 6, "2026Q4"),    # Microsoft: FY ends June -> June quarter is Q4
        ("2026-09-30", 6, "2027Q1"),    # Microsoft's September quarter opens fiscal 2027
        ("2026-06-30", 12, "2026Q2"),   # calendar-year company (IBM)
        ("2025-12-31", 12, "2025Q4"),
        ("2026-03-31", 9, "2026Q2"),
        ("2026-01-03", 12, "2025Q4"),   # 52/53-week year ending in early January
    ])
    def test_labels(self, period_end, fy_end, expected):
        assert ec.fiscal_quarter_label(period_end, fy_end) == expected

    def test_fy_end_month_skips_trailing_twelve_months(self):
        annual = [
            {"fiscalDateEnding": "2026-06-30"},   # trailing twelve months, not a fiscal year
            {"fiscalDateEnding": "2025-09-30"},
            {"fiscalDateEnding": "2024-09-30"},
            {"fiscalDateEnding": "2023-09-30"},
        ]
        assert ec.fiscal_year_end_month(annual) == 9

    def test_fy_end_month_unknown(self):
        assert ec.fiscal_year_end_month([{"fiscalDateEnding": "2026-06-30"}]) is None


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _Client:
    """Returns queued JSON payloads in order and records the requests."""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    async def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return _Resp(self.payloads.pop(0))


BURST = {"Information": "Please consider spreading out your free API requests more sparingly "
                        "(1 request per second). ... rate limit (25 requests per day) ..."}
DAILY = {"Information": "Our standard API rate limit is 25 requests per day."}


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(ec, "AV_MIN_INTERVAL_SECONDS", 0.0)
    ec.clear_caches()
    ec._av_lock = None
    yield
    ec.clear_caches()


class TestAlphaVantageRequests:

    async def test_per_second_limit_is_retried_not_treated_as_daily(self):
        client = _Client([BURST, {"transcript": [{"speaker": "A"}]}])
        data = await ec._av_request(client, {"function": "X"})
        assert data == {"transcript": [{"speaker": "A"}]}
        assert len(client.calls) == 2
        assert ec._av_exhausted_until == 0.0

    async def test_daily_limit_raises(self):
        with pytest.raises(ec.AlphaVantageExhausted):
            await ec._av_request(_Client([DAILY]), {"function": "X"})
        assert ec._av_exhausted_until > 0

    async def test_persistent_burst_gives_up(self):
        client = _Client([BURST] * (ec.AV_BURST_RETRIES + 1))
        with pytest.raises(ec.AlphaVantageExhausted):
            await ec._av_request(client, {"function": "X"})

    async def test_latest_call_quarters_uses_fiscal_calendar(self):
        earnings = {
            "annualEarnings": [
                {"fiscalDateEnding": "2026-06-30"},
                {"fiscalDateEnding": "2025-09-30"},
                {"fiscalDateEnding": "2024-09-30"},
            ],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2026-09-30", "reportedDate": "2099-10-30", "reportedEPS": "None"},  # not yet
                {"fiscalDateEnding": "2026-06-30", "reportedDate": "2026-07-30", "reportedEPS": "2.02"},
                {"fiscalDateEnding": "2026-03-31", "reportedDate": "2026-04-30", "reportedEPS": "2.01"},
                {"fiscalDateEnding": "2025-12-31", "reportedDate": "2026-01-29", "reportedEPS": "2.84"},
            ],
        }
        labels = await ec.latest_call_quarters(_Client([earnings]), "AAPL", "k")
        assert labels == ["2026Q3", "2026Q2"]

    async def test_fetch_transcript_uses_latest_fiscal_quarter(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ec, "CACHE_DIR", tmp_path)
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "k")
        requested = []

        async def labels(client, ticker, key, limit=2):
            return ["2026Q4", "2026Q3"]

        async def transcript(client, ticker, quarter, key):
            requested.append(quarter)
            return [{"speaker": "CEO", "title": "CEO", "content": "hi"}] if quarter == "2026Q4" else []

        monkeypatch.setattr(ec, "latest_call_quarters", labels)
        monkeypatch.setattr(ec, "_alpha_vantage_transcript", transcript)
        result, err = await ec.fetch_transcript("MSFT")
        assert err is None and result["quarter"] == "2026Q4"
        assert requested == ["2026Q4"]   # newest first, stops once found

    async def test_falls_back_to_calendar_guess_when_calendar_unknown(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ec, "CACHE_DIR", tmp_path)
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "k")
        requested = []

        async def no_labels(client, ticker, key, limit=2):
            return []

        async def transcript(client, ticker, quarter, key):
            requested.append(quarter)
            return []

        monkeypatch.setattr(ec, "latest_call_quarters", no_labels)
        monkeypatch.setattr(ec, "_alpha_vantage_transcript", transcript)
        await ec.fetch_transcript("XYZ")
        assert requested == ec.candidate_quarters()
