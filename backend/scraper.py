"""
Alpha-Guard — Financial Data Ingestion
=======================================
Data sources:
  1. SEC EDGAR (primary) — Free JSON API at data.sec.gov for 10-K XBRL data
  2. Yahoo Finance (yfinance) — Global market data (BSE/NSE/international) and
     market capitalisation for US companies
"""

import asyncio
import re
import time
import html as html_module
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException

from config import SEC_USER_AGENT
from models import FinancialData, CompanyInfo
from risk_engine import ZScoreNotApplicable

router = APIRouter(prefix="/api/data", tags=["Data Ingestion"])

# SEC EDGAR API base — no authentication required
SEC_EDGAR_BASE = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

# SEC allows 10 requests/second per client; stay well under it
_SEC_CONCURRENCY = asyncio.Semaphore(4)

# Mapping of common XBRL US-GAAP concept tags to our FinancialData fields.
# Tags are tried in order, but only values for the aligned fiscal period count,
# so a stale tag a company stopped using years ago can no longer win.
XBRL_CONCEPT_MAP = {
    "total_assets": [
        "Assets",
    ],
    "current_assets": [
        "AssetsCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
    "retained_earnings": [
        "RetainedEarningsAccumulatedDeficit",
    ],
    "ebit": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "total_liabilities": [
        "Liabilities",
    ],
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ],
}

# Income-statement concepts are reported over a period; the rest are point-in-time
DURATION_FIELDS = {"ebit", "revenue"}

ANNUAL_FORMS = {"10-K", "10-K/A"}

# ──────────────────────────────────────────────
#  Caching
# ──────────────────────────────────────────────

class _TTLCache:
    """Minimal in-process cache with per-entry expiry."""

    def __init__(self, ttl_seconds: float, max_entries: int = 256):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._data: dict = {}

    def get(self, key):
        item = self._data.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key, value):
        if len(self._data) >= self.max_entries:
            # Drop the entry closest to expiry
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)
        self._data[key] = (time.monotonic() + self.ttl, value)

    def clear(self):
        self._data.clear()


_ticker_map_cache = _TTLCache(ttl_seconds=24 * 3600, max_entries=1)
_json_cache = _TTLCache(ttl_seconds=6 * 3600)
_filing_text_cache = _TTLCache(ttl_seconds=24 * 3600, max_entries=64)
_yahoo_info_cache = _TTLCache(ttl_seconds=3600)


def clear_caches() -> None:
    for cache in (_ticker_map_cache, _json_cache, _filing_text_cache, _yahoo_info_cache):
        cache.clear()


async def _sec_get(url: str, timeout: float = 30.0) -> httpx.Response:
    """GET from SEC with the required User-Agent and a concurrency cap."""
    async with _SEC_CONCURRENCY:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, headers=SEC_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp


async def _sec_get_json(url: str) -> dict:
    cached = _json_cache.get(url)
    if cached is not None:
        return cached
    data = (await _sec_get(url)).json()
    _json_cache.set(url, data)
    return data


# ──────────────────────────────────────────────
#  Indian / International Ticker Detection
# ──────────────────────────────────────────────

# Well-known Indian company tickers (without suffix)
INDIAN_TICKERS = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "AXISBANK",
    "BAJFINANCE", "MARUTI", "HCLTECH", "WIPRO", "ASIANPAINT",
    "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "NTPC", "POWERGRID",
    "ULTRACEMCO", "NESTLEIND", "TITAN", "ADANIENT", "ADANIPORTS",
    "TECHM", "ONGC", "COALINDIA", "JSWSTEEL", "BAJAJFINSV",
    "DIVISLAB", "DRREDDY", "CIPLA", "BRITANNIA", "GRASIM",
    "HDFCLIFE", "SBILIFE", "INDUSINDBK", "HEROMOTOCO", "EICHERMOT",
    "APOLLOHOSP", "TATACONSUM", "BPCL", "HINDALCO",
}

# Known international exchange suffixes
EXCHANGE_SUFFIXES = {
    ".NS": "NSE (India)",
    ".BO": "BSE (India)",
    ".L": "LSE (London)",
    ".T": "TSE (Tokyo)",
    ".HK": "HKEX (Hong Kong)",
    ".DE": "XETRA (Germany)",
    ".PA": "Euronext Paris",
    ".AS": "Euronext Amsterdam",
    ".TO": "TSX (Toronto)",
    ".AX": "ASX (Australia)",
    ".SS": "SSE (Shanghai)",
    ".SZ": "SZSE (Shenzhen)",
    ".KS": "KRX (Korea)",
    ".SI": "SGX (Singapore)",
}


def is_international_ticker(ticker: str) -> bool:
    """Check if a ticker is for an international (non-US) market."""
    upper = ticker.upper()
    for suffix in EXCHANGE_SUFFIXES:
        if upper.endswith(suffix.upper()):
            return True
    if upper in INDIAN_TICKERS:
        return True
    return False


def normalize_ticker(ticker: str) -> str:
    """Auto-append exchange suffix for known markets.

    Rules:
        - Known Indian tickers without suffix -> append .NS (NSE is primary)
        - Already has a suffix -> keep as-is
        - Unknown -> keep as-is (assume US)
    """
    upper = ticker.upper()
    for suffix in EXCHANGE_SUFFIXES:
        if upper.endswith(suffix.upper()):
            return ticker
    if upper in INDIAN_TICKERS:
        return f"{upper}.NS"
    return ticker


# ──────────────────────────────────────────────
#  SEC EDGAR (US Companies)
# ──────────────────────────────────────────────

async def _get_ticker_map() -> dict[str, tuple[str, str]]:
    """Ticker -> (zero-padded CIK, company name), cached for a day."""
    cached = _ticker_map_cache.get("map")
    if cached is not None:
        return cached

    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        data = (await _sec_get(url, timeout=20.0)).json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="SEC EDGAR connection timed out. Please try again.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"SEC EDGAR returned error: {e.response.status_code}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach SEC EDGAR: {str(e)[:200]}",
        )

    mapping = {
        entry.get("ticker", "").upper(): (str(entry["cik_str"]).zfill(10), entry.get("title", ""))
        for entry in data.values()
    }
    _ticker_map_cache.set("map", mapping)
    return mapping


async def resolve_ticker_to_cik(ticker: str) -> tuple[str, str]:
    """Resolve a stock ticker to its SEC CIK number and company name."""
    mapping = await _get_ticker_map()
    found = mapping.get(ticker.upper())
    if found:
        return found
    raise HTTPException(
        status_code=404,
        detail=f"Ticker '{ticker}' not found in SEC EDGAR database.",
    )


async def get_company_facts(cik: str) -> dict:
    """Fetch all XBRL company facts from SEC EDGAR."""
    return await _sec_get_json(f"{SEC_EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json")


async def get_submissions(cik: str) -> dict:
    """Fetch the filing index and company metadata (incl. SIC code)."""
    return await _sec_get_json(f"{SEC_EDGAR_BASE}/submissions/CIK{cik}.json")


def _annual_entries(facts: dict, tag: str, taxonomy: str = "us-gaap", unit: str = "USD") -> list[dict]:
    concept = facts.get("facts", {}).get(taxonomy, {}).get(tag)
    if not concept:
        return []
    return [
        v for v in concept.get("units", {}).get(unit, [])
        if v.get("form") in ANNUAL_FORMS and v.get("val") is not None and v.get("end")
    ]


def _is_annual_duration(entry: dict) -> bool:
    start, end = entry.get("start"), entry.get("end")
    if not start or not end:
        return False
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        return False
    return 330 <= days <= 400


def find_fiscal_period_end(facts: dict) -> str | None:
    """Latest balance-sheet date reported in an annual filing (from total Assets)."""
    entries = [e for e in _annual_entries(facts, "Assets") if not e.get("start")]
    if not entries:
        return None
    return max(e["end"] for e in entries)


def extract_value_for_period(
    facts: dict,
    concept_tags: list[str],
    period_end: str,
    duration: bool,
) -> float | None:
    """Value for the given fiscal period, from the first tag that reports it.

    Balance-sheet (instant) values must be dated `period_end`; income-statement
    (duration) values must cover a ~12-month period ending on `period_end`.
    If a period was restated, the most recently filed figure wins.
    """
    for tag in concept_tags:
        matches = [
            e for e in _annual_entries(facts, tag)
            if e["end"] == period_end
            and (_is_annual_duration(e) if duration else not e.get("start"))
        ]
        if matches:
            latest = max(matches, key=lambda e: e.get("filed", ""))
            return float(latest["val"])
    return None


def extract_latest_annual_value(facts: dict, concept_tags: list[str]) -> float | None:
    """Most recent annual value across tags (kept for ad-hoc lookups).

    Prefer extract_value_for_period() when combining several metrics, so they
    all describe the same fiscal year.
    """
    best: dict | None = None
    for tag in concept_tags:
        for e in _annual_entries(facts, tag):
            if best is None or e["end"] > best["end"]:
                best = e
    return float(best["val"]) if best else None


def _extract_total_liabilities(facts: dict, period_end: str) -> float | None:
    """Total liabilities, derived from L+E minus equity if not reported directly."""
    direct = extract_value_for_period(facts, XBRL_CONCEPT_MAP["total_liabilities"], period_end, False)
    if direct is not None:
        return direct
    liab_and_equity = extract_value_for_period(facts, ["LiabilitiesAndStockholdersEquity"], period_end, False)
    equity = extract_value_for_period(
        facts,
        ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "StockholdersEquity"],
        period_end,
        False,
    )
    if liab_and_equity is not None and equity is not None:
        return liab_and_equity - equity
    return None


def _extract_public_float(facts: dict) -> float | None:
    """Latest dei:EntityPublicFloat — market value of non-affiliate shares."""
    concept = facts.get("facts", {}).get("dei", {}).get("EntityPublicFloat")
    if not concept:
        return None
    values = [v for v in concept.get("units", {}).get("USD", []) if v.get("val")]
    if not values:
        return None
    return float(max(values, key=lambda v: v.get("end", ""))["val"])


async def fetch_market_cap(ticker: str, facts: dict | None = None) -> float | None:
    """Market value of equity: Yahoo Finance first, SEC public float as fallback."""
    info = await get_yahoo_info(ticker)
    cap = info.get("marketCap") if info else None
    if cap:
        return float(cap)
    if facts is not None:
        return _extract_public_float(facts)
    return None


async def fetch_financial_data_from_edgar(ticker: str) -> FinancialData:
    """Fetch and assemble financial data from SEC EDGAR for Z-Score calculation.

    All values are aligned to a single fiscal year-end.
    """
    cik, _ = await resolve_ticker_to_cik(ticker)
    facts, submissions = await asyncio.gather(get_company_facts(cik), get_submissions(cik))

    sic_code = None
    try:
        sic_code = int(submissions.get("sic") or 0) or None
    except (TypeError, ValueError):
        pass

    if sic_code is not None and 6000 <= sic_code <= 6799:
        raise ZScoreNotApplicable(
            f"{ticker.upper()} is a financial company (SIC {sic_code}). The Altman Z-Score "
            "is not applicable to banks, insurers or investment firms."
        )

    period_end = find_fiscal_period_end(facts)
    if period_end is None:
        raise HTTPException(
            status_code=422,
            detail=f"No annual (10-K) balance sheet found in {ticker}'s XBRL data.",
        )

    extracted: dict[str, float] = {}
    missing_fields = []

    for field, concepts in XBRL_CONCEPT_MAP.items():
        if field == "total_liabilities":
            value = _extract_total_liabilities(facts, period_end)
        else:
            value = extract_value_for_period(facts, concepts, period_end, field in DURATION_FIELDS)
        if value is not None:
            extracted[field] = value
        else:
            missing_fields.append(field)

    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract the following metrics from {ticker}'s 10-K filing "
                   f"for the fiscal year ending {period_end}: {', '.join(missing_fields)}. "
                   "Manual input may be required.",
        )

    market_cap = await fetch_market_cap(ticker, facts)

    return FinancialData(
        ticker=ticker.upper(),
        market_cap=market_cap,
        sic_code=sic_code,
        fiscal_period_end=period_end,
        **extracted,
    )


# ──────────────────────────────────────────────
#  10-K Full-Text Section Extraction
# ──────────────────────────────────────────────

MAX_SECTION_CHARS = 40_000

_HIDDEN_BLOCKS = re.compile(
    r"<(script|style|ix:header)\b.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


def _decode_filing(raw: bytes) -> str:
    """Filings are mostly UTF-8, but older and some current ones are Windows-1252."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# Tags that end a visual line; table cells stay on their row's line
_BLOCK_END = re.compile(r"<(?:br\b[^>]*|/(?:p|div|tr|li|h[1-6]|table|center)\s*)>", re.IGNORECASE)
_CELL_BOUNDARY = re.compile(r"<(?:/?t[dh]\b[^>]*|p\b[^>]*|div\b[^>]*)>", re.IGNORECASE)


def _strip_html_tags(html_text: str) -> str:
    """Remove HTML tags, hidden inline-XBRL data and decode entities.

    Block-level boundaries are kept as newlines so section headings can be
    told apart from mid-sentence cross-references.
    """
    clean = _HIDDEN_BLOCKS.sub(" ", html_text)
    clean = _BLOCK_END.sub("\n", clean)
    clean = _CELL_BOUNDARY.sub(" ", clean)
    # Inline tags (span, font, b, a...) don't separate words when rendered;
    # filings often split a single word across several spans.
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = html_module.unescape(clean)
    clean = re.sub(r'[^\S\n]+', ' ', clean)       # collapse spaces, keep newlines
    clean = re.sub(r' ?\n[\s]*', '\n', clean)     # collapse blank lines
    return clean.strip()


def _find_spans(
    text: str, start_re: re.Pattern, end_re: re.Pattern, keep_first_start: bool,
) -> list[tuple[int, int]]:
    """Candidate (begin, end) spans, one per distinct end marker.

    When several starts share an end marker, keep_first_start picks the first
    (running page headers repeat the heading on every page) rather than the
    last (the heading nearest the section, when cross-references can't be
    told apart from headings).
    """
    spans_by_end: dict[int, tuple[int, int]] = {}
    for start_match in start_re.finditer(text):
        end_match = end_re.search(text, start_match.end())
        if not end_match:
            continue
        key = end_match.start()
        if keep_first_start and key in spans_by_end:
            continue
        spans_by_end[key] = (start_match.end(), end_match.start())
    return list(spans_by_end.values())


def _extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
    """Extract a section from 10-K text between two Item headings.

    A 10-K mentions each Item several times: in the table of contents, in
    cross-references ("see Item 8 of this Form 10-K"), and at the real heading.
    Markers are first matched only at the start of a line, where headings
    live; cross-references sit mid-sentence. Candidates are grouped by end
    marker and the longest is returned — the table-of-contents entry is only
    a few words long. If the document has no line structure, matching falls
    back to anywhere in the text.
    """
    line_start = r'(?:^|\n)[ \t]*(?:part\s+[iv]+[\.\:\s\-—–]*)?'
    spans = _find_spans(
        text,
        re.compile(line_start + f'(?:{start_pattern})', re.IGNORECASE),
        re.compile(line_start + f'(?:{end_pattern})', re.IGNORECASE),
        keep_first_start=True,
    )
    if not spans:
        spans = _find_spans(
            text,
            re.compile(start_pattern, re.IGNORECASE),
            re.compile(end_pattern, re.IGNORECASE),
            keep_first_start=False,
        )
    if not spans:
        return ""

    begin, finish = max(spans, key=lambda span: span[1] - span[0])
    section = re.sub(r'\s+', ' ', text[begin:finish]).strip()
    return section[:MAX_SECTION_CHARS]


# End markers must include the next heading's title: MD&A routinely says
# "...included in Part II, Item 8 of this Form 10-K", which is not a heading.
_SEP = r'[\.\:\s\-—–]*'
RISK_FACTORS_START = rf'item\s*1a{_SEP}risk\s*factors'
RISK_FACTORS_END = (
    rf'item\s*(?:1b{_SEP}unresolved\s*staff|1c{_SEP}cybersecurity|2{_SEP}(?:properties|description\s*of\s*propert))'
)
MDA_START = rf'item\s*7{_SEP}management[\'’]?s?\s*discussion'
MDA_END = rf'item\s*(?:7a{_SEP}quantitative\s*and\s*qualitative|8{_SEP}financial\s*statements)'


async def _latest_10k_url(cik: str) -> str | None:
    submissions = await get_submissions(cik)
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form == "10-K" and i < len(accession_numbers) and i < len(primary_docs):
            acc = accession_numbers[i].replace("-", "")
            doc = primary_docs[i]
            return f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc}/{doc}"
    return None


async def fetch_10k_text_sections(ticker: str) -> dict[str, str]:
    """Fetch and extract key text sections from the latest 10-K filing."""
    cik, _ = await resolve_ticker_to_cik(ticker)

    filing_url = await _latest_10k_url(cik)
    if not filing_url:
        return {"risk_factors": "", "mda": "", "error": "No 10-K filing found"}

    plain_text = _filing_text_cache.get(filing_url)
    if plain_text is None:
        raw_html = _decode_filing((await _sec_get(filing_url, timeout=45.0)).content)
        # Regex over a multi-MB document is CPU-bound; keep it off the event loop
        plain_text = await asyncio.to_thread(_strip_html_tags, raw_html)
        _filing_text_cache.set(filing_url, plain_text)

    risk_factors, mda = await asyncio.gather(
        asyncio.to_thread(_extract_section, plain_text, RISK_FACTORS_START, RISK_FACTORS_END),
        asyncio.to_thread(_extract_section, plain_text, MDA_START, MDA_END),
    )

    return {
        "risk_factors": risk_factors,
        "mda": mda,
    }


# ──────────────────────────────────────────────
#  Yahoo Finance via yfinance (Global Markets)
# ──────────────────────────────────────────────
# yfinance is synchronous and network-bound, so every call runs in a worker
# thread to keep the event loop free for other requests.

def _yahoo_info_sync(ticker: str) -> dict:
    import yfinance as yf
    return yf.Ticker(ticker).info or {}


async def get_yahoo_info(ticker: str) -> dict:
    """Cached yfinance `info` dict; empty dict on any failure."""
    key = ticker.upper()
    cached = _yahoo_info_cache.get(key)
    if cached is not None:
        return cached
    try:
        info = await asyncio.to_thread(_yahoo_info_sync, ticker)
    except Exception:
        return {}
    _yahoo_info_cache.set(key, info)
    return info


def _safe_get(series, keys, default=None):
    """Try multiple key names against a pandas Series."""
    if hasattr(series, 'get'):
        for key in keys:
            val = series.get(key)
            if val is not None and str(val) != 'nan':
                return float(val)
    return default


def _fetch_financial_data_yahoo_sync(normalized: str, info: dict) -> FinancialData:
    import yfinance as yf

    stock = yf.Ticker(normalized)
    bs = stock.balance_sheet
    financials = stock.financials

    if bs is None or bs.empty:
        raise HTTPException(
            status_code=422,
            detail=f"No balance sheet data available for '{normalized}' on Yahoo Finance.",
        )

    latest_bs = bs.iloc[:, 0]
    period_end = str(bs.columns[0])[:10]
    latest_fin = {}
    if financials is not None and not financials.empty:
        # Use the income statement for the same fiscal year as the balance sheet
        matching = [c for c in financials.columns if str(c)[:10] == period_end]
        latest_fin = financials[matching[0]] if matching else financials.iloc[:, 0]

    total_assets = _safe_get(latest_bs, ["Total Assets", "TotalAssets"])
    current_assets = _safe_get(latest_bs, ["Current Assets", "CurrentAssets"])
    current_liabilities = _safe_get(latest_bs, ["Current Liabilities", "CurrentLiabilities"])
    retained_earnings = _safe_get(latest_bs, ["Retained Earnings", "RetainedEarnings"])
    total_liabilities = _safe_get(latest_bs, ["Total Liabilities Net Minority Interest", "Total Liab", "TotalLiabilitiesNetMinorityInterest"])
    ebit = _safe_get(latest_fin, ["EBIT", "Operating Income", "OperatingIncome"])
    revenue = _safe_get(latest_fin, ["Total Revenue", "TotalRevenue", "Revenue"])
    market_cap = info.get("marketCap")

    missing = []
    if total_assets is None: missing.append("total_assets")
    if current_assets is None: missing.append("current_assets")
    if current_liabilities is None: missing.append("current_liabilities")
    if total_liabilities is None: missing.append("total_liabilities")
    if revenue is None: missing.append("revenue")

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract from Yahoo Finance for '{normalized}': {', '.join(missing)}.",
        )

    return FinancialData(
        ticker=normalized.upper(),
        total_assets=total_assets,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        retained_earnings=retained_earnings if retained_earnings is not None else 0.0,
        ebit=ebit if ebit is not None else 0.0,
        market_cap=float(market_cap) if market_cap else None,
        total_liabilities=total_liabilities,
        revenue=revenue,
        sector=info.get("sector") or "Unknown",
        fiscal_period_end=period_end,
    )


async def fetch_financial_data_yahoo(ticker: str) -> FinancialData:
    """Fetch financial data from Yahoo Finance using yfinance.

    Supports global tickers including BSE/NSE (.NS/.BO suffixes),
    LSE (.L), TSE (.T), and all major world exchanges.
    """
    try:
        import yfinance  # noqa: F401
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"yfinance could not be imported: {str(e)[:200]}",
        )

    normalized = normalize_ticker(ticker)
    info = await get_yahoo_info(normalized)

    if (info.get("sector") or "").lower() == "financial services":
        raise ZScoreNotApplicable(
            f"{normalized.upper()} is a financial company. The Altman Z-Score "
            "is not applicable to banks, insurers or investment firms."
        )

    try:
        return await asyncio.to_thread(_fetch_financial_data_yahoo_sync, normalized, info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Yahoo Finance data fetch failed for '{normalized}': {str(e)[:300]}",
        )


async def fetch_financial_data_auto(ticker: str) -> tuple[FinancialData, str]:
    """Smart routing: fetch from SEC EDGAR (US) or Yahoo Finance (international).

    ZScoreNotApplicable propagates without a fallback: another data source
    would not make a bank a valid Altman subject.
    """
    if is_international_ticker(ticker):
        data = await fetch_financial_data_yahoo(ticker)
        return data, "Yahoo Finance"

    try:
        data = await fetch_financial_data_from_edgar(ticker)
        return data, "SEC EDGAR"
    except HTTPException:
        data = await fetch_financial_data_yahoo(ticker)
        return data, "Yahoo Finance (fallback)"


async def get_company_name(ticker: str) -> str:
    """Best-effort display name for a ticker."""
    if is_international_ticker(ticker):
        info = await get_yahoo_info(normalize_ticker(ticker))
        return info.get("longName") or info.get("shortName") or ticker.upper()
    try:
        _, name = await resolve_ticker_to_cik(ticker)
        return name or ticker.upper()
    except HTTPException:
        return ticker.upper()


# ──────────────────────────────────────────────
#  API Endpoints
# ──────────────────────────────────────────────

@router.get(
    "/company/{ticker}",
    response_model=CompanyInfo,
    summary="Get Company Info",
    description="Resolve a stock ticker to company information.",
)
async def api_company_info(ticker: str) -> CompanyInfo:
    if is_international_ticker(ticker):
        normalized = normalize_ticker(ticker)
        info = await get_yahoo_info(normalized)
        return CompanyInfo(
            ticker=normalized.upper(),
            name=info.get("longName") or info.get("shortName") or normalized.upper(),
            cik=None,
            sector=info.get("sector"),
        )
    cik, name = await resolve_ticker_to_cik(ticker)
    return CompanyInfo(ticker=ticker.upper(), name=name, cik=cik)


@router.get(
    "/financials/{ticker}",
    response_model=FinancialData,
    summary="Fetch Financial Data (Auto-Routed)",
    description="Fetch the latest financial data for a company. "
                "Automatically routes US tickers to SEC EDGAR and international tickers "
                "(BSE/NSE/LSE etc.) to Yahoo Finance.",
)
async def api_financials(ticker: str) -> FinancialData:
    try:
        data, _ = await fetch_financial_data_auto(ticker)
    except ZScoreNotApplicable as e:
        raise HTTPException(status_code=422, detail=str(e))
    return data


@router.get(
    "/financials-global/{ticker}",
    response_model=FinancialData,
    summary="Fetch Global Financial Data (Yahoo Finance)",
    description="Fetch financial data from Yahoo Finance. "
                "Supports all major world exchanges including BSE (.BO) and NSE (.NS).",
)
async def api_financials_global(ticker: str) -> FinancialData:
    try:
        return await fetch_financial_data_yahoo(ticker)
    except ZScoreNotApplicable as e:
        raise HTTPException(status_code=422, detail=str(e))
