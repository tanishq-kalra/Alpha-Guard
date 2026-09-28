"""
Alpha-Guard — Central Configuration
====================================
Single source of truth for the version string and environment-driven settings.
"""

import os

VERSION = "0.5.0"

# Shown as "Prepared by" on research reports
REPORT_TEAM = [
    ("Tanishq Kalra", "23bce8021"),
    ("Priya Pareek", "23bce9243"),
    ("Varsha Shekhawat", "23bce7221"),
    ("Dhanishta Sandip Likhar", "23bce9274"),
]

# SEC requires a descriptive User-Agent with a real contact address:
# https://www.sec.gov/os/accessing-edgar-data
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Alpha-Guard Research alpha-guard@research.dev",
)

# An alias that always points at the current Flash model, so it is never retired
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Comma-separated list of allowed CORS origins. "*" allows any origin.
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]

# Max requests per client IP per minute on the expensive endpoints
# (forensic audit, PDF report). 0 disables the limit.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))


def alphavantage_api_key() -> str | None:
    """Free key from https://www.alphavantage.co/support/#api-key (earnings call transcripts)."""
    return os.getenv("ALPHAVANTAGE_API_KEY") or None


def gemini_api_key() -> str | None:
    """Read at call time so tests and late-loaded .env files are respected."""
    return os.getenv("GEMINI_API_KEY") or None
