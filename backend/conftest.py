import pytest


@pytest.fixture(autouse=True)
def _computed_truth_score_mode(monkeypatch):
    """Tests exercise the real scoring pipeline unless they opt into demo mode."""
    monkeypatch.setenv("TRUTH_SCORE_MODE", "computed")
