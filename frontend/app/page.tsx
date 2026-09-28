"use client";

import { useState, useCallback, useEffect } from "react";
import DashboardHeader from "@/components/DashboardHeader";
import TickerSearch from "@/components/TickerSearch";
import RiskOverview, { type RiskOverviewData } from "@/components/RiskOverview";
import MetricCard from "@/components/MetricCard";
import MonteCarloChart from "@/components/MonteCarloChart";
import ApiKeyBanner from "@/components/ApiKeyBanner";
import { AnimatedSection, FadeTransition } from "@/components/AnimatedSection";
import {
  fetchFinancials,
  calculateZScore,
  fetchCompanyInfo,
  runMonteCarlo,
  checkConfigStatus,
  zScoreComponentRows,
  type ZScoreResult,
  type MonteCarloResult,
} from "@/lib/api";

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zScore, setZScore] = useState<ZScoreResult | null>(null);
  const [riskData, setRiskData] = useState<RiskOverviewData | null>(null);
  const [searchedTicker, setSearchedTicker] = useState("");
  const [monteCarloData, setMonteCarloData] = useState<MonteCarloResult | null>(null);
  const [mcLoading, setMcLoading] = useState(false);
  const [lastRevenue, setLastRevenue] = useState<number | null>(null);
  const [geminiMissing, setGeminiMissing] = useState(false);

  useEffect(() => {
    checkConfigStatus()
      .then((status) => setGeminiMissing(!status.gemini_configured))
      .catch(() => {});
  }, []);

  const handleSearch = useCallback(async (ticker: string) => {
    setIsLoading(true);
    setError(null);
    setSearchedTicker(ticker);
    setMonteCarloData(null);

    try {
      const financials = await fetchFinancials(ticker);
      setLastRevenue(financials.revenue);

      const result = await calculateZScore(financials);
      setZScore(result);

      let companyName = ticker;
      try {
        const info = await fetchCompanyInfo(ticker);
        companyName = info.name || ticker;
      } catch { /* optional */ }

      setRiskData({
        ticker: result.ticker,
        companyName,
        score: result.score,
        zone: result.zone,
        components: zScoreComponentRows(result),
        modelLabel: result.model_label,
        safeThreshold: result.safe_threshold,
        distressThreshold: result.distress_threshold,
        source: financials.fiscal_period_end
          ? `${financials.sector ? "Yahoo Finance" : "SEC EDGAR 10-K"} · FY ending ${financials.fiscal_period_end}`
          : undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      setZScore(null);
      setRiskData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleStressTest = useCallback(async () => {
    if (!searchedTicker) return;
    setMcLoading(true);
    try {
      const result = await runMonteCarlo({
        ticker: searchedTicker,
        num_simulations: 1000,
        time_horizon_years: 5,
        initial_revenue: lastRevenue || undefined,
      });
      setMonteCarloData(result);
    } catch { /* non-critical */ }
    finally { setMcLoading(false); }
  }, [searchedTicker, lastRevenue]);

  const trendFor = (val: number): "up" | "down" | "neutral" => {
    if (val > 0.1) return "up";
    if (val < -0.05) return "down";
    return "neutral";
  };

  const colorFor = (val: number): "green" | "amber" | "red" | "blue" => {
    if (val > 0.3) return "green";
    if (val > 0.1) return "blue";   // was "cyan", now remapped to "blue"
    if (val > 0) return "amber";
    return "red";
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
      <DashboardHeader />
      <ApiKeyBanner show={geminiMissing} />

      <main style={{ flex: 1, width: "100%", maxWidth: 1480, margin: "0 auto", padding: "40px 24px" }}>

        {/* ── Hero / Search ── */}
        <AnimatedSection className="mb-12">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }} className="text-center">

            {/* Eyebrow */}
            <p style={{
              fontFamily: "var(--font-ibm-plex-mono, monospace)",
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--green)",
              marginBottom: 12,
            }}>
              Forensic Credit Research
            </p>

            {/* Serif headline */}
            <h2 style={{
              fontFamily: "var(--font-source-serif, Georgia, serif)",
              fontSize: "clamp(28px, 4vw, 44px)",
              fontWeight: 700,
              color: "var(--ink)",
              lineHeight: 1.15,
              letterSpacing: "-0.02em",
              marginBottom: 12,
            }}>
              Credit Risk{" "}
              <span style={{ color: "var(--green)" }}>Intelligence</span>
            </h2>

            {/* Sans subhead */}
            <p style={{
              fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
              fontSize: 14,
              color: "var(--ink-2)",
              maxWidth: 480,
              lineHeight: 1.6,
              marginBottom: 32,
            }}>
              Institutional-grade financial forensics powered by Altman Z-Score
              analysis, Monte Carlo simulation, and global market data.
            </p>

            {/* Case meta box */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 0,
              marginBottom: 28,
              background: "var(--paper-2)",
              border: "1px solid var(--rule)",
              borderRadius: 4,
              overflow: "hidden",
            }}>
              {[
                { label: "Platform", value: "Alpha-Guard v0.4" },
                { label: "Coverage", value: "SEC EDGAR · NYSE · BSE" },
                { label: "Model", value: "Altman Z / Z'' (auto)" },
              ].map((item, i) => (
                <div
                  key={i}
                  style={{
                    padding: "8px 16px",
                    borderRight: i < 2 ? "1px solid var(--rule)" : "none",
                    textAlign: "center",
                  }}
                >
                  <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 2 }}>{item.label}</p>
                  <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, color: "var(--ink)" }}>{item.value}</p>
                </div>
              ))}
            </div>

            <TickerSearch onSearch={handleSearch} isLoading={isLoading} />
          </div>
        </AnimatedSection>

        {/* ── Error ── */}
        {error && (
          <AnimatedSection className="mb-6">
            <div style={{
              background: "var(--red-tint)",
              borderLeft: "4px solid var(--red)",
              borderRadius: "0 4px 4px 0",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}>
              <svg style={{ width: 14, height: 14, color: "var(--red)", flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 13, color: "var(--ink-2)" }}>{error}</p>
            </div>
          </AnimatedSection>
        )}

        {/* ── Z-Score Metric Cards — connected border grid ── */}
        <FadeTransition transitionKey={`metrics-${searchedTicker}`}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 1, background: "var(--rule)", border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden", marginBottom: 24 }} className="grid-cols-2 md:grid-cols-4">
            <MetricCard
              label="Working Capital"
              value={zScore ? zScore.components.x1_working_capital_to_total_assets.toFixed(4) : "—.——"}
              subtitle="X1 · Current Assets − Liabilities"
              trend={zScore ? trendFor(zScore.components.x1_working_capital_to_total_assets) : "neutral"}
              accentColor={zScore ? colorFor(zScore.components.x1_working_capital_to_total_assets) : "green"}
            />
            <MetricCard
              label="Profitability"
              value={zScore ? zScore.components.x2_retained_earnings_to_total_assets.toFixed(4) : "—.——"}
              subtitle="X2 · Retained Earnings / Assets"
              trend={zScore ? trendFor(zScore.components.x2_retained_earnings_to_total_assets) : "neutral"}
              accentColor={zScore ? colorFor(zScore.components.x2_retained_earnings_to_total_assets) : "blue"}
            />
            <MetricCard
              label="Operating Efficiency"
              value={zScore ? zScore.components.x3_ebit_to_total_assets.toFixed(4) : "—.——"}
              subtitle="X3 · EBIT / Total Assets"
              trend={zScore ? trendFor(zScore.components.x3_ebit_to_total_assets) : "neutral"}
              accentColor={zScore ? colorFor(zScore.components.x3_ebit_to_total_assets) : "amber"}
            />
            <MetricCard
              label={zScore?.x4_basis === "book" ? "Book Leverage" : "Market Leverage"}
              value={zScore ? zScore.components.x4_market_cap_to_total_liabilities.toFixed(4) : "—.——"}
              subtitle={zScore?.x4_basis === "book" ? "X4 · Book Equity / Liabilities" : "X4 · Market Cap / Liabilities"}
              trend={zScore ? trendFor(zScore.components.x4_market_cap_to_total_liabilities) : "neutral"}
              accentColor={zScore ? colorFor(zScore.components.x4_market_cap_to_total_liabilities) : "green"}
            />
          </div>
        </FadeTransition>

        {/* ── Risk Overview ── */}
        <AnimatedSection delay={0.2} className="mb-8">
          <FadeTransition transitionKey={`risk-${searchedTicker}`}>
            <RiskOverview data={riskData} />
          </FadeTransition>
        </AnimatedSection>

        {/* ── Monte Carlo Section ── */}
        <AnimatedSection delay={0.3} className="mb-8">
          <div style={{
            background: "var(--paper-2)",
            border: "1px solid var(--rule)",
            borderRadius: 4,
            padding: 24,
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 4,
                  background: "var(--paper)", border: "1px solid var(--rule)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <svg style={{ width: 13, height: 13, color: "var(--ink-faint)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 20V10" />
                    <path d="M18 20V4" />
                    <path d="M6 20v-4" />
                  </svg>
                </div>
                <div>
                  <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 15, fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                    Monte Carlo Simulation
                  </h3>
                  <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", margin: 0 }}>
                    Revenue Stress Testing · 1,000 Paths
                  </p>
                </div>
              </div>

              {searchedTicker && (
                <button
                  id="run-stress-test-btn"
                  onClick={handleStressTest}
                  disabled={mcLoading}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "7px 16px",
                    borderRadius: 4,
                    background: mcLoading ? "var(--paper)" : "var(--green)",
                    color: mcLoading ? "var(--ink-2)" : "#ffffff",
                    border: `1px solid ${mcLoading ? "var(--rule-strong)" : "var(--green)"}`,
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    cursor: mcLoading ? "not-allowed" : "pointer",
                    opacity: mcLoading ? 0.7 : 1,
                    transition: "all 0.15s ease",
                  }}
                >
                  {mcLoading ? (
                    <>
                      <div style={{ width: 10, height: 10, border: "2px solid var(--rule)", borderTopColor: "var(--green)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                      Running...
                    </>
                  ) : (
                    <>
                      <svg style={{ width: 10, height: 10 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      Run Stress Test
                    </>
                  )}
                </button>
              )}
            </div>

            {monteCarloData ? (
              <MonteCarloChart data={monteCarloData} />
            ) : (
              <div style={{
                height: 120,
                borderRadius: 4,
                background: "var(--paper)",
                border: "1px dashed var(--rule-strong)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}>
                <div style={{ textAlign: "center" }}>
                  <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 11, color: "var(--ink-faint)" }}>
                    {searchedTicker
                      ? `${searchedTicker} ready — click "Run Stress Test" above`
                      : "Simulation Engine Ready"}
                  </p>
                  <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 4, opacity: 0.6 }}>
                    {searchedTicker
                      ? "1,000 GBM revenue paths will be generated"
                      : "Search a ticker first to enable stress testing"}
                  </p>
                </div>
              </div>
            )}
          </div>
        </AnimatedSection>

        {/* ── Data Sources Panel ── */}
        <AnimatedSection delay={0.4} className="mb-8">
          <div style={{
            background: "var(--paper-2)",
            border: "1px solid var(--rule)",
            borderRadius: 4,
            overflow: "hidden",
          }}>
            {/* Panel header */}
            <div style={{
              padding: "14px 20px",
              borderBottom: "1px solid var(--rule)",
              background: "var(--paper)",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}>
              <div style={{ width: 28, height: 28, borderRadius: 4, background: "var(--paper-2)", border: "1px solid var(--rule)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg style={{ width: 13, height: 13, color: "var(--ink-faint)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
              </div>
              <div>
                <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: 0 }}>Data Sources</h3>
                <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", margin: 0 }}>Ingestion Pipeline</p>
              </div>
            </div>

            {/* Flat rows with hairline dividers */}
            {[
              { name: "SEC EDGAR",   status: "Connected",        detail: "10-K XBRL · www.sec.gov",                      active: true,                                    type: "green" },
              { name: "Yahoo Finance", status: "Connected",      detail: "yfinance · Global Markets (BSE/NSE/LSE)",       active: true,                                    type: "green" },
              { name: "Gemini AI",   status: geminiMissing ? "Not Configured" : (searchedTicker ? "Active" : "Idle"), detail: "Forensic Linguistic Analysis", active: !geminiMissing && !!searchedTicker, type: "blue" },
              { name: "Monte Carlo", status: monteCarloData ? "Active" : "Idle", detail: "GBM Revenue Simulation · 1K Paths", active: !!monteCarloData,               type: "blue" },
            ].map((source, i, arr) => (
              <div
                key={source.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "11px 20px",
                  borderBottom: i < arr.length - 1 ? "1px solid var(--rule)" : "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: source.active
                      ? (source.type === "blue" ? "var(--blue)" : "var(--green)")
                      : "var(--rule-strong)",
                    flexShrink: 0,
                  }} />
                  <div>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 11, fontWeight: 600, color: "var(--ink)", margin: 0 }}>{source.name}</p>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", margin: 0 }}>{source.detail}</p>
                  </div>
                </div>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 3,
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 9,
                    fontWeight: 600,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    background: source.active
                      ? (source.type === "blue" ? "var(--blue-tint)" : "var(--green-tint)")
                      : "var(--paper)",
                    color: source.active
                      ? (source.type === "blue" ? "var(--blue)" : "var(--green)")
                      : "var(--ink-faint)",
                    border: `1px solid ${source.active
                      ? (source.type === "blue" ? "var(--blue-tint)" : "var(--green-tint)")
                      : "var(--rule)"}`,
                  }}
                >
                  {source.status}
                </span>
              </div>
            ))}
          </div>
        </AnimatedSection>
      </main>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid var(--rule)", padding: "14px 24px" }}>
        <div style={{ maxWidth: 1480, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
            ALPHA-GUARD v0.3.0 · Forensic Credit Risk Platform
          </p>
          <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
            FastAPI · Next.js · SEC EDGAR · Yahoo Finance · Google Gemini
          </p>
        </div>
      </footer>
    </div>
  );
}
