"""
Alpha-Guard — Central Configuration
====================================
Single source of truth for the version string and environment-driven settings.
"""

import os

VERSION = "0.4.0"

# SEC requires a descriptive User-Agent with a real contact address:
# https://www.sec.gov/os/accessing-edgar-data
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Alpha-Guard Research alpha-guard@research.dev",
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Comma-separated list of allowed CORS origins. "*" allows any origin.
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]

# Max requests per client IP per minute on the expensive endpoints
# (forensic audit, PDF report). 0 disables the limit.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))


def truth_score_mode() -> str:
    """'demo' (default): a deterministic simulated score per ticker, no AI calls.
    'computed': the heuristic + Gemini analysis pipeline.
    Read at call time so tests and late-loaded .env files are respected."""
    mode = os.getenv("TRUTH_SCORE_MODE", "demo").strip().lower()
    return mode if mode in {"demo", "computed"} else "demo"


def gemini_api_key() -> str | None:
    """Read at call time so tests and late-loaded .env files are respected."""
    return os.getenv("GEMINI_API_KEY") or None
