"""
Alpha-Guard — Pydantic Models for Financial Data & Risk Analysis
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


class CompanyInfo(BaseModel):
    """Basic company identification."""
    ticker: str = Field(..., description="Stock ticker symbol", examples=["AAPL"])
    name: Optional[str] = Field(None, description="Company name")
    cik: Optional[str] = Field(None, description="SEC Central Index Key")
    sector: Optional[str] = Field(None, description="Industry sector")


class HistoryPoint(BaseModel):
    """One fiscal year of headline figures (for trend charts and growth statistics)."""
    fiscal_period_end: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None


class FinancialData(BaseModel):
    """Core financial metrics required for Z-Score and risk calculations.

    All monetary values should be in the same currency (typically USD).
    Values are expected from the most recent annual filing (10-K).
    """
    ticker: str = Field(..., description="Stock ticker symbol")
    total_assets: float = Field(..., gt=0, description="Total Assets")
    # Banks and insurers don't report a current/non-current split, so these are optional
    current_assets: Optional[float] = Field(None, ge=0, description="Total Current Assets")
    current_liabilities: Optional[float] = Field(None, ge=0, description="Total Current Liabilities")
    retained_earnings: float = Field(..., description="Retained Earnings (can be negative)")
    ebit: float = Field(..., description="Earnings Before Interest and Taxes")
    market_cap: Optional[float] = Field(
        None, gt=0,
        description="Market Value of Equity. If unknown, the book-equity Z'' model is used.",
    )
    total_liabilities: float = Field(..., gt=0, description="Total Liabilities")
    revenue: float = Field(..., ge=0, description="Total Revenue / Net Sales")
    # Earnings quality (optional) — cash vs accrual earnings
    net_income: Optional[float] = Field(None, description="Net income for the fiscal year")
    operating_cash_flow: Optional[float] = Field(None, description="Net cash from operating activities")
    revenue_prior_year: Optional[float] = Field(None, description="Revenue for the previous fiscal year (growth)")
    history: list[HistoryPoint] = Field(default_factory=list, description="Up to 5 fiscal years, newest first")
    # Classification — drives which Altman model variant applies
    sic_code: Optional[int] = Field(None, description="SEC Standard Industrial Classification code")
    sector: Optional[str] = Field(None, description="Sector name (Yahoo Finance)")
    fiscal_period_end: Optional[str] = Field(None, description="Balance-sheet date all values are aligned to")
    z_model: Literal["auto", "original", "z_double_prime"] = Field(
        "auto",
        description="Altman model: 'original' (public manufacturers), "
                    "'z_double_prime' (non-manufacturers / emerging markets), or 'auto'.",
    )


class ZScoreComponents(BaseModel):
    """Individual Z-Score component ratios.

    x4 is Market Cap / Total Liabilities for the original model and
    Book Equity / Total Liabilities for Z'' (see ZScoreResult.x4_basis).
    """
    x1_working_capital_to_total_assets: float = Field(..., description="Working Capital / Total Assets")
    x2_retained_earnings_to_total_assets: float = Field(..., description="Retained Earnings / Total Assets")
    x3_ebit_to_total_assets: float = Field(..., description="EBIT / Total Assets")
    x4_market_cap_to_total_liabilities: float = Field(..., description="Equity (market or book) / Total Liabilities")
    x5_revenue_to_total_assets: float = Field(..., description="Revenue / Total Assets")


class ZScoreResult(BaseModel):
    """Result of an Altman Z-Score calculation."""
    ticker: str
    score: float = Field(..., description="Computed Altman Z-Score")
    zone: str = Field(..., description="Risk zone: Safe, Gray, or Distress")
    components: ZScoreComponents
    interpretation: str = Field(..., description="Human-readable risk assessment")
    model: Literal["original", "z_double_prime"] = Field("original", description="Altman model variant used")
    model_label: str = Field("Altman Z (1968)", description="Display name of the model")
    weights: dict[str, float] = Field(default_factory=dict, description="Coefficient per component (x1..x5)")
    safe_threshold: float = Field(2.99, description="Score above which the company is Safe")
    distress_threshold: float = Field(1.81, description="Score below which the company is in Distress")
    x4_basis: Literal["market", "book"] = Field("market", description="Equity measure used in X4")


class MonteCarloInput(BaseModel):
    """Input parameters for Monte Carlo simulation."""
    ticker: str = Field(..., description="Stock ticker symbol")
    num_simulations: int = Field(default=10_000, ge=100, le=100_000, description="Number of simulation paths")
    time_horizon_years: int = Field(default=3, ge=1, le=10, description="Forecast horizon in years")
    initial_revenue: Optional[float] = Field(None, description="Starting revenue (auto-fetched if omitted)")
    revenue_growth_mean: float = Field(default=0.05, description="Mean annual revenue growth rate")
    revenue_growth_std: float = Field(default=0.15, ge=0, description="Std dev of annual revenue growth rate")
    seed: Optional[int] = Field(None, description="RNG seed for reproducible runs (random if omitted)")
    parameter_source: Optional[str] = Field(None, description="Where the growth assumptions came from")


class MonteCarloResult(BaseModel):
    """Result of a Monte Carlo simulation with charting data."""
    ticker: str
    num_simulations: int
    time_horizon_years: int
    mean_final_revenue: Optional[float] = None
    median_final_revenue: Optional[float] = None
    percentile_5: Optional[float] = None
    percentile_95: Optional[float] = None
    probability_of_decline: Optional[float] = Field(None, description="P(revenue decline > 20%)")
    status: str = Field(default="active", description="Simulation status")
    # Charting data
    histogram: list[dict] = Field(default_factory=list, description="Revenue distribution bins [{range, count, pct}]")
    sample_paths: list[dict] = Field(default_factory=list, description="Sample revenue paths [{year, p5, p25, median, p75, p95, mean}]")
    initial_revenue: Optional[float] = None
    growth_mean: Optional[float] = Field(None, description="Annual log-growth drift used")
    growth_std: Optional[float] = Field(None, description="Annual volatility used")
    parameter_source: Optional[str] = Field(None, description="Where the growth assumptions came from")


# ──────────────────────────────────────────────
#  Forensic AI Analysis Models
# ──────────────────────────────────────────────

class ForensicRequest(BaseModel):
    """Input for the forensic audit pipeline."""
    ticker: str = Field(..., description="Stock ticker symbol", examples=["AAPL"])


class RedFlag(BaseModel):
    """An individual suspicious finding from linguistic analysis."""
    sentence: str = Field(..., description="The suspicious sentence or phrase")
    category: str = Field(..., description="Type: hedging, evasion, sentiment_gap, or inconsistency")
    severity: int = Field(..., ge=1, le=10, description="Severity rating 1-10")
    explanation: str = Field(..., description="AI-generated explanation of why this is suspicious")
    verified: Optional[bool] = Field(
        None, description="True if the quoted sentence was found verbatim in the filing text",
    )


class LinguisticAnalysis(BaseModel):
    """Linguistic metrics from the 10-K text analysis."""
    hedging_score: float = Field(..., ge=0, le=100, description="Hedging density score (0=none, 100=extreme)")
    evasion_score: float = Field(..., ge=0, le=100, description="Evasion language score")
    sentiment: str = Field(..., description="Overall MD&A sentiment: bullish, neutral, bearish, or unknown")
    sentiment_source: Optional[Literal["ai", "lexicon"]] = Field(
        None, description="Whether sentiment came from Gemini or the financial tone lexicon",
    )
    net_tone: Optional[float] = Field(
        None, ge=-1, le=1,
        description="Lexicon tone: (positive - negative) / (positive + negative) words",
    )
    sentiment_confidence: float = Field(..., ge=0, le=1, description="Confidence in sentiment classification")
    hedging_words_found: list[str] = Field(default_factory=list, description="List of hedging words detected")
    suspicious_sentences: list[RedFlag] = Field(default_factory=list, description="Flagged sentences with explanations")
    total_words_analyzed: int = Field(default=0, description="Total word count analyzed")


class TruthComponent(BaseModel):
    """One piece of evidence in the Truth Score (Credibility Index)."""
    key: Literal["financial_health", "filing_language", "call_candor", "narrative_consistency", "earnings_quality"]
    label: str
    score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1, description="Nominal weight before re-normalisation")
    effective_weight: float = Field(0.0, ge=0, le=1, description="Share of the final score after missing components are excluded")
    detail: str = Field(..., description="What drove this component's score")


class TruthScoreBreakdown(BaseModel):
    """How the Truth Score was built.

    `components` hold the weighted evidence. The penalty fields describe the
    filing-language component (100 minus these = its score).
    """
    components: list[TruthComponent] = Field(default_factory=list)
    hedging_penalty: float = 0.0
    evasion_penalty: float = 0.0
    red_flag_penalty: float = 0.0
    sentiment_gap_penalty: float = 0.0
    basis: Literal["ai+heuristic", "heuristic"] = Field(
        ..., description="Whether Gemini findings contributed, or rule-based analysis only",
    )


class ForensicResult(BaseModel):
    """Complete forensic analysis output merging AI insights with financial math."""
    truth_score: Optional[int] = Field(None, ge=0, le=100, description="Overall Truth Score (0=deceptive, 100=credible)")
    truth_zone: Optional[str] = Field(None, description="Zone: Credible, Suspicious, or Deceptive")
    linguistic_analysis: LinguisticAnalysis
    red_flags: list[RedFlag] = Field(default_factory=list, description="All detected red flags")
    deception_alert: bool = Field(default=False, description="True if sentiment diverges from financial reality")
    deception_reason: Optional[str] = Field(None, description="Explanation for deception alert")
    z_score_result: Optional[ZScoreResult] = Field(None, description="Merged Z-Score financial analysis")
    ai_confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Gemini confidence in its sentiment label (0-1). None if AI did not run.")
    truth_score_breakdown: Optional[TruthScoreBreakdown] = Field(None, description="How the Truth Score was derived")
    language_source: Optional[str] = Field(
        None, description="Text the language metrics came from (10-K MD&A, or the earnings press release as a fallback)",
    )
    analysis_note: Optional[str] = Field(None, description="Why parts of the analysis were skipped, if any")


# ──────────────────────────────────────────────
#  Earnings Call Models
# ──────────────────────────────────────────────

class CallSegmentMetrics(BaseModel):
    """Language metrics for one part of an earnings call."""
    words: int
    hedging_score: float = Field(..., ge=0, le=100)
    evasion_score: float = Field(..., ge=0, le=100)
    sentiment: str = Field(..., description="Lexicon sentiment: bullish, neutral, bearish or unknown")
    net_tone: Optional[float] = Field(None, ge=-1, le=1, description="(positive - negative) / (positive + negative)")
    provider_sentiment: Optional[float] = Field(None, description="Average sentiment supplied by the transcript provider")


class CallExchange(BaseModel):
    """One analyst question and management's answer."""
    analyst: str
    question: str
    respondents: list[str] = Field(default_factory=list)
    answer_excerpt: str
    answer_words: int
    deflection_phrase: Optional[str] = Field(None, description="Evasive phrase found in the answer, if any")
    brief: bool = Field(False, description="Answer shorter than 40 words")


class EarningsCallAnalysis(BaseModel):
    """Analysis of the latest earnings conference call (or earnings press release)."""
    available: bool
    source: Optional[Literal["alpha_vantage", "sec_8k"]] = None
    source_label: Optional[str] = None
    quarter: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    prepared: Optional[CallSegmentMetrics] = Field(None, description="Scripted remarks / press release commentary")
    qa: Optional[CallSegmentMetrics] = Field(None, description="Executives' answers during analyst Q&A")
    executives: list[str] = Field(default_factory=list)
    analyst_questions: int = 0
    deflection_rate: Optional[float] = Field(None, ge=0, le=1, description="Share of answers containing a deflection")
    tone_shift: Optional[float] = Field(None, description="Q&A tone minus prepared-remarks tone")
    candor_score: Optional[int] = Field(None, ge=0, le=100, description="Call Candor Score: 100 = open and consistent")
    flags: list[str] = Field(default_factory=list)
    exchanges: list[CallExchange] = Field(default_factory=list, description="Most notable Q&A exchanges")
    note: Optional[str] = Field(None, description="Why the call is unavailable or a fallback was used")


# ──────────────────────────────────────────────
#  Investment Conviction Models
# ──────────────────────────────────────────────

class ConvictionPillar(BaseModel):
    """One dimension of the investment case."""
    key: Literal["financial_strength", "profitability", "growth", "credibility", "valuation", "earnings_quality"]
    label: str
    score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    effective_weight: float = Field(0.0, ge=0, le=1)
    detail: str
    metric: Optional[str] = Field(None, description="Headline figure, e.g. 'Net margin 24.3%'")


class InvestmentConviction(BaseModel):
    """How convinced the platform is that this is a sound company to invest in (educational)."""
    score: Optional[int] = Field(None, ge=0, le=100, description="Conviction 0-100 (shown as a percentage)")
    verdict: Optional[Literal["High conviction", "Moderate conviction", "Neutral — watch", "Low conviction"]] = None
    headline: str
    pillars: list[ConvictionPillar] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    capped_reason: Optional[str] = Field(None, description="Why the score was capped, if it was")
    disclaimer: str = (
        "Educational analysis generated from public data by rule-based models. "
        "Not financial advice — do your own research before investing."
    )


class RiskItem(BaseModel):
    """One entry in the report's risk register."""
    severity: Literal["high", "medium", "low"]
    area: str = Field(..., description="Which analysis raised it, e.g. 'Earnings call'")
    finding: str


class ForensicAuditResponse(BaseModel):
    """Top-level response for the forensic audit endpoint."""
    ticker: str
    company_name: Optional[str] = None
    timestamp: str = Field(..., description="ISO 8601 timestamp of analysis")
    forensic: ForensicResult
    data_sources: list[str] = Field(default_factory=list, description="Data sources used")
    gemini_active: bool = Field(default=False, description="Whether Gemini AI actually produced this analysis")
    ai_error: Optional[str] = Field(None, description="Why Gemini did not contribute, if it did not")
    earnings_call: Optional[EarningsCallAnalysis] = Field(None, description="Latest earnings call analysis")
    conviction: Optional[InvestmentConviction] = Field(None, description="Investment conviction summary")
    financials: Optional[FinancialData] = Field(None, description="Financial statement data used, with history")
    monte_carlo: Optional[MonteCarloResult] = Field(None, description="Revenue stress test using the company's own growth history")
    risk_register: list[RiskItem] = Field(default_factory=list, description="Every warning raised, most severe first")
