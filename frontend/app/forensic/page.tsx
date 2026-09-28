"use client";

import { useState, useCallback, useEffect } from "react";
import DashboardHeader from "@/components/DashboardHeader";
import TickerSearch from "@/components/TickerSearch";
import TruthScoreGauge from "@/components/TruthScoreGauge";
import RiskRadar from "@/components/RiskRadar";
import RedFlagTerminal from "@/components/RedFlagTerminal";
import ApiKeyBanner from "@/components/ApiKeyBanner";
import { AnimatedSection, FadeTransition } from "@/components/AnimatedSection";
import { runForensicAudit, checkConfigStatus, type ForensicAuditResponse, type RedFlag } from "@/lib/api";

export default function ForensicPage() {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [auditResult, setAuditResult] = useState<ForensicAuditResponse | null>(null);
    const [ticker, setTicker] = useState("");
    const [geminiMissing, setGeminiMissing] = useState(false);

    useEffect(() => {
        checkConfigStatus()
            .then((status) => setGeminiMissing(!status.gemini_configured))
            .catch(() => {});
    }, []);

    useEffect(() => {
        if (auditResult) {
            window.dispatchEvent(
                new CustomEvent("alpha-guard:flags", {
                    detail: { flagCount: auditResult.forensic.red_flags.length },
                })
            );
        }
    }, [auditResult]);

    const handleSearch = useCallback(async (searchTicker: string) => {
        setIsLoading(true);
        setError(null);
        setTicker(searchTicker);
        setAuditResult(null);

        try {
            const result = await runForensicAudit(searchTicker);
            setAuditResult(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Forensic audit failed.");
            setAuditResult(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const f = auditResult?.forensic;
    const la = f?.linguistic_analysis;
    const zc = f?.z_score_result?.components;

    const radarData = f && zc
        ? [
            { label: "Liquidity (X1)", financial: Math.max(0, Math.min(100, (zc.x1_working_capital_to_total_assets + 0.5) * 100)), narrative: 100 - (la?.hedging_score ?? 50) },
            { label: "Profitability (X2)", financial: Math.max(0, Math.min(100, (zc.x2_retained_earnings_to_total_assets + 0.5) * 100)), narrative: 100 - (la?.evasion_score ?? 50) },
            { label: "Efficiency (X3)", financial: Math.max(0, Math.min(100, zc.x3_ebit_to_total_assets * 100)), narrative: la?.sentiment === "bullish" ? 90 : la?.sentiment === "bearish" ? 20 : 50 },
            { label: "Leverage (X4)", financial: Math.max(0, Math.min(100, zc.x4_market_cap_to_total_liabilities * 20)), narrative: f.truth_score ?? 50 },
        ]
        : undefined;

    const redFlags: RedFlag[] = f?.red_flags ?? [];

    const metrics = [
        {
            label: "Hedging Score",
            value: la ? la.hedging_score.toFixed(1) : "—",
            color: la && la.hedging_score > 50 ? "var(--red)" : la && la.hedging_score > 25 ? "var(--amber)" : "var(--green)",
        },
        {
            label: "Evasion Score",
            value: la ? la.evasion_score.toFixed(1) : "—",
            color: la && la.evasion_score > 50 ? "var(--red)" : la && la.evasion_score > 25 ? "var(--amber)" : "var(--green)",
        },
        {
            label: la?.sentiment_source === "lexicon" ? "Sentiment (Lexicon)" : la?.sentiment_source === "ai" ? "Sentiment (AI)" : "Sentiment",
            value: la ? la.sentiment.toUpperCase() : "—",
            color: la?.sentiment === "bullish" ? "var(--green)" : la?.sentiment === "bearish" ? "var(--red)" : "var(--amber)",
        },
        {
            label: "Z-Score Zone",
            value: f?.z_score_result?.zone.toUpperCase() ?? "—",
            color: f?.z_score_result?.zone === "Safe" ? "var(--green)" : f?.z_score_result?.zone === "Distress" ? "var(--red)" : "var(--amber)",
        },
    ];

    return (
        <div style={{ minHeight: "100vh", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
            <DashboardHeader />
            <ApiKeyBanner show={geminiMissing} />

            <main style={{ flex: 1, width: "100%", maxWidth: 1480, margin: "0 auto", padding: "40px 24px" }}>

                {/* ── Hero / Search ── */}
                <AnimatedSection className="text-center mb-12">
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 500, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--green)", marginBottom: 12 }}>
                        Linguistic Intelligence
                    </p>
                    <h2 style={{
                        fontFamily: "var(--font-source-serif, Georgia, serif)",
                        fontSize: "clamp(26px, 4vw, 42px)",
                        fontWeight: 700,
                        color: "var(--ink)",
                        lineHeight: 1.15,
                        letterSpacing: "-0.02em",
                        marginBottom: 12,
                    }}>
                        Linguistic{" "}
                        <span style={{ color: "var(--green)" }}>Stress Analysis</span>
                    </h2>
                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 14, color: "var(--ink-2)", maxWidth: 520, margin: "0 auto 32px" }}>
                        Gemini-powered forensic intelligence that reads between the lines of
                        10-K filings — detecting hedging, evasion, and narrative deception.
                    </p>
                    <TickerSearch onSearch={handleSearch} isLoading={isLoading} />
                </AnimatedSection>

                {/* ── Error ── */}
                {error && (
                    <AnimatedSection className="mb-6">
                        <div style={{ background: "var(--red-tint)", borderLeft: "4px solid var(--red)", borderRadius: "0 4px 4px 0", padding: "12px 16px" }}>
                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--red)", marginBottom: 3 }}>Analysis Error</p>
                            <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 13, color: "var(--ink-2)" }}>{error}</p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── AI Offline ── */}
                {auditResult && !auditResult.gemini_active && auditResult.truth_score_mode !== "demo" && !isLoading && (
                    <AnimatedSection className="mb-6">
                        <div style={{ background: "var(--amber-tint)", borderLeft: "4px solid var(--amber)", borderRadius: "0 4px 4px 0", padding: "12px 16px" }}>
                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--amber)", marginBottom: 3 }}>AI Analyst Offline</p>
                            <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 13, color: "var(--ink-2)" }}>
                                {auditResult.ai_error ?? "Reverting to heuristic models."}
                            </p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── Loading ── */}
                {isLoading && (
                    <AnimatedSection className="mb-10">
                        <div style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: 40, textAlign: "center" }}>
                            <div style={{
                                width: 24, height: 24, border: "2px solid var(--rule)", borderTopColor: "var(--green)",
                                borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px",
                            }} />
                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-2)" }}>
                                Running forensic analysis on {ticker}...
                            </p>
                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 6 }}>
                                Fetching 10-K filing · Computing Z-Score · Analyzing narrative
                            </p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── Results ── */}
                {f && !isLoading && (
                    <FadeTransition transitionKey={`forensic-${ticker}`}>
                        <div>
                            {/* Company header */}
                            {auditResult?.company_name && (
                                <AnimatedSection className="mb-6">
                                    <div style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 12,
                                        padding: "10px 0",
                                        borderBottom: "1px solid var(--rule)",
                                    }}>
                                        <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 16, fontWeight: 700, color: "var(--ink)" }}>
                                            {auditResult.ticker}
                                        </span>
                                        <span style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 13, color: "var(--ink-2)" }}>
                                            {auditResult.company_name}
                                        </span>
                                        <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginLeft: "auto" }}>
                                            {new Date(auditResult.timestamp).toLocaleString()}
                                        </span>
                                    </div>
                                </AnimatedSection>
                            )}

                            {/* Truth Score + Risk Radar */}
                            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                                <AnimatedSection delay={0.05} className="lg:col-span-1">
                                    <TruthScoreGauge
                                        score={f.truth_score}
                                        zone={f.truth_zone}
                                        deceptionAlert={f.deception_alert}
                                        deceptionReason={f.deception_reason ?? undefined}
                                        aiConfidenceScore={f.ai_confidence_score}
                                        isDemo={auditResult?.truth_score_mode === "demo"}
                                    />
                                    {(f.truth_score_breakdown || f.analysis_note) && (
                                        <div style={{ marginTop: 8, padding: "10px 14px", background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4 }}>
                                            {f.truth_score_breakdown && f.truth_score_breakdown.basis !== "demo" && (
                                                <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, color: "var(--ink-2)", lineHeight: 1.6 }}>
                                                    100 − hedging {f.truth_score_breakdown.hedging_penalty}
                                                    {" "}− evasion {f.truth_score_breakdown.evasion_penalty}
                                                    {" "}− red flags {f.truth_score_breakdown.red_flag_penalty}
                                                    {" "}− sentiment gap {f.truth_score_breakdown.sentiment_gap_penalty}
                                                    <br />
                                                    <span style={{ color: "var(--ink-faint)" }}>
                                                        Basis: {f.truth_score_breakdown.basis === "heuristic" ? "lexicon heuristics only" : "Gemini + lexicon heuristics"}
                                                        {la?.net_tone != null && ` · Net tone ${la.net_tone > 0 ? "+" : ""}${la.net_tone.toFixed(2)}`}
                                                    </span>
                                                </p>
                                            )}
                                            {f.analysis_note && (
                                                <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 11, color: "var(--ink-faint)", marginTop: f.truth_score_breakdown ? 6 : 0 }}>
                                                    {f.analysis_note}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </AnimatedSection>
                                <AnimatedSection delay={0.1} className="lg:col-span-2">
                                    <RiskRadar data={radarData} />
                                </AnimatedSection>
                            </section>

                            {/* Forensic Metrics Row — connected border grid */}
                            <section style={{ marginBottom: 24 }}>
                                <div style={{
                                    display: "grid",
                                    gridTemplateColumns: "repeat(4,1fr)",
                                    border: "1px solid var(--rule)",
                                    borderRadius: 4,
                                    overflow: "hidden",
                                }}
                                    className="grid-cols-2 sm:grid-cols-4"
                                >
                                    {metrics.map((metric, i) => (
                                        <div
                                            key={metric.label}
                                            style={{
                                                padding: "16px 20px",
                                                textAlign: "center",
                                                background: "var(--paper-2)",
                                                borderRight: i < metrics.length - 1 ? "1px solid var(--rule)" : "none",
                                            }}
                                        >
                                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 6 }}>
                                                {metric.label}
                                            </p>
                                            <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 22, fontWeight: 600, color: metric.color }}>
                                                {metric.value}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Red Flag Evidence Log */}
                            <AnimatedSection delay={0.3} className="mb-8">
                                <RedFlagTerminal flags={redFlags.length > 0 ? redFlags : undefined} />
                            </AnimatedSection>

                            {/* Data Sources */}
                            {auditResult?.data_sources && auditResult.data_sources.length > 0 && (
                                <AnimatedSection delay={0.4} className="mb-8">
                                    <div style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: "14px 20px" }}>
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 10 }}>
                                            Data Sources
                                        </p>
                                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                                            {auditResult.data_sources.map((src, i) => (
                                                <span
                                                    key={i}
                                                    style={{
                                                        padding: "3px 10px",
                                                        borderRadius: 3,
                                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                        fontSize: 10,
                                                        color: "var(--ink-2)",
                                                        background: "var(--paper)",
                                                        border: "1px solid var(--rule)",
                                                    }}
                                                >
                                                    {src}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </AnimatedSection>
                            )}
                        </div>
                    </FadeTransition>
                )}

                {/* ── Methodology — always visible ── */}
                {!isLoading && (
                    <AnimatedSection delay={0.1} className="mb-8">
                        <section style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden" }}>
                            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--rule)", background: "var(--paper)" }}>
                                <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                                    <svg style={{ width: 14, height: 14, color: "var(--ink-faint)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                                        <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
                                    </svg>
                                    Analysis Methodology
                                </h3>
                            </div>
                            <div style={{ padding: 20, display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }} className="grid-cols-1 md:grid-cols-3">
                                {[
                                    { title: "Hedging Detection", desc: "Scans Item 1A for hedging words like 'uncertain,' 'might,' 'potentially.' Computes density score normalized against filing length." },
                                    { title: "Sentiment Gap Analysis", desc: "Compares Gemini AI's sentiment classification of MD&A narrative against the quantitative Z-Score zone. Divergence triggers Deception Alert." },
                                    { title: "Truth Score Formula", desc: "100 − hedging_penalty(25%) − evasion_penalty(15%) − sentiment_gap(40%) − red_flag_penalty(20%). Score ≥70 = Credible, <40 = Deceptive." },
                                ].map((method) => (
                                    <div
                                        key={method.title}
                                        style={{ padding: "14px 16px", borderRadius: 4, background: "var(--paper)", border: "1px solid var(--rule)" }}
                                    >
                                        <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 6 }}>
                                            {method.title}
                                        </p>
                                        <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 11, color: "var(--ink-2)", lineHeight: 1.55 }}>
                                            {method.desc}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </AnimatedSection>
                )}
            </main>

            <footer style={{ borderTop: "1px solid var(--rule)", padding: "14px 24px" }}>
                <div style={{ maxWidth: 1480, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>ALPHA-GUARD v0.3.0 · Forensic AI Intelligence Layer</p>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>Powered by Google Gemini · FastAPI · SEC EDGAR · Yahoo Finance</p>
                </div>
            </footer>
        </div>
    );
}
