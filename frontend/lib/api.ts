/**
 * Alpha-Guard — API Client
 * =========================
 * Centralized fetch wrapper for all backend API calls.
 * Set NEXT_PUBLIC_API_URL to point at a different backend (e.g. http://localhost:8000).
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://alpha-guard-backend.onrender.com";

// ── Types matching backend Pydantic models ──

export interface CompanyInfo {
    ticker: string;
    name: string | null;
    cik: string | null;
    sector: string | null;
}

export interface HistoryPoint {
    fiscal_period_end: string;
    revenue: number | null;
    net_income: number | null;
    operating_cash_flow: number | null;
    total_assets: number | null;
    total_liabilities: number | null;
}

export interface FinancialData {
    ticker: string;
    total_assets: number;
    /** null for banks/insurers, which have no current/non-current split */
    current_assets: number | null;
    current_liabilities: number | null;
    retained_earnings: number;
    ebit: number;
    market_cap: number | null;
    total_liabilities: number;
    revenue: number;
    sic_code?: number | null;
    sector?: string | null;
    fiscal_period_end?: string | null;
    z_model?: "auto" | "original" | "z_double_prime";
    net_income?: number | null;
    operating_cash_flow?: number | null;
    revenue_prior_year?: number | null;
    /** Up to 5 fiscal years, newest first */
    history?: HistoryPoint[];
}

export interface ZScoreComponents {
    x1_working_capital_to_total_assets: number;
    x2_retained_earnings_to_total_assets: number;
    x3_ebit_to_total_assets: number;
    x4_market_cap_to_total_liabilities: number;
    x5_revenue_to_total_assets: number;
}

export interface ZScoreResult {
    ticker: string;
    score: number;
    zone: "Safe" | "Gray" | "Distress";
    components: ZScoreComponents;
    interpretation: string;
    model: "original" | "z_double_prime";
    model_label: string;
    weights: Record<"x1" | "x2" | "x3" | "x4" | "x5", number>;
    safe_threshold: number;
    distress_threshold: number;
    x4_basis: "market" | "book";
}

export interface ZScoreComponentRow {
    key: "x1" | "x2" | "x3" | "x4" | "x5";
    label: string;
    value: number;
    weight: number;
}

/** Component rows for the model actually used; components with zero weight are omitted. */
export function zScoreComponentRows(z: ZScoreResult): ZScoreComponentRow[] {
    const c = z.components;
    const w = z.weights ?? { x1: 1.2, x2: 1.4, x3: 3.3, x4: 0.6, x5: 1.0 };
    const rows: ZScoreComponentRow[] = [
        { key: "x1", label: "X1 — Working Capital / Total Assets", value: c.x1_working_capital_to_total_assets, weight: w.x1 },
        { key: "x2", label: "X2 — Retained Earnings / Total Assets", value: c.x2_retained_earnings_to_total_assets, weight: w.x2 },
        { key: "x3", label: "X3 — EBIT / Total Assets", value: c.x3_ebit_to_total_assets, weight: w.x3 },
        {
            key: "x4",
            label: z.x4_basis === "book" ? "X4 — Book Equity / Total Liabilities" : "X4 — Market Cap / Total Liabilities",
            value: c.x4_market_cap_to_total_liabilities,
            weight: w.x4,
        },
        { key: "x5", label: "X5 — Revenue / Total Assets", value: c.x5_revenue_to_total_assets, weight: w.x5 },
    ];
    return rows.filter((r) => r.weight !== 0);
}

export interface RedFlag {
    sentence: string;
    category: string;
    severity: number;
    explanation: string;
    verified?: boolean | null;
}

export interface LinguisticAnalysis {
    hedging_score: number;
    evasion_score: number;
    sentiment: string;
    sentiment_confidence: number;
    sentiment_source?: "ai" | "lexicon" | null;
    net_tone?: number | null;
    hedging_words_found: string[];
    suspicious_sentences: RedFlag[];
    total_words_analyzed: number;
}

export interface TruthComponent {
    key: "financial_health" | "filing_language" | "call_candor" | "narrative_consistency" | "earnings_quality";
    label: string;
    score: number;
    /** Nominal weight */
    weight: number;
    /** Share of the final score after missing components are excluded */
    effective_weight: number;
    detail: string;
}

export interface TruthScoreBreakdown {
    components: TruthComponent[];
    hedging_penalty: number;
    evasion_penalty: number;
    red_flag_penalty: number;
    sentiment_gap_penalty: number;
    basis: "ai+heuristic" | "heuristic";
}

export interface ForensicResult {
    /** null when there was not enough filing text to judge */
    truth_score: number | null;
    truth_zone: string | null;
    linguistic_analysis: LinguisticAnalysis;
    red_flags: RedFlag[];
    deception_alert: boolean;
    deception_reason: string | null;
    z_score_result: ZScoreResult | null;
    ai_confidence_score: number | null;
    truth_score_breakdown: TruthScoreBreakdown | null;
    analysis_note: string | null;
}

export interface CallSegmentMetrics {
    words: number;
    hedging_score: number;
    evasion_score: number;
    sentiment: string;
    net_tone: number | null;
    provider_sentiment: number | null;
}

export interface CallExchange {
    analyst: string;
    question: string;
    respondents: string[];
    answer_excerpt: string;
    answer_words: number;
    deflection_phrase: string | null;
    brief: boolean;
}

export interface EarningsCallAnalysis {
    available: boolean;
    source: "alpha_vantage" | "sec_8k" | null;
    source_label: string | null;
    quarter: string | null;
    date: string | null;
    url: string | null;
    /** Scripted remarks, or the press release's commentary */
    prepared: CallSegmentMetrics | null;
    /** Executives' answers during analyst Q&A (transcripts only) */
    qa: CallSegmentMetrics | null;
    executives: string[];
    analyst_questions: number;
    deflection_rate: number | null;
    tone_shift: number | null;
    /** 0-100; null for press releases (no Q&A to measure) */
    candor_score: number | null;
    flags: string[];
    exchanges: CallExchange[];
    note: string | null;
}

export interface RiskItem {
    severity: "high" | "medium" | "low";
    area: string;
    finding: string;
}

export interface ConvictionPillar {
    key: "financial_strength" | "profitability" | "growth" | "credibility" | "valuation" | "earnings_quality";
    label: string;
    score: number;
    weight: number;
    effective_weight: number;
    detail: string;
    metric: string | null;
}

export interface InvestmentConviction {
    /** 0-100, shown as a percentage; null when there is too little data */
    score: number | null;
    verdict: "High conviction" | "Moderate conviction" | "Neutral — watch" | "Low conviction" | null;
    headline: string;
    pillars: ConvictionPillar[];
    strengths: string[];
    concerns: string[];
    capped_reason: string | null;
    disclaimer: string;
}

export interface ForensicAuditResponse {
    ticker: string;
    company_name: string | null;
    timestamp: string;
    forensic: ForensicResult;
    data_sources: string[];
    gemini_active: boolean;
    ai_error: string | null;
    earnings_call?: EarningsCallAnalysis | null;
    conviction?: InvestmentConviction | null;
    financials?: FinancialData | null;
    monte_carlo?: MonteCarloResult | null;
    risk_register?: RiskItem[];
}

export interface HealthCheck {
    status: string;
    platform: string;
    version: string;
    modules: string[];
}

// ── API Error ──

export class ApiError extends Error {
    status: number;
    detail: string;

    constructor(status: number, detail: string) {
        super(detail);
        this.status = status;
        this.detail = detail;
    }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new ApiError(
                res.status,
                body.detail || `API error: ${res.status} ${res.statusText}`
            );
        }

        return res.json();
    } catch (err) {
        if (err instanceof ApiError) throw err;
        throw new ApiError(0, `Network error: Unable to reach backend at ${API_BASE}. Check CORS or if the server is down.`);
    }
}

// ── Endpoints ──

export async function healthCheck(): Promise<HealthCheck> {
    return apiFetch<HealthCheck>("/");
}

export async function fetchCompanyInfo(ticker: string): Promise<CompanyInfo> {
    return apiFetch<CompanyInfo>(`/api/data/company/${encodeURIComponent(ticker)}`);
}

export async function fetchFinancials(ticker: string): Promise<FinancialData> {
    return apiFetch<FinancialData>(`/api/data/financials/${encodeURIComponent(ticker)}`);
}

export async function calculateZScore(data: FinancialData): Promise<ZScoreResult> {
    return apiFetch<ZScoreResult>("/api/risk/z-score", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function runForensicAudit(ticker: string): Promise<ForensicAuditResponse> {
    return apiFetch<ForensicAuditResponse>("/api/risk/forensic-audit", {
        method: "POST",
        body: JSON.stringify({ ticker }),
    });
}

// ── Monte Carlo ──

export interface MonteCarloInput {
    ticker: string;
    num_simulations?: number;
    time_horizon_years?: number;
    initial_revenue?: number;
    revenue_growth_mean?: number;
    revenue_growth_std?: number;
    seed?: number;
}

export interface MonteCarloResult {
    ticker: string;
    num_simulations: number;
    time_horizon_years: number;
    mean_final_revenue: number | null;
    median_final_revenue: number | null;
    percentile_5: number | null;
    percentile_95: number | null;
    probability_of_decline: number | null;
    status: string;
    initial_revenue: number | null;
    histogram: { range: string; count: number; pct: number; midpoint: number }[];
    sample_paths: { year: number; p5: number; p25: number; median: number; p75: number; p95: number; mean: number }[];
    growth_mean?: number | null;
    growth_std?: number | null;
    parameter_source?: string | null;
}

export async function runMonteCarlo(params: MonteCarloInput): Promise<MonteCarloResult> {
    return apiFetch<MonteCarloResult>("/api/risk/monte-carlo", {
        method: "POST",
        body: JSON.stringify(params),
    });
}

// ── Config Status ──

export interface ConfigStatus {
    gemini_configured: boolean;
    gemini_model?: string;
    rate_limit_per_minute?: number;
}

export async function checkConfigStatus(): Promise<ConfigStatus> {
    return apiFetch<ConfigStatus>("/api/config/status");
}
