"""
Alpha-Guard — Earnings Call Analysis Tests
===========================================
Transcript segmentation, deflection detection, candor scoring, source
fallback and caching. No network access.
"""

from datetime import date

import pytest

import earnings_call as ec

# Captured at import, before conftest replaces it with an offline stub for each test
REAL_FETCH_CALL_MATERIAL = ec.fetch_call_material

UPBEAT = "We delivered strong record growth with excellent profitability and improved margins across every segment. "
GLOOMY = "Demand was weak and we saw losses, impairment, delays and a decline in orders amid difficult conditions. "


def _turn(speaker, title, content, sentiment=0.5):
    return {"speaker": speaker, "title": title, "content": content, "sentiment": sentiment}


def _call(answers):
    """Opening by IR, CEO/CFO prepared remarks, then one question per answer."""
    turns = [
        _turn("Jane IR", "Head of Investor Relations",
              "Forward-looking statements may differ materially; we assume no obligation to update. " * 5),
        _turn("Alex Chen", "CEO", UPBEAT * 20, 0.8),
        _turn("Sam Rao", "CFO", UPBEAT * 20, 0.7),
    ]
    for i, answer in enumerate(answers):
        turns.append(_turn("Operator", "Operator", f"Our next question comes from Analyst {i}."))
        turns.append(_turn(f"Analyst {i}", "Analyst", "Can you give us more detail on margins in the quarter?"))
        turns.append(_turn("Sam Rao", "CFO", answer, 0.3))
    turns.append(_turn("Operator", "Operator", "This concludes today's call."))
    return turns


class TestSegmentation:

    def test_roles(self):
        assert ec._role(_turn("Operator", "Operator", "")) == "operator"
        assert ec._role(_turn("Pat", "Analyst", "")) == "analyst"
        assert ec._role(_turn("Pat", "Morgan Stanley", "")) == "analyst"
        assert ec._role(_turn("Alex", "Chief Executive Officer", "")) == "executive"
        assert ec._role(_turn("Sam", "CFO", "")) == "executive"

    def test_prepared_excludes_ir_safe_harbor(self):
        parts = ec.analyze_transcript(_call([UPBEAT * 5]))
        assert parts["prepared"].words == len((UPBEAT * 40).split())
        assert parts["prepared"].hedging_score == 0  # safe-harbor boilerplate left out

    def test_exchanges_pair_questions_with_answers(self):
        parts = ec.analyze_transcript(_call([UPBEAT * 5, GLOOMY * 5]))
        assert len(parts["exchanges"]) == 2
        assert parts["exchanges"][0].analyst == "Analyst 0"
        assert parts["exchanges"][0].respondents == ["Sam Rao (CFO)"]
        assert parts["qa"].words == len((UPBEAT * 5 + GLOOMY * 5).split())
        assert "Alex Chen — CEO" in parts["executives"]

    def test_provider_sentiment_averaged(self):
        parts = ec.analyze_transcript(_call([UPBEAT * 5]))
        assert parts["prepared"].provider_sentiment == 0.75
        assert parts["qa"].provider_sentiment == 0.3

    def test_call_without_questions(self):
        parts = ec.analyze_transcript([_turn("Alex", "CEO", UPBEAT * 10)])
        assert parts["qa"] is None and parts["exchanges"] == []


class TestDeflection:

    def test_refusal_detected(self):
        parts = ec.analyze_transcript(_call([
            "We don't break out that number, but overall we feel good about the business. " * 3,
        ]))
        ex = parts["exchanges"][0]
        assert ex.deflection_phrase == "we don't break out"
        assert "break out" in ex.answer_excerpt

    def test_referring_back_is_not_deflection(self):
        parts = ec.analyze_transcript(_call(["As I said earlier, margins improved because of pricing and mix. " * 3]))
        assert parts["exchanges"][0].deflection_phrase is None

    def test_brief_answer(self):
        parts = ec.analyze_transcript(_call(["Not much to add there."]))
        assert parts["exchanges"][0].brief is True

    def test_moderator_handoffs_and_thank_yous_are_not_exchanges(self):
        # Apple-style Q&A: the IR director hosts, analysts sign off with "Thanks"
        turns = [
            _turn("Tim", "CEO", UPBEAT * 20),
            _turn("Suhasini", "Director, Investor Relations", "We'll now open the call to questions. Operator?"),
            _turn("Operator", "Operator", "Our first question is from Michael Ng."),
            _turn("Michael Ng", "Analyst", "Can you talk about gross margin drivers into the September quarter please?"),
            _turn("Kevan", "CFO", UPBEAT * 5),
            _turn("Michael Ng", "Analyst", "Great, thank you."),
            _turn("Kevan", "CFO", "Thank you, Michael."),
            _turn("Suhasini", "Director, Investor Relations", "Thank you, Michael. Operator, could we have the next question, please?"),
            _turn("Operator", "Operator", "Next is Ben Reitzes."),
            _turn("Ben Reitzes", "Analyst", "Services?"),
            _turn("Tim", "CEO", UPBEAT * 5),
        ]
        parts = ec.analyze_transcript(turns)
        assert [e.analyst for e in parts["exchanges"]] == ["Michael Ng", "Ben Reitzes"]
        assert not any(e.brief for e in parts["exchanges"])
        assert all("Operator" not in e.answer_excerpt for e in parts["exchanges"])

    @pytest.mark.parametrize("text, courtesy", [
        ("Great. Thank you both for taking my questions. Congrats again, Tim. Thank you.", True),
        ("Tim, congrats on your tenure. You joined in 2011 when Apple reported $108 billion.", True),
        ("Thanks. I wanted to ask about services margins going forward", False),
        ("I'd love to get your take on pricing in China", False),
        ("Services?", False),
    ])
    def test_courtesy_detection(self, text, courtesy):
        assert ec._is_courtesy({"content": text}) is courtesy


class TestCandor:

    def test_open_consistent_call_scores_100(self):
        parts = ec.analyze_transcript(_call([UPBEAT * 5] * 4))
        score, flags, shift, rate = ec.candor_assessment(parts["prepared"], parts["qa"], parts["exchanges"], "Safe")
        assert score == 100 and flags == [] and rate == 0.0 and shift == 0.0

    def test_evasive_call_is_penalised(self):
        evasive = "It's too early to say, and we're not going to comment on that. " * 4
        parts = ec.analyze_transcript(_call([evasive, evasive, GLOOMY * 5, UPBEAT * 5]))
        score, flags, shift, rate = ec.candor_assessment(parts["prepared"], parts["qa"], parts["exchanges"], "Safe")
        assert rate == 0.5
        assert any("deflected 2 of 4" in f for f in flags)
        assert any("Tone drops" in f for f in flags)
        assert shift < -0.25
        assert score < 75

    def test_upbeat_call_in_distress_is_flagged(self):
        parts = ec.analyze_transcript(_call([UPBEAT * 5]))
        score, flags, _, _ = ec.candor_assessment(parts["prepared"], parts["qa"], parts["exchanges"], "Distress")
        assert any("Distress" in f for f in flags)
        assert score == 80


class TestQuarters:

    def test_candidate_quarters(self):
        assert ec.candidate_quarters(date(2026, 9, 28)) == ["2026Q2", "2026Q3", "2026Q1"]
        assert ec.candidate_quarters(date(2026, 2, 10)) == ["2025Q4", "2026Q1", "2025Q3"]


class TestPressRelease:

    def test_uses_quotes_when_long_enough(self):
        quote = "“" + UPBEAT * 12 + "”"
        parts = ec.analyze_press_release("Revenue table 1 2 3. " * 50 + quote)
        assert parts["scope"] == "management quotes"
        assert parts["prepared"].sentiment == "bullish"

    def test_falls_back_to_full_release(self):
        parts = ec.analyze_press_release("“Short quote from the CEO about the quarter.” " + GLOOMY * 20)
        assert parts["scope"] == "full release"
        assert parts["prepared"].sentiment == "bearish"

    def test_release_has_no_candor_score(self):
        material = {"release": {"text": UPBEAT * 30, "date": "2026-07-30", "url": "https://sec.gov/x"},
                    "transcript_error": "no key"}
        result = ec.build_call_analysis(material, "Safe")
        assert result.available and result.source == "sec_8k"
        assert result.candor_score is None
        assert "no key" in result.note
        assert any("can't be measured" in f for f in result.flags)


class TestFetching:

    @pytest.fixture(autouse=True)
    def _isolated_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ec, "CACHE_DIR", tmp_path)
        ec.clear_caches()
        yield
        ec.clear_caches()

    def _patch_av(self, monkeypatch, responses):
        calls = []

        async def fake(client, ticker, quarter, key):
            calls.append(quarter)
            return responses.get(quarter, [])

        async def no_calendar(client, ticker, key, limit=2):
            return []  # exercise the calendar-quarter fallback

        monkeypatch.setattr(ec, "_alpha_vantage_transcript", fake)
        monkeypatch.setattr(ec, "latest_call_quarters", no_calendar)
        return calls

    async def test_tries_quarters_until_found_and_caches(self, monkeypatch):
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "k")
        monkeypatch.setattr(ec, "candidate_quarters", lambda: ["2026Q2", "2026Q3"])
        calls = self._patch_av(monkeypatch, {"2026Q3": _call([UPBEAT])})
        first, err = await ec.fetch_transcript("aapl")
        assert err is None and first["quarter"] == "2026Q3" and calls == ["2026Q2", "2026Q3"]
        again, _ = await ec.fetch_transcript("AAPL")
        assert again["quarter"] == "2026Q3" and calls == ["2026Q2", "2026Q3"]  # served from disk cache

    async def test_rate_limit_reported(self, monkeypatch):
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "k")
        self._patch_av(monkeypatch, {q: None for q in ec.candidate_quarters()})
        result, err = await ec.fetch_transcript("MSFT")
        assert result is None and "limit" in err

    async def test_no_key_only_ibm_demo(self, monkeypatch):
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        calls = self._patch_av(monkeypatch, {"2024Q1": _call([UPBEAT])})
        _, err = await ec.fetch_transcript("AAPL")
        assert "ALPHAVANTAGE_API_KEY" in err and calls == []
        ibm, _ = await ec.fetch_transcript("IBM")
        assert ibm["quarter"] == "2024Q1"

    async def test_miss_is_remembered(self, monkeypatch):
        monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "k")
        calls = self._patch_av(monkeypatch, {})
        await ec.fetch_transcript("ZZZ")
        n = len(calls)
        _, err = await ec.fetch_transcript("ZZZ")
        assert len(calls) == n and "checked recently" in err

    async def test_falls_back_to_sec_release(self, monkeypatch):
        async def no_transcript(ticker):
            return None, "no key"

        async def release(ticker):
            return {"source": "sec_8k", "date": "2026-07-30", "url": "u", "text": GLOOMY * 30}, None

        monkeypatch.setattr(ec, "fetch_transcript", no_transcript)
        monkeypatch.setattr(ec, "fetch_earnings_release", release)
        material = await REAL_FETCH_CALL_MATERIAL("AAPL")
        assert material["release"]["date"] == "2026-07-30"
        assert material["transcript_error"] == "no key"

    async def test_transcript_preferred_over_release(self, monkeypatch):
        async def transcript(ticker):
            return {"source": "alpha_vantage", "quarter": "2026Q2", "turns": _call([UPBEAT * 5])}, None

        async def release_must_not_run(ticker):
            raise AssertionError("release fetched although a transcript exists")

        monkeypatch.setattr(ec, "fetch_transcript", transcript)
        monkeypatch.setattr(ec, "fetch_earnings_release", release_must_not_run)
        result = ec.build_call_analysis(await REAL_FETCH_CALL_MATERIAL("AAPL"), "Safe")
        assert result.source == "alpha_vantage" and result.quarter == "2026Q2"
        assert result.candor_score == 100 and result.analyst_questions == 1

    async def test_international_skips_sec(self, monkeypatch):
        async def no_transcript(ticker):
            return None, "none"

        async def release_must_not_run(ticker):
            raise AssertionError("SEC is US-only")

        monkeypatch.setattr(ec, "fetch_transcript", no_transcript)
        monkeypatch.setattr(ec, "fetch_earnings_release", release_must_not_run)
        material = await REAL_FETCH_CALL_MATERIAL("RELIANCE.NS", allow_sec=False)
        result = ec.build_call_analysis(material, None)
        assert result.available is False and result.note == "none"


class TestReleaseDocumentPicking:

    ITEMS = [
        {"name": "0000040545-26-000047-index-headers.html", "size": ""},
        {"name": "0000040545-26-000047-index.html", "size": ""},
        {"name": "ge-20260716.htm", "size": "38287"},
        {"name": "R1.htm", "size": "49309"},
    ]

    def test_named_exhibit(self):
        items = self.ITEMS + [{"name": "msft-ex99_1.htm", "size": "900"}]
        assert ec.pick_release_document(items, "ge-20260716.htm") == "msft-ex99_1.htm"

    def test_earnings_release_name(self):
        items = self.ITEMS + [{"name": "ge2q2026earningsrelease.htm", "size": "357063"}]
        assert ec.pick_release_document(items, "ge-20260716.htm") == "ge2q2026earningsrelease.htm"

    def test_falls_back_to_largest_non_cover_document(self):
        items = self.ITEMS + [{"name": "q2results.htm", "size": "250000"}]
        assert ec.pick_release_document(items, "ge-20260716.htm") == "q2results.htm"

    def test_only_cover_and_index_pages(self):
        assert ec.pick_release_document(self.ITEMS, "ge-20260716.htm") is None
