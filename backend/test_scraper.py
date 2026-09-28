"""
Alpha-Guard — Data Ingestion Tests
===================================
XBRL period alignment and 10-K section extraction against small fixtures.
No network access.
"""

import pytest

import scraper
from risk_engine import ZScoreNotApplicable


def _fact(val, end, start=None, form="10-K", filed="2024-11-01"):
    entry = {"val": val, "end": end, "form": form, "filed": filed}
    if start:
        entry["start"] = start
    return entry


def _facts(us_gaap: dict, dei: dict | None = None) -> dict:
    return {
        "facts": {
            "us-gaap": {tag: {"units": {"USD": entries}} for tag, entries in us_gaap.items()},
            "dei": {tag: {"units": {"USD": entries}} for tag, entries in (dei or {}).items()},
        }
    }


FY24 = "2024-09-28"
FY23 = "2023-09-30"


def _complete_facts(**overrides) -> dict:
    base = {
        "Assets": [_fact(300, FY23), _fact(350, FY24)],
        "AssetsCurrent": [_fact(120, FY24)],
        "LiabilitiesCurrent": [_fact(90, FY24)],
        "RetainedEarningsAccumulatedDeficit": [_fact(40, FY24)],
        "OperatingIncomeLoss": [_fact(60, FY24, start="2023-10-01")],
        "Liabilities": [_fact(250, FY24)],
        "RevenueFromContractWithCustomerExcludingAssessedTax": [_fact(390, FY24, start="2023-10-01")],
    }
    base.update(overrides)
    return _facts(base)


class TestXbrlPeriodAlignment:

    def test_fiscal_period_end_is_latest_balance_sheet_date(self):
        assert scraper.find_fiscal_period_end(_complete_facts()) == FY24

    def test_stale_tag_is_ignored_in_favour_of_current_period(self):
        # "Revenues" was last used in 2018; the current tag must win for FY24
        facts = _facts({
            "Revenues": [_fact(100, "2018-09-29", start="2017-10-01")],
            "RevenueFromContractWithCustomerExcludingAssessedTax": [_fact(390, FY24, start="2023-10-01")],
        })
        value = scraper.extract_value_for_period(
            facts, scraper.XBRL_CONCEPT_MAP["revenue"], FY24, duration=True,
        )
        assert value == 390

    def test_quarterly_duration_is_not_mistaken_for_annual(self):
        facts = _facts({
            "OperatingIncomeLoss": [
                _fact(15, FY24, start="2024-06-30"),   # Q4 only
                _fact(60, FY24, start="2023-10-01"),   # full year
            ],
        })
        assert scraper.extract_value_for_period(facts, ["OperatingIncomeLoss"], FY24, duration=True) == 60

    def test_prior_year_comparative_is_not_used(self):
        facts = _facts({"AssetsCurrent": [_fact(999, FY23)]})
        assert scraper.extract_value_for_period(facts, ["AssetsCurrent"], FY24, duration=False) is None

    def test_restated_value_uses_latest_filing(self):
        facts = _facts({"Liabilities": [
            _fact(250, FY24, filed="2024-11-01"),
            _fact(260, FY24, form="10-K/A", filed="2025-02-01"),
        ]})
        assert scraper.extract_value_for_period(facts, ["Liabilities"], FY24, duration=False) == 260

    def test_quarterly_forms_are_ignored(self):
        facts = _facts({"Assets": [_fact(500, "2025-03-29", form="10-Q"), _fact(350, FY24)]})
        assert scraper.find_fiscal_period_end(facts) == FY24

    def test_total_liabilities_derived_when_not_reported(self):
        facts = _facts({
            "LiabilitiesAndStockholdersEquity": [_fact(350, FY24)],
            "StockholdersEquity": [_fact(100, FY24)],
        })
        assert scraper._extract_total_liabilities(facts, FY24) == 250

    def test_public_float_fallback(self):
        facts = _facts({}, dei={"EntityPublicFloat": [_fact(2_000, "2024-03-29"), _fact(1_500, "2023-03-31")]})
        assert scraper._extract_public_float(facts) == 2_000


class TestFetchFromEdgar:

    @pytest.fixture(autouse=True)
    def _clear(self):
        scraper.clear_caches()
        yield
        scraper.clear_caches()

    def _patch(self, monkeypatch, facts, sic="3571", market_cap=3_000.0):
        async def fake_resolve(ticker):
            return "0000320193", "Test Co"

        async def fake_facts(cik):
            return facts

        async def fake_submissions(cik):
            return {"sic": sic}

        async def fake_info(ticker):
            return {"marketCap": market_cap} if market_cap else {}

        monkeypatch.setattr(scraper, "resolve_ticker_to_cik", fake_resolve)
        monkeypatch.setattr(scraper, "get_company_facts", fake_facts)
        monkeypatch.setattr(scraper, "get_submissions", fake_submissions)
        monkeypatch.setattr(scraper, "get_yahoo_info", fake_info)

    async def test_market_cap_is_real_not_total_assets(self, monkeypatch):
        self._patch(monkeypatch, _complete_facts())
        data = await scraper.fetch_financial_data_from_edgar("TEST")
        assert data.market_cap == 3_000.0
        assert data.market_cap != data.total_assets
        assert data.fiscal_period_end == FY24
        assert data.sic_code == 3571

    async def test_missing_market_cap_stays_none(self, monkeypatch):
        self._patch(monkeypatch, _complete_facts(), market_cap=None)
        data = await scraper.fetch_financial_data_from_edgar("TEST")
        assert data.market_cap is None

    async def test_bank_is_rejected(self, monkeypatch):
        self._patch(monkeypatch, _complete_facts(), sic="6021")
        with pytest.raises(ZScoreNotApplicable):
            await scraper.fetch_financial_data_from_edgar("BANK")


class TestTickerMapCache:

    async def test_ticker_map_downloaded_once(self, monkeypatch):
        scraper.clear_caches()
        calls = []

        class FakeResp:
            def json(self):
                return {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}}

        async def fake_get(url, timeout=30.0):
            calls.append(url)
            return FakeResp()

        monkeypatch.setattr(scraper, "_sec_get", fake_get)
        assert await scraper.resolve_ticker_to_cik("aapl") == ("0000320193", "Apple Inc.")
        assert await scraper.resolve_ticker_to_cik("AAPL") == ("0000320193", "Apple Inc.")
        assert len(calls) == 1
        scraper.clear_caches()


class TestSectionExtraction:

    FILING = (
        "TABLE OF CONTENTS Item 1. Business 3 Item 1A. Risk Factors 12 Item 1B. Unresolved Staff Comments 20 "
        "Item 7. Management's Discussion and Analysis 25 Item 7A. Quantitative Disclosures 40 Item 8. Financial 41 "
        "PART I Item 1. Business We make things. See Item 1A. Risk Factors for more. "
        "Item 1A. Risk Factors " + "Our business faces many risks. " * 50 +
        "Item 1B. Unresolved Staff Comments None. Item 2. Properties We lease offices. "
        "Item 7. Management’s Discussion and Analysis of Financial Condition "
        "Read this with the statements included in Part II, Item 8 of this Form 10-K. "
        + "Revenue grew this year. " * 80 +
        "Item 7A. Quantitative and Qualitative Disclosures About Market Risk Rates. Item 8. Financial Statements"
    )

    def test_risk_factors_skips_table_of_contents(self):
        section = scraper._extract_section(self.FILING, scraper.RISK_FACTORS_START, scraper.RISK_FACTORS_END)
        assert section.count("Our business faces many risks.") == 50
        assert "We make things" not in section

    def test_mda_skips_table_of_contents(self):
        section = scraper._extract_section(self.FILING, scraper.MDA_START, scraper.MDA_END)
        assert section.count("Revenue grew this year.") == 80
        assert "Quantitative" not in section

    def test_html_headings_beat_quoted_cross_references(self):
        # Mirrors real filings: TOC table rows, then body headings in their own
        # <div>s, with MD&A text quoting the *full* title of Item 8 mid-sentence.
        html = (
            "<table><tr><td>Item 7.</td><td>Management's Discussion and Analysis</td><td>25</td></tr>"
            "<tr><td>Item 8.</td><td>Financial Statements and Supplementary Data</td><td>40</td></tr></table>"
            "<div>ITEM 7. MANAGEMENT&#8217;S DISCUSSION AND ANALYSIS</div>"
            "<p>This should be read with the statements in Part II, &#8220;Item 8. Financial Statements "
            "and Supplementary Data&#8221; of this report.</p>"
            + "<p>Operating margin expanded on pricing.</p>" * 60 +
            "<div>ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA</div><p>Balance sheet.</p>"
        )
        text = scraper._strip_html_tags(html)
        section = scraper._extract_section(text, scraper.MDA_START, scraper.MDA_END)
        assert section.count("Operating margin expanded on pricing.") == 60
        assert "Balance sheet" not in section

    def test_running_page_headers_keep_whole_section(self):
        # Ford-style filings repeat the Item heading at the top of every page
        page = "<p>Liquidity remained strong this quarter.</p>" * 20
        html = (
            "<div>ITEM 7. Management's Discussion and Analysis</div>" + page
            + "<div>Item 7. Management's Discussion and Analysis (Continued)</div>" + page
            + "<div>Item 7. Management's Discussion and Analysis (Continued)</div>" + page
            + "<div>ITEM 7A. Quantitative and Qualitative Disclosures About Market Risk</div>"
        )
        section = scraper._extract_section(scraper._strip_html_tags(html), scraper.MDA_START, scraper.MDA_END)
        assert section.count("Liquidity remained strong this quarter.") == 60

    def test_words_split_across_spans_are_rejoined(self):
        text = scraper._strip_html_tags("<div>ITEM 1A. <span>RIS</span><span>K FACTORS</span></div>")
        assert "RISK FACTORS" in text

    def test_missing_section_returns_empty(self):
        assert scraper._extract_section("no items here", scraper.MDA_START, scraper.MDA_END) == ""

    def test_strip_html_removes_hidden_xbrl_and_scripts(self):
        html = (
            "<html><ix:header><ix:hidden>dei:Secret 123</ix:hidden></ix:header>"
            "<script>var x = 1;</script><p>Item&#160;7. Hello&amp;bye</p></html>"
        )
        text = scraper._strip_html_tags(html)
        assert "Secret" not in text
        assert "var x" not in text
        assert "Hello&bye" in text
