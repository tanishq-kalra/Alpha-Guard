"""
Alpha-Guard — Forensic Analysis Tests
======================================
Lexicon scoring, quote verification, Truth Score composition and the
analysis pipeline's handling of missing text / missing AI. No network access.
"""

import pytest

import forensic_analyzer as fa
from models import RedFlag, ZScoreComponents, ZScoreResult


def _z(zone: str) -> ZScoreResult:
    return ZScoreResult(
        ticker="TEST",
        score={"Safe": 4.0, "Gray": 2.5, "Distress": 1.0}[zone],
        zone=zone,
        components=ZScoreComponents(
            x1_working_capital_to_total_assets=0.1,
            x2_retained_earnings_to_total_assets=0.1,
            x3_ebit_to_total_assets=0.1,
            x4_market_cap_to_total_liabilities=1.0,
            x5_revenue_to_total_assets=1.0,
        ),
        interpretation="",
    )


PLAIN_MDA = " ".join(["Revenue increased twelve percent driven by higher unit sales in every region."] * 40)


class TestLexicon:

    def test_substrings_do_not_count(self):
        # "mayor", "dismay" and "couldron" must not match "may"/"could"
        score, words = fa.compute_hedging_score("The mayor was in dismay over the couldron.")
        assert score == 0
        assert words == []

    def test_risk_is_not_hedging(self):
        score, _ = fa.compute_hedging_score("risk risks risk factors risk")
        assert score == 0

    def test_evasion_phrase_not_double_counted_as_hedging(self):
        text = "We believe demand is strong. " * 10
        hedging, words = fa.compute_hedging_score(text)
        evasion = fa.compute_evasion_score(text)
        assert hedging == 0
        assert not any(w.startswith("believe") for w in words)
        assert evasion > 0

    def test_hedging_counts_whole_words(self):
        score, words = fa.compute_hedging_score("Sales may rise and could change. It may.")
        assert "may (2x)" in words
        assert "could (1x)" in words
        assert score > 0


class TestQuoteVerification:

    def test_verbatim_quote_is_verified(self):
        source = fa._normalize_for_match("We expect  margins to\nimprove materially next year.")
        assert fa.quote_in_text("We expect margins to improve materially next year.", source)

    def test_curly_quotes_and_case_are_normalized(self):
        source = fa._normalize_for_match("Management’s outlook REMAINS positive for the segment.")
        assert fa.quote_in_text("management's outlook remains positive for the segment", source)

    def test_hallucinated_quote_is_not_verified(self):
        source = fa._normalize_for_match(PLAIN_MDA)
        assert not fa.quote_in_text("We are hiding a massive accounting fraud.", source)

    def test_parse_red_flags_sanitizes_fields(self):
        flags = fa.parse_red_flags(
            {"suspicious_sentences": [
                {"sentence": "Revenue increased twelve percent driven by higher unit sales", "category": "BOGUS", "severity": "42"},
                {"sentence": "", "category": "hedging"},
                "not a dict",
            ]},
            PLAIN_MDA,
        )
        assert len(flags) == 1
        assert flags[0].category == "inconsistency"
        assert flags[0].severity == 10
        assert flags[0].verified is True


class TestTruthScore:

    def test_clean_filing_scores_100(self):
        score, zone, breakdown = fa.compute_truth_score(12, 1.5, [], 0, ai_used=True)
        assert score == 100
        assert zone == "Credible"
        assert breakdown.basis == "ai+heuristic"

    def test_penalties_add_up(self):
        flags = [
            RedFlag(sentence="a", category="hedging", severity=8, explanation="", verified=True),
            RedFlag(sentence="b", category="evasion", severity=8, explanation="", verified=True),
        ]
        # hedging (25-15)*1=10, evasion (4.5-2)*2=5, flags 16*0.75=12, gap 15 → 100-42
        score, zone, b = fa.compute_truth_score(25, 4.5, flags, 15, ai_used=True)
        assert (b.hedging_penalty, b.evasion_penalty, b.red_flag_penalty, b.sentiment_gap_penalty) == (10, 5, 12, 15)
        assert score == 58
        assert zone == "Suspicious"

    def test_unverified_flags_do_not_penalize(self):
        flags = [RedFlag(sentence="x", category="hedging", severity=10, explanation="", verified=False)]
        score, _, b = fa.compute_truth_score(0, 0, flags, 0, ai_used=True)
        assert b.red_flag_penalty == 0
        assert score == 100

    def test_score_is_clamped_and_deceptive(self):
        flags = [RedFlag(sentence=str(i), category="evasion", severity=10, explanation="", verified=True) for i in range(10)]
        score, zone, _ = fa.compute_truth_score(100, 100, flags, 40, ai_used=True)
        assert score == 0
        assert zone == "Deceptive"

    def test_confidence_no_longer_drives_score(self):
        # A bearish filing the AI is very sure about must not be "credible" by default,
        # nor an uncertain one "deceptive": confidence is not an input at all.
        import inspect
        assert "confidence" not in inspect.signature(fa.compute_truth_score).parameters


class TestSentimentGap:

    def test_bullish_in_distress_triggers_alert(self):
        alert, reason, penalty = fa.detect_sentiment_gap("bullish", "Distress")
        assert alert and penalty == 40 and "CRITICAL" in reason

    def test_consistent_sentiment_no_penalty(self):
        assert fa.detect_sentiment_gap("bearish", "Distress") == (False, None, 0.0)


class TestPipeline:

    async def test_short_text_skips_ai_and_score(self, monkeypatch):
        called = False

        async def fake_gemini(text):
            nonlocal called
            called = True
            return {}, None

        monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
        result, ai_error = await fa.analyze_filing_text("Filing text could not be retrieved.", "", _z("Safe"))
        assert called is False
        assert result.truth_score is None
        assert result.truth_zone is None
        assert result.analysis_note
        assert ai_error is not None

    async def test_ai_failure_falls_back_to_heuristics(self, monkeypatch):
        async def fake_gemini(text):
            return None, "Gemini API error: quota"

        monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
        result, ai_error = await fa.analyze_filing_text(PLAIN_MDA, "", _z("Distress"))
        assert ai_error == "Gemini API error: quota"
        assert result.truth_score == 100
        assert result.truth_score_breakdown.basis == "heuristic"
        assert result.ai_confidence_score is None
        assert result.linguistic_analysis.sentiment == "unknown"
        assert result.deception_alert is False  # no AI sentiment → no gap check

    async def test_ai_success_with_deception(self, monkeypatch):
        async def fake_gemini(text):
            return {
                "sentiment": "bullish",
                "confidence": 0.95,
                "suspicious_sentences": [{
                    "sentence": "Revenue increased twelve percent driven by higher unit sales in every region.",
                    "category": "sentiment_gap", "severity": 6, "explanation": "Too rosy",
                }],
            }, None

        monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
        result, ai_error = await fa.analyze_filing_text(PLAIN_MDA, "", _z("Distress"))
        assert ai_error is None
        assert result.deception_alert is True
        assert result.red_flags[0].severity == 10  # alert inserted first
        # 100 - gap 40 - verified flag 6*0.75 = 55.5, rounds to 56
        assert result.truth_score == 56
        assert result.truth_zone == "Suspicious"
        assert result.ai_confidence_score == 0.95

    async def test_no_zscore_skips_gap_check(self, monkeypatch):
        async def fake_gemini(text):
            return {"sentiment": "bullish", "confidence": 0.9, "suspicious_sentences": []}, None

        monkeypatch.setattr(fa, "call_gemini_analysis", fake_gemini)
        result, _ = await fa.analyze_filing_text(PLAIN_MDA, "", None)
        assert result.deception_alert is False
        assert result.truth_score_breakdown.sentiment_gap_penalty == 0


class TestGeminiCall:

    async def test_missing_key_reports_reason(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result, error = await fa.call_gemini_analysis("text")
        assert result is None
        assert "GEMINI_API_KEY" in error

    def test_parse_json_strips_code_fences(self):
        assert fa._parse_gemini_json('```json\n{"sentiment": "neutral"}\n```') == {"sentiment": "neutral"}

    def test_parse_json_rejects_non_object(self):
        with pytest.raises(ValueError):
            fa._parse_gemini_json("[1, 2]")


class TestLexiconTone:

    BULLISH = " ".join(["Our strong growth and record profitability reflect excellent execution and improved margins."] * 40)
    BEARISH = " ".join(["Weak demand caused losses, impairment charges and a decline in revenue amid litigation."] * 40)

    def test_bullish_text(self):
        sentiment, net = fa.compute_lexicon_tone(self.BULLISH)
        assert sentiment == "bullish" and net > 0.3

    def test_bearish_text(self):
        sentiment, net = fa.compute_lexicon_tone(self.BEARISH)
        assert sentiment == "bearish" and net < -0.3

    def test_too_few_tone_words_is_unknown(self):
        assert fa.compute_lexicon_tone(PLAIN_MDA) == ("unknown", None)

    def test_unknown_sentiment_never_penalised(self):
        assert fa.detect_sentiment_gap("unknown", "Distress") == (False, None, 0.0)

    async def test_gap_detected_without_ai(self, monkeypatch):
        async def no_ai(text):
            return None, "no key"

        monkeypatch.setattr(fa, "call_gemini_analysis", no_ai)
        result, _ = await fa.analyze_filing_text(self.BULLISH, "", _z("Distress"))
        la = result.linguistic_analysis
        assert la.sentiment == "bullish" and la.sentiment_source == "lexicon"
        assert result.deception_alert is True
        assert "lexicon" in result.deception_reason
        assert result.truth_score_breakdown.sentiment_gap_penalty == 40
        assert result.truth_score_breakdown.basis == "heuristic"
        assert result.truth_score <= 60

    async def test_ai_sentiment_overrides_lexicon(self, monkeypatch):
        async def ai(text):
            return {"sentiment": "bearish", "confidence": 0.9, "suspicious_sentences": []}, None

        monkeypatch.setattr(fa, "call_gemini_analysis", ai)
        result, _ = await fa.analyze_filing_text(self.BULLISH, "", _z("Distress"))
        assert result.linguistic_analysis.sentiment == "bearish"
        assert result.linguistic_analysis.sentiment_source == "ai"
        assert result.deception_alert is False


class TestGeminiErrorMessages:

    class _Err(Exception):
        def __init__(self, code, text):
            super().__init__(text)
            self.code = code

    def test_zero_quota_is_explained(self):
        msg = fa.describe_gemini_error(self._Err(429, "429 RESOURCE_EXHAUSTED {'quota_limit_value': '0'}"))
        assert "quota" in msg and "aistudio.google.com" in msg

    def test_rate_limit(self):
        assert "rate limit" in fa.describe_gemini_error(self._Err(429, "RESOURCE_EXHAUSTED"))

    def test_bad_key(self):
        assert "rejected the API key" in fa.describe_gemini_error(self._Err(400, "API_KEY_INVALID"))

    def test_unknown_model(self):
        assert "not found" in fa.describe_gemini_error(self._Err(404, "NOT_FOUND"))


class TestGeminiRetry:

    class _Err(Exception):
        def __init__(self, code, text):
            super().__init__(text)
            self.code = code

    def _patch_client(self, monkeypatch, outcomes):
        """Fake google-genai client that returns/raises `outcomes` in order."""
        import sys
        import types as pytypes

        calls = []

        class Models:
            async def generate_content(self, model, contents, config):
                calls.append(model)
                outcome = outcomes.pop(0)
                if isinstance(outcome, Exception):
                    raise outcome
                return pytypes.SimpleNamespace(text=outcome)

        class Client:
            def __init__(self, api_key):
                self.aio = pytypes.SimpleNamespace(models=Models())

        genai_mod = pytypes.SimpleNamespace(Client=Client)
        types_mod = pytypes.SimpleNamespace(GenerateContentConfig=lambda **kw: kw)
        google_pkg = pytypes.ModuleType("google")
        google_pkg.genai = genai_mod
        monkeypatch.setitem(sys.modules, "google", google_pkg)
        monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
        monkeypatch.setitem(sys.modules, "google.genai.types", types_mod)
        genai_mod.types = types_mod
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        monkeypatch.setattr(fa, "GEMINI_RETRY_DELAY_SECONDS", 0.0)
        return calls

    async def test_retries_then_succeeds(self, monkeypatch):
        calls = self._patch_client(monkeypatch, [self._Err(503, "UNAVAILABLE"), '{"sentiment": "neutral"}'])
        result, error = await fa.call_gemini_analysis("text")
        assert error is None and result == {"sentiment": "neutral"}
        assert calls == [fa.GEMINI_MODEL, fa.GEMINI_MODEL]

    async def test_falls_back_to_lighter_model(self, monkeypatch):
        busy = self._Err(503, "UNAVAILABLE")
        calls = self._patch_client(monkeypatch, [busy, busy, '{"sentiment": "bearish"}'])
        result, _ = await fa.call_gemini_analysis("text")
        assert result == {"sentiment": "bearish"} and calls[-1] == fa.GEMINI_FALLBACK_MODEL

    async def test_quota_error_is_not_retried(self, monkeypatch):
        calls = self._patch_client(monkeypatch, [self._Err(429, "RESOURCE_EXHAUSTED {'quota_limit_value': '0'}")])
        result, error = await fa.call_gemini_analysis("text")
        assert result is None and "quota" in error and len(calls) == 1

    async def test_persistent_overload_message(self, monkeypatch):
        busy = self._Err(503, "UNAVAILABLE")
        self._patch_client(monkeypatch, [busy, busy, busy])
        result, error = await fa.call_gemini_analysis("text")
        assert result is None and "temporarily overloaded" in error
