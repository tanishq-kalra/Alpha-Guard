"""
Alpha-Guard — Risk Engine
=========================
Financial risk analysis engine implementing:
  1. Altman Z-Score (original and Z'' variants, auto-selected per company)
  2. Monte Carlo Simulation (geometric Brownian motion revenue stress test)
"""

import numpy as np
from fastapi import APIRouter, HTTPException

from models import FinancialData, ZScoreResult, ZScoreComponents, MonteCarloInput, MonteCarloResult

router = APIRouter(prefix="/api/risk", tags=["Risk Analysis"])

# ──────────────────────────────────────────────
#  Altman Z-Score
# ──────────────────────────────────────────────

# Coefficients and zone thresholds for each Altman model variant.
#   original       — Altman (1968), publicly traded manufacturers; X4 uses market equity
#   z_double_prime — Altman (1995) Z'', non-manufacturers & emerging markets; X4 uses
#                    book equity and drops X5 (asset turnover varies too much by industry)
Z_MODELS = {
    "original": {
        "label": "Altman Z (1968) — public manufacturers",
        "weights": {"x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0},
        "safe": 2.99,
        "distress": 1.81,
        "x4_basis": "market",
    },
    "z_double_prime": {
        "label": "Altman Z'' (1995) — non-manufacturers / emerging markets",
        "weights": {"x1": 6.56, "x2": 3.26, "x3": 6.72, "x4": 1.05, "x5": 0.0},
        "safe": 2.60,
        "distress": 1.10,
        "x4_basis": "book",
    },
}

# Kept for callers that import the original-model constants
ALTMAN_WEIGHTS = Z_MODELS["original"]["weights"]
SAFE_THRESHOLD = Z_MODELS["original"]["safe"]
DISTRESS_THRESHOLD = Z_MODELS["original"]["distress"]


class ZScoreNotApplicable(ValueError):
    """Raised when no Altman variant is valid for the company (e.g. banks, insurers)."""


def is_financial_company(data: FinancialData) -> bool:
    """Banks, insurers, brokers and investment trusts (SIC 6000-6799)."""
    if data.sic_code is not None and 6000 <= data.sic_code <= 6799:
        return True
    return (data.sector or "").strip().lower() in {"financial services", "financials", "financial"}


def select_z_model(data: FinancialData) -> str:
    """Pick the Altman variant appropriate for this company.

    Raises:
        ZScoreNotApplicable: for financial companies, whose balance sheets
            (no current/non-current split, leverage as the business model)
            fall outside every Altman model's design.
        ValueError: if the original model is forced without a market cap.
    """
    if is_financial_company(data):
        raise ZScoreNotApplicable(
            "The Altman Z-Score is not applicable to financial institutions "
            "(banks, insurers, investment firms). Their leverage and balance-sheet "
            "structure fall outside the model's design."
        )

    if data.z_model != "auto":
        if data.z_model == "original" and data.market_cap is None:
            raise ValueError("The original Altman model requires market_cap.")
        return data.z_model

    if data.market_cap is None:
        return "z_double_prime"
    if data.sic_code is not None:
        # SIC 2000-3999 = manufacturing, the population the original model was fit on
        return "original" if 2000 <= data.sic_code <= 3999 else "z_double_prime"
    if data.sector is not None:
        # Yahoo Finance data (typically non-US) with no SIC code: Altman recommends
        # Z'' for emerging markets and for firms outside US manufacturing.
        return "z_double_prime"
    # Manually supplied figures with a market cap: use the classic model
    return "original"


def classify_zone(score: float, model: str = "original") -> tuple[str, str]:
    """Classify Z-Score into risk zones with human-readable interpretation.

    Returns:
        Tuple of (zone_name, interpretation_string)
    """
    safe = Z_MODELS[model]["safe"]
    distress = Z_MODELS[model]["distress"]
    if score > safe:
        return (
            "Safe",
            f"Z-Score of {score:.2f} indicates strong financial health. "
            "The company is in the Safe Zone with low bankruptcy probability."
        )
    elif score > distress:
        return (
            "Gray",
            f"Z-Score of {score:.2f} places the company in the Gray Zone. "
            "Financial health is uncertain — further analysis is recommended."
        )
    else:
        return (
            "Distress",
            f"Z-Score of {score:.2f} signals significant financial distress. "
            "The company is in the Distress Zone with elevated bankruptcy risk within 2 years."
        )


def calculate_altman_z_score(data: FinancialData) -> ZScoreResult:
    """Calculate the Altman Z-Score using the variant suited to the company.

    Original (manufacturers):
        Z   = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
    Z'' (non-manufacturers / emerging markets):
        Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4

    Where:
        X1 = (Current Assets − Current Liabilities) / Total Assets
        X2 = Retained Earnings / Total Assets
        X3 = EBIT / Total Assets
        X4 = Equity / Total Liabilities  (market equity for Z, book equity for Z'')
        X5 = Revenue / Total Assets

    Raises:
        ZScoreNotApplicable: for financial companies.
        ValueError: If total_assets or total_liabilities are zero/negative.
    """
    if data.total_assets <= 0:
        raise ValueError("Total assets must be positive for Z-Score calculation.")
    if data.total_liabilities <= 0:
        raise ValueError("Total liabilities must be positive for Z-Score calculation.")

    model = select_z_model(data)
    spec = Z_MODELS[model]
    weights = spec["weights"]

    if spec["x4_basis"] == "market":
        equity = data.market_cap
    else:
        equity = data.total_assets - data.total_liabilities

    # Compute the 5 component ratios
    working_capital = data.current_assets - data.current_liabilities
    x1 = working_capital / data.total_assets
    x2 = data.retained_earnings / data.total_assets
    x3 = data.ebit / data.total_assets
    x4 = equity / data.total_liabilities
    x5 = data.revenue / data.total_assets

    # Weighted sum
    score = (
        weights["x1"] * x1
        + weights["x2"] * x2
        + weights["x3"] * x3
        + weights["x4"] * x4
        + weights["x5"] * x5
    )

    zone, interpretation = classify_zone(score, model)

    return ZScoreResult(
        ticker=data.ticker,
        score=round(score, 4),
        zone=zone,
        components=ZScoreComponents(
            x1_working_capital_to_total_assets=round(x1, 6),
            x2_retained_earnings_to_total_assets=round(x2, 6),
            x3_ebit_to_total_assets=round(x3, 6),
            x4_market_cap_to_total_liabilities=round(x4, 6),
            x5_revenue_to_total_assets=round(x5, 6),
        ),
        interpretation=interpretation,
        model=model,
        model_label=spec["label"],
        weights=dict(weights),
        safe_threshold=spec["safe"],
        distress_threshold=spec["distress"],
        x4_basis=spec["x4_basis"],
    )


# ──────────────────────────────────────────────
#  Monte Carlo Simulation
# ──────────────────────────────────────────────

def _format_money_range(low: float, high: float) -> str:
    """Histogram bin label scaled to the magnitude of the values."""
    top = max(abs(low), abs(high))
    if top >= 1e9:
        return f"${low / 1e9:.1f}B-${high / 1e9:.1f}B"
    if top >= 1e6:
        return f"${low / 1e6:.0f}M-${high / 1e6:.0f}M"
    return f"${low:,.0f}-${high:,.0f}"


def run_monte_carlo_simulation(params: MonteCarloInput) -> MonteCarloResult:
    """Run a Monte Carlo simulation for revenue forecasting.

    Uses geometric Brownian motion to simulate N revenue paths over T years.
    Returns summary stats, histogram distribution, and percentile bands.
    """
    rng = np.random.default_rng(params.seed)

    initial_revenue = params.initial_revenue or 1_000_000.0
    n = params.num_simulations
    t = params.time_horizon_years
    mu = params.revenue_growth_mean
    sigma = params.revenue_growth_std

    # Geometric Brownian Motion: S(t+1) = S(t) * exp((mu - 0.5*sigma^2) + sigma*Z)
    drift = mu - 0.5 * sigma ** 2
    random_shocks = rng.standard_normal(size=(n, t))
    log_returns = drift + sigma * random_shocks
    cumulative_returns = np.cumsum(log_returns, axis=1)

    # Revenue matrix: each row is a simulation, each col is a year
    revenue_matrix = initial_revenue * np.exp(
        np.hstack([np.zeros((n, 1)), cumulative_returns])
    )  # shape: (n, t+1) — includes year 0

    # Final revenues
    final_revenues = revenue_matrix[:, -1]

    # Summary stats
    decline_threshold = initial_revenue * 0.80
    prob_decline = float(np.mean(final_revenues < decline_threshold))

    # Build histogram (20 bins)
    hist_counts, bin_edges = np.histogram(final_revenues, bins=20)
    histogram = []
    for i in range(len(hist_counts)):
        low = bin_edges[i]
        high = bin_edges[i + 1]
        histogram.append({
            "range": _format_money_range(low, high),
            "count": int(hist_counts[i]),
            "pct": round(float(hist_counts[i]) / n * 100, 1),
            "midpoint": round(float((low + high) / 2), 2),
        })

    # Percentile bands per year (year 0 through year T), computed in one pass
    pcts = np.percentile(revenue_matrix, [5, 25, 50, 75, 95], axis=0)
    means = revenue_matrix.mean(axis=0)
    sample_paths = [
        {
            "year": year_idx,
            "p5": round(float(pcts[0, year_idx]), 2),
            "p25": round(float(pcts[1, year_idx]), 2),
            "median": round(float(pcts[2, year_idx]), 2),
            "p75": round(float(pcts[3, year_idx]), 2),
            "p95": round(float(pcts[4, year_idx]), 2),
            "mean": round(float(means[year_idx]), 2),
        }
        for year_idx in range(t + 1)
    ]

    return MonteCarloResult(
        ticker=params.ticker,
        num_simulations=n,
        time_horizon_years=t,
        mean_final_revenue=round(float(np.mean(final_revenues)), 2),
        median_final_revenue=round(float(np.median(final_revenues)), 2),
        percentile_5=round(float(np.percentile(final_revenues, 5)), 2),
        percentile_95=round(float(np.percentile(final_revenues, 95)), 2),
        probability_of_decline=round(prob_decline, 4),
        status="active",
        histogram=histogram,
        sample_paths=sample_paths,
        initial_revenue=initial_revenue,
    )


# ──────────────────────────────────────────────
#  API Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/z-score",
    response_model=ZScoreResult,
    summary="Calculate Altman Z-Score",
    description="Compute the Altman Z-Score for a company given its financial metrics. "
                "The model variant (original Z or Z'') is chosen from the company's "
                "classification unless `z_model` is set. Financial companies are rejected.",
)
async def api_z_score(financials: FinancialData) -> ZScoreResult:
    try:
        return calculate_altman_z_score(financials)
    except ValueError as e:  # includes ZScoreNotApplicable
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/monte-carlo",
    response_model=MonteCarloResult,
    summary="Run Monte Carlo Simulation",
    description="Run a Monte Carlo revenue stress test using geometric Brownian motion. "
                "Returns percentile bands per year, a final-revenue histogram and P(decline > 20%).",
)
async def api_monte_carlo(params: MonteCarloInput) -> MonteCarloResult:
    return run_monte_carlo_simulation(params)
