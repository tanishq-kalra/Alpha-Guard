"""
Alpha-Guard — Financial Data Ingestion
=======================================
Data sources:
  1. SEC EDGAR (primary) — Free JSON API at data.sec.gov for 10-K XBRL data
  2. Yahoo Finance (secondary/fallback) — Playwright-based web scraping
"""

import re
import html as html_module
import httpx
from fastapi import APIRouter, HTTPException

from models import FinancialData, CompanyInfo

router = APIRouter(prefix="/api/data", tags=["Data Ingestion"])

# SEC EDGAR API base — no authentication required
SEC_EDGAR_BASE = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": "Alpha-Guard Research alpha-guard@research.dev",
    "Accept": "application/json",
}

# Mapping of common XBRL US-GAAP concept tags to our FinancialData fields
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
    ],
    "total_liabilities": [
        "Liabilities",
    ],
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
}


async def resolve_ticker_to_cik(ticker: str) -> tuple[str, str]:
    """Resolve a stock ticker to its SEC CIK number and company name.

    Uses the SEC's company_tickers.json endpoint which maps all tickers
    to their CIK identifiers.

    Returns:
        Tuple of (cik_padded_to_10_digits, company_name)

    Raises:
        HTTPException: If the ticker is not found or SEC is unreachable.
    """
    # NOTE: The tickers JSON lives on www.sec.gov, NOT data.sec.gov
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=SEC_HEADERS, timeout=20.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectTimeout:
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

    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            name = entry.get("title", "")
            return cik, name

    raise HTTPException(
        status_code=404,
        detail=f"Ticker '{ticker}' not found in SEC EDGAR database.",
    )


async def get_company_facts(cik: str) -> dict:
    """Fetch all XBRL company facts from SEC EDGAR.

    Endpoint: /api/xbrl/companyfacts/CIK{cik}.json

    Returns the full JSON payload containing all reported financial concepts.
    """
    url = f"{SEC_EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=SEC_HEADERS, timeout=30.0)
        resp.raise_for_status()
        return resp.json()


def extract_latest_annual_value(facts: dict, concept_tags: list[str]) -> float | None:
    """Extract the most recent 10-K annual value for a given financial concept.

    Searches through the us-gaap taxonomy for matching concept tags.
    Filters for 10-K filings (form = '10-K') and returns the latest value.

    Args:
        facts: The 'facts' object from the companyfacts API response.
        concept_tags: List of XBRL concept names to search (in priority order).

    Returns:
        The numeric value, or None if not found.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    for tag in concept_tags:
        concept = us_gaap.get(tag)
        if not concept:
            continue

        units = concept.get("units", {})
        # Financial values are typically in USD
        values = units.get("USD", [])

        # Filter for 10-K filings only
        annual_values = [
            v for v in values
            if v.get("form") == "10-K" and v.get("val") is not None
        ]

        if not annual_values:
            continue

        # Sort by filing date (descending) and take the latest
        annual_values.sort(key=lambda x: x.get("end", ""), reverse=True)
        return float(annual_values[0]["val"])

    return None


async def fetch_financial_data_from_edgar(ticker: str) -> FinancialData:
    """Fetch and assemble financial data from SEC EDGAR for Z-Score calculation.

    Pipeline:
        1. Resolve ticker → CIK
        2. Fetch all company facts (XBRL)
        3. Extract each required metric from the latest 10-K filing
        4. Return assembled FinancialData

    Note: market_cap is not available from SEC filings — a default placeholder
    is used. In production, this would be supplemented by a market data API.
    """
    cik, company_name = await resolve_ticker_to_cik(ticker)
    facts = await get_company_facts(cik)

    extracted = {}
    missing_fields = []

    for field, concepts in XBRL_CONCEPT_MAP.items():
        value = extract_latest_annual_value(facts, concepts)
        if value is not None:
            extracted[field] = value
        else:
            missing_fields.append(field)

    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract the following metrics from {ticker}'s 10-K filing: "
                   f"{', '.join(missing_fields)}. Manual input may be required.",
        )

    # Market cap placeholder — in production, source from a market data provider
    if "market_cap" not in extracted:
        extracted["market_cap"] = extracted.get("total_assets", 1_000_000)  # Rough proxy

    return FinancialData(ticker=ticker.upper(), **extracted)


# ──────────────────────────────────────────────
#  10-K Full-Text Section Extraction
# ──────────────────────────────────────────────

def _strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    clean = re.sub(r'<[^>]+>', ' ', html_text)
    clean = html_module.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
    """Extract a section from 10-K text between two Item markers.

    Uses case-insensitive regex to find section boundaries.
    Returns the text between the markers, truncated to ~15000 chars for API limits.
    """
    pattern = re.compile(
        rf'{start_pattern}(.*?){end_pattern}',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(text)
    if match:
        section_text = match.group(1).strip()
        return section_text[:15000] if len(section_text) > 15000 else section_text
    return ""


async def fetch_10k_text_sections(ticker: str) -> dict[str, str]:
    """Fetch and extract key text sections from the latest 10-K filing.

    Pipeline:
        1. Resolve ticker → CIK
        2. Query SEC EDGAR filing index for latest 10-K
        3. Fetch the primary document HTML
        4. Extract Item 1A (Risk Factors) and Item 7 (MD&A)

    Returns:
        Dict with keys 'risk_factors' and 'mda', each containing extracted text.
    """
    cik, _ = await resolve_ticker_to_cik(ticker)

    # Query EDGAR submissions API for recent filings
    submissions_url = f"{SEC_EDGAR_BASE}/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=5&search_text=&action=getcompany&output=atom"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Try the submissions JSON endpoint first
        sub_url = f"{SEC_EDGAR_BASE}/submissions/CIK{cik}.json"
        resp = await client.get(sub_url, headers=SEC_HEADERS, timeout=20.0)
        resp.raise_for_status()
        submissions = resp.json()

        # Find latest 10-K in recent filings
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        filing_url = None
        for i, form in enumerate(forms):
            if form == "10-K" and i < len(accession_numbers) and i < len(primary_docs):
                acc = accession_numbers[i].replace("-", "")
                doc = primary_docs[i]
                filing_url = f"{SEC_EDGAR_BASE}/Archives/edgar/data/{cik.lstrip('0')}/{acc}/{doc}"
                break

        if not filing_url:
            return {"risk_factors": "", "mda": "", "error": "No 10-K filing found"}

        # Fetch the full filing document
        doc_resp = await client.get(filing_url, headers=SEC_HEADERS, timeout=30.0)
        doc_resp.raise_for_status()
        raw_html = doc_resp.text

    # Strip HTML to get plain text
    plain_text = _strip_html_tags(raw_html)

    # Extract sections using Item markers
    # Item 1A: Risk Factors → ends at Item 1B or Item 2
    risk_factors = _extract_section(
        plain_text,
        r'item\s*1a[\.\:\s]*risk\s*factors',
        r'item\s*(?:1b|2)[\.\:\s]'
    )

    # Item 7: MD&A → ends at Item 7A or Item 8
    mda = _extract_section(
        plain_text,
        r'item\s*7[\.\:\s]*management[\'\u2019]?s?\s*discussion',
        r'item\s*(?:7a|8)[\.\:\s]'
    )

    return {
        "risk_factors": risk_factors,
        "mda": mda,
    }


# ──────────────────────────────────────────────
#  Yahoo Finance Scraper (Playwright-based)
# ──────────────────────────────────────────────

async def scrape_yahoo_finance(ticker: str) -> dict:
    """Scrape financial data from Yahoo Finance using Playwright.

    Target pages:
        - https://finance.yahoo.com/quote/{ticker}/financials/
        - https://finance.yahoo.com/quote/{ticker}/balance-sheet/

    Key HTML structure (identified via browser inspection):
        - Financial tables use <div class="tableBody"> containers
        - Row labels are in <div class="rowTitle"> elements
        - Values are in <div class="column"> elements
        - Period headers (Annual/Quarterly) toggle data views

    This is a SECONDARY data source — used when SEC EDGAR data is
    incomplete or when market-cap data is needed.

    Returns:
        Dict with extracted financial metrics, or empty dict if scraping fails.

    Note:
        This function requires Playwright to be installed and configured.
        Run `playwright install chromium` before first use.
    """
    # Playwright integration is designed for use with the browser agent.
    # Direct programmatic scraping structure:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    result = {}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # --- Income Statement ---
            await page.goto(
                f"https://finance.yahoo.com/quote/{ticker}/financials/",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await page.wait_for_timeout(3000)  # Allow dynamic content to load

            # Extract revenue from the financials table
            revenue_rows = await page.query_selector_all('[data-test="fin-row"]')
            for row in revenue_rows:
                title_el = await row.query_selector('[data-test="fin-col-0"]')
                if title_el:
                    title = await title_el.inner_text()
                    if "Total Revenue" in title:
                        value_el = await row.query_selector('[data-test="fin-col-1"]')
                        if value_el:
                            val_text = await value_el.inner_text()
                            result["revenue"] = val_text

            # --- Balance Sheet ---
            await page.goto(
                f"https://finance.yahoo.com/quote/{ticker}/balance-sheet/",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await page.wait_for_timeout(3000)

            balance_rows = await page.query_selector_all('[data-test="fin-row"]')
            for row in balance_rows:
                title_el = await row.query_selector('[data-test="fin-col-0"]')
                if title_el:
                    title = await title_el.inner_text()
                    value_el = await row.query_selector('[data-test="fin-col-1"]')
                    if value_el:
                        val_text = await value_el.inner_text()
                        if "Total Assets" in title:
                            result["total_assets"] = val_text
                        elif "Total Liabilities" in title:
                            result["total_liabilities"] = val_text
                        elif "Retained Earnings" in title:
                            result["retained_earnings"] = val_text

            await browser.close()

    except Exception as e:
        result["error"] = f"Yahoo Finance scraping failed: {str(e)}"

    return result


# ──────────────────────────────────────────────
#  API Endpoints
# ──────────────────────────────────────────────

@router.get(
    "/company/{ticker}",
    response_model=CompanyInfo,
    summary="Get Company Info",
    description="Resolve a stock ticker to company information via SEC EDGAR.",
)
async def api_company_info(ticker: str) -> CompanyInfo:
    cik, name = await resolve_ticker_to_cik(ticker)
    return CompanyInfo(ticker=ticker.upper(), name=name, cik=cik)


@router.get(
    "/financials/{ticker}",
    response_model=FinancialData,
    summary="Fetch Financial Data",
    description="Fetch the latest 10-K financial data for a company from SEC EDGAR. "
                "Returns all metrics needed for Altman Z-Score calculation.",
)
async def api_financials(ticker: str) -> FinancialData:
    return await fetch_financial_data_from_edgar(ticker)


@router.get(
    "/yahoo/{ticker}",
    summary="Scrape Yahoo Finance (Fallback)",
    description="Scrape financial data from Yahoo Finance using Playwright. "
                "Use as a fallback when SEC EDGAR data is incomplete.",
)
async def api_yahoo_scrape(ticker: str) -> dict:
    return await scrape_yahoo_finance(ticker)
