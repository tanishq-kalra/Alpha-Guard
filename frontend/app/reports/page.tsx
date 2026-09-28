"use client";

import { useState, useCallback, useRef } from "react";
import DashboardHeader from "@/components/DashboardHeader";
import TickerSearch from "@/components/TickerSearch";
import { AnimatedSection, FadeTransition } from "@/components/AnimatedSection";
import EarningsCallPanel from "@/components/EarningsCallPanel";
import TruthBreakdown from "@/components/TruthBreakdown";
import ConvictionPanel from "@/components/ConvictionPanel";
import MonteCarloChart from "@/components/MonteCarloChart";
import {
    CompanySnapshot,
    DataSources,
    FinancialTrends,
    Methodology,
    ReportCover,
    ReportSection,
    RiskRegister,
} from "@/components/report/ReportParts";
import {
    runForensicAudit,
    zScoreComponentRows,
    API_BASE,
    type ZScoreResult,
    type ForensicAuditResponse,
} from "@/lib/api";

interface ReportData {
    ticker: string;
    companyName: string;
    timestamp: string;
    zScore: ZScoreResult | null;
    forensic: ForensicAuditResponse;
}

export default function ReportsPage() {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [report, setReport] = useState<ReportData | null>(null);
    const reportRef = useRef<HTMLDivElement>(null);

    const handleSearch = useCallback(async (ticker: string) => {
        setIsLoading(true);
        setError(null);

        try {
            // The audit already computes the Z-Score and resolves the company name
            const audit = await runForensicAudit(ticker);
            setReport({
                ticker: audit.ticker,
                companyName: audit.company_name || audit.ticker,
                timestamp: audit.timestamp,
                zScore: audit.forensic.z_score_result,
                forensic: audit,
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : "Report generation failed.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    const handlePrint = () => window.print();

    const z = report?.zScore;
    const f = report?.forensic.forensic;
    const audit = report?.forensic;

    return (
        <div style={{ minHeight: "100vh", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
            <DashboardHeader />

            <main style={{ flex: 1, width: "100%", maxWidth: 1480, margin: "0 auto", padding: "40px 24px" }}>

                {/* ── Hero ── */}
                <AnimatedSection className="text-center mb-12 print:hidden">
                    <div style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 12px",
                        borderRadius: 3,
                        background: "var(--green-tint)",
                        border: "1px solid var(--green-tint)",
                        marginBottom: 14,
                    }}>
                        <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)" }} />
                        <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--green)" }}>
                            Report Generator
                        </span>
                    </div>

                    <h2 style={{
                        fontFamily: "var(--font-source-serif, Georgia, serif)",
                        fontSize: "clamp(26px, 4vw, 42px)",
                        fontWeight: 700,
                        color: "var(--ink)",
                        lineHeight: 1.15,
                        letterSpacing: "-0.02em",
                        marginBottom: 12,
                    }}>
                        Research{" "}
                        <span style={{ color: "var(--green)" }}>Report</span>
                    </h2>
                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 14, color: "var(--ink-2)", maxWidth: 480, margin: "0 auto 32px" }}>
                        A full research report: investment conviction, financial trends, Z-Score,
                        Truth Score, earnings call, stress test and risk register. Print-ready.
                    </p>
                    <TickerSearch onSearch={handleSearch} isLoading={isLoading} />
                </AnimatedSection>

                {/* ── Error ── */}
                {error && (
                    <AnimatedSection className="mb-6 print:hidden">
                        <div style={{ background: "var(--red-tint)", borderLeft: "4px solid var(--red)", borderRadius: "0 4px 4px 0", padding: "12px 16px" }}>
                            <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 13, color: "var(--ink-2)" }}>{error}</p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── Loading ── */}
                {isLoading && (
                    <AnimatedSection className="mb-10 print:hidden">
                        <div style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: 40, textAlign: "center" }}>
                            <div style={{ width: 24, height: 24, border: "2px solid var(--rule)", borderTopColor: "var(--green)", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-2)" }}>
                                Generating research report...
                            </p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── Report ── */}
                {report && audit && !isLoading && (
                    <FadeTransition transitionKey={`report-${report.ticker}`}>
                        <div>
                            {/* Action Buttons */}
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginBottom: 16 }} className="print:hidden">
                                <button
                                    id="report-download-pdf"
                                    onClick={async () => {
                                        try {
                                            const res = await fetch(`${API_BASE}/api/reports/generate-pdf`, {
                                                method: "POST",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ ticker: report.ticker }),
                                            });
                                            if (res.status === 429) throw new Error("Rate limit reached — please wait a minute and try again.");
                                            if (!res.ok) throw new Error("PDF generation failed");
                                            const blob = await res.blob();
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = `AlphaGuard_${report.ticker}_Report.pdf`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        } catch (err) {
                                            alert(err instanceof Error && err.message !== "Failed to fetch"
                                                ? err.message
                                                : "PDF generation failed. Is the backend running?");
                                        }
                                    }}
                                    style={{
                                        display: "flex", alignItems: "center", gap: 6,
                                        padding: "7px 16px", borderRadius: 4,
                                        background: "var(--paper-2)", color: "var(--ink-2)",
                                        border: "1px solid var(--rule-strong)",
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 10, fontWeight: 600, letterSpacing: "0.1em",
                                        textTransform: "uppercase", cursor: "pointer",
                                        transition: "border-color 0.15s ease",
                                    }}
                                >
                                    <svg style={{ width: 12, height: 12 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                                        <polyline points="7 10 12 15 17 10" />
                                        <line x1="12" y1="15" x2="12" y2="3" />
                                    </svg>
                                    Download PDF
                                </button>
                                <button
                                    id="report-print-btn"
                                    onClick={handlePrint}
                                    style={{
                                        display: "flex", alignItems: "center", gap: 6,
                                        padding: "7px 16px", borderRadius: 4,
                                        background: "var(--green)", color: "#ffffff",
                                        border: "1px solid var(--green)",
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 10, fontWeight: 600, letterSpacing: "0.1em",
                                        textTransform: "uppercase", cursor: "pointer",
                                        transition: "background 0.15s ease",
                                    }}
                                >
                                    <svg style={{ width: 12, height: 12 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                                        <polyline points="6 9 6 2 18 2 18 9" />
                                        <path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2" />
                                        <rect x="6" y="14" width="12" height="8" />
                                    </svg>
                                    Print / Save PDF
                                </button>
                            </div>

                            {/* Report Document */}
                            <div
                                ref={reportRef}
                                style={{
                                    background: "var(--paper-2)",
                                    border: "1px solid var(--rule)",
                                    borderRadius: 4,
                                    overflow: "hidden",
                                }}
                            >
                                {/* Cover: key metrics, contents, team */}
                                <ReportCover audit={audit} />

                                <ReportSection id="summary">
                                    {audit.conviction ? (
                                        <ConvictionPanel conviction={audit.conviction} />
                                    ) : (
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-faint)" }}>
                                            Investment conviction unavailable for this ticker.
                                        </p>
                                    )}
                                </ReportSection>

                                <ReportSection id="snapshot" accent="var(--blue)">
                                    <CompanySnapshot fin={audit.financials} />
                                </ReportSection>

                                <ReportSection id="trends" accent="var(--blue)">
                                    <FinancialTrends history={audit.financials?.history} />
                                </ReportSection>

                                <ReportSection id="health" accent="var(--green)">
                                    {z ? (
                                        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 32 }} className="grid-cols-1 md:grid-cols-3">
                                            {/* Score */}
                                            <div style={{ textAlign: "center" }}>
                                                <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 6 }}>Z-Score</p>
                                                <p style={{
                                                    fontFamily: "var(--font-source-serif, Georgia, serif)",
                                                    fontSize: 52,
                                                    fontWeight: 700,
                                                    lineHeight: 1,
                                                    color: z.zone === "Safe" ? "var(--green)" : z.zone === "Distress" ? "var(--red)" : "var(--amber)",
                                                    margin: "0 0 8px",
                                                }}>
                                                    {z.score.toFixed(2)}
                                                </p>
                                                <span style={{
                                                    padding: "3px 10px",
                                                    borderRadius: 3,
                                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                    fontSize: 9,
                                                    fontWeight: 600,
                                                    letterSpacing: "0.12em",
                                                    textTransform: "uppercase",
                                                    background: z.zone === "Safe" ? "var(--green-tint)" : z.zone === "Distress" ? "var(--red-tint)" : "var(--amber-tint)",
                                                    color: z.zone === "Safe" ? "var(--green)" : z.zone === "Distress" ? "var(--red)" : "var(--amber)",
                                                }}>
                                                    {z.zone} Zone
                                                </span>
                                            </div>

                                            {/* Components table */}
                                            <div>
                                                <table style={{ width: "100%", fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 11, borderCollapse: "collapse" }}>
                                                    <thead>
                                                        <tr style={{ color: "var(--ink-faint)", fontSize: 9, textAlign: "left" }}>
                                                            <th style={{ padding: "0 0 8px", fontWeight: 500 }}>Component</th>
                                                            <th style={{ padding: "0 0 8px", textAlign: "right", fontWeight: 500 }}>Ratio</th>
                                                            <th style={{ padding: "0 0 8px", textAlign: "right", fontWeight: 500 }}>Weight</th>
                                                            <th style={{ padding: "0 0 8px", textAlign: "right", fontWeight: 500 }}>Weighted</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody style={{ color: "var(--ink-2)" }}>
                                                        {zScoreComponentRows(z).map((r) => ({ label: r.label, val: r.value, w: r.weight })).map((c) => (
                                                            <tr key={c.label} style={{ borderTop: "1px solid var(--rule)" }}>
                                                                <td style={{ padding: "6px 0" }}>{c.label}</td>
                                                                <td style={{ padding: "6px 0", textAlign: "right" }}>{c.val.toFixed(4)}</td>
                                                                <td style={{ padding: "6px 0", textAlign: "right", color: "var(--ink-faint)" }}>×{c.w}</td>
                                                                <td style={{ padding: "6px 0", textAlign: "right", fontWeight: 600, color: "var(--ink)" }}>{(c.val * c.w).toFixed(4)}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                                {z && (
                                                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 11, color: "var(--ink-2)", lineHeight: 1.55, fontStyle: "italic", marginTop: 12 }}>
                                                        {z.interpretation}
                                                    </p>
                                                )}
                                                {z?.model_label && (
                                                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 6 }}>
                                                        Model: {z.model_label}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ) : (
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-faint)" }}>
                                            {audit.data_sources.find((s) => s.startsWith("Z-Score not computed") || s.startsWith("Financial data unavailable"))
                                                ?? "Z-Score data unavailable for this ticker."}
                                        </p>
                                    )}
                                </ReportSection>

                                <ReportSection id="forensic" accent="var(--red)">
                                    {f ? (
                                        <div>
                                            {/* Key Metrics */}
                                            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0, border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden", marginBottom: 20 }}>
                                                {[
                                                    f.truth_score === null
                                                        ? { label: "Truth Score", value: "N/A", sub: "not enough evidence", color: "var(--ink-faint)" }
                                                        : { label: "Truth Score", value: String(f.truth_score), sub: f.truth_zone ?? "", color: f.truth_score >= 70 ? "var(--green)" : f.truth_score >= 40 ? "var(--amber)" : "var(--red)" },
                                                    { label: "Hedging", value: f.linguistic_analysis.hedging_score.toFixed(1), sub: "score", color: "var(--ink)" },
                                                    { label: "Evasion", value: f.linguistic_analysis.evasion_score.toFixed(1), sub: "score", color: "var(--ink)" },
                                                    { label: "Sentiment", value: f.linguistic_analysis.sentiment.toUpperCase(), sub: f.linguistic_analysis.sentiment_source === "lexicon" ? "lexicon tone" : f.linguistic_analysis.sentiment_source === "ai" ? "Gemini" : "", color: f.linguistic_analysis.sentiment === "bullish" ? "var(--green)" : f.linguistic_analysis.sentiment === "bearish" ? "var(--red)" : "var(--amber)" },
                                                ].map((item, i, arr) => (
                                                    <div key={item.label} style={{ padding: "14px 16px", textAlign: "center", background: "var(--paper)", borderRight: i < arr.length - 1 ? "1px solid var(--rule)" : "none" }}>
                                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>{item.label}</p>
                                                        <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 22, fontWeight: 600, color: item.color }}>{item.value}</p>
                                                        {item.sub && <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 2 }}>{item.sub}</p>}
                                                    </div>
                                                ))}
                                            </div>

                                            {/* How the Truth Score was built */}
                                            <div style={{ marginBottom: 20 }}>
                                                <TruthBreakdown
                                                    breakdown={f.truth_score_breakdown}
                                                    score={f.truth_score}
                                                    note={f.analysis_note}
                                                    aiNote={audit.gemini_active ? null : audit.ai_error}
                                                />
                                            </div>

                                            {/* Deception Alert */}
                                            {f.deception_alert && f.deception_reason && (
                                                <div style={{ background: "var(--red-tint)", borderLeft: "4px solid var(--red)", borderRadius: "0 4px 4px 0", padding: "10px 14px", marginBottom: 20 }}>
                                                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--red)", marginBottom: 4 }}>
                                                        ⚠ Deception Alert
                                                    </p>
                                                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 12, color: "var(--ink-2)" }}>{f.deception_reason}</p>
                                                </div>
                                            )}

                                            {/* Red Flags */}
                                            {f.red_flags.length > 0 && (
                                                <div>
                                                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 10 }}>
                                                        Red Flags ({f.red_flags.length})
                                                    </p>
                                                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                                        {f.red_flags.map((flag, i) => (
                                                            <div key={i} style={{
                                                                padding: "12px 14px",
                                                                borderRadius: 4,
                                                                background: "var(--paper)",
                                                                border: "1px solid var(--rule)",
                                                                borderLeft: `3px solid ${flag.severity >= 8 ? "var(--red)" : flag.severity >= 5 ? "var(--amber)" : "var(--blue)"}`,
                                                            }}>
                                                                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                                                                    <span style={{
                                                                        padding: "1px 6px", borderRadius: 3,
                                                                        fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, fontWeight: 600,
                                                                        background: flag.severity >= 8 ? "var(--red-tint)" : flag.severity >= 5 ? "var(--amber-tint)" : "var(--blue-tint)",
                                                                        color: flag.severity >= 8 ? "var(--red)" : flag.severity >= 5 ? "var(--amber)" : "var(--blue)",
                                                                    }}>
                                                                        SEV {flag.severity}
                                                                    </span>
                                                                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink-faint)" }}>
                                                                        {flag.category}
                                                                    </span>
                                                                </div>
                                                                <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontStyle: "italic", fontSize: 12, color: "var(--ink)", marginBottom: 6, lineHeight: 1.5 }}>
                                                                    &quot;{flag.sentence}&quot;
                                                                </p>
                                                                <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 11, color: "var(--ink-2)", lineHeight: 1.5 }}>
                                                                    {flag.explanation}
                                                                </p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-faint)" }}>
                                            Forensic analysis unavailable for this ticker.
                                        </p>
                                    )}
                                </ReportSection>

                                <ReportSection id="call" accent="var(--amber)">
                                    <EarningsCallPanel call={audit.earnings_call} />
                                </ReportSection>

                                <ReportSection id="stress" accent="var(--blue)">
                                    {audit.monte_carlo ? (
                                        <div>
                                            {audit.monte_carlo.parameter_source && (
                                                <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 12, color: "var(--ink-2)", marginBottom: 12 }}>
                                                    Assumptions — {audit.monte_carlo.parameter_source}.
                                                </p>
                                            )}
                                            <MonteCarloChart data={audit.monte_carlo} />
                                        </div>
                                    ) : (
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-faint)" }}>
                                            Stress test not run (no revenue data).
                                        </p>
                                    )}
                                </ReportSection>

                                <ReportSection id="risks" accent="var(--red)">
                                    <RiskRegister items={audit.risk_register} />
                                </ReportSection>

                                <ReportSection id="methodology">
                                    <Methodology />
                                </ReportSection>

                                <ReportSection id="sources">
                                    <DataSources audit={audit} />
                                </ReportSection>

                                {/* Report Footer */}
                                <div style={{ padding: "10px 32px", background: "var(--paper)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                                        ALPHA-GUARD v0.5.0 · Research Report
                                    </span>
                                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                                        Generated by Alpha-Guard Forensic Credit Risk Platform
                                    </span>
                                </div>
                            </div>
                        </div>
                    </FadeTransition>
                )}
            </main>

            <footer style={{ borderTop: "1px solid var(--rule)", padding: "14px 24px" }} className="print:hidden">
                <div style={{ maxWidth: 1480, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>ALPHA-GUARD v0.5.0 · Research Reports</p>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>Powered by FastAPI · Next.js · SEC EDGAR · Google Gemini</p>
                </div>
            </footer>
        </div>
    );
}
