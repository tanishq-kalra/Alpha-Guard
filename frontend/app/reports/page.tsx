"use client";

import { useState, useCallback, useRef } from "react";
import DashboardHeader from "@/components/DashboardHeader";
import TickerSearch from "@/components/TickerSearch";
import { AnimatedSection, FadeTransition } from "@/components/AnimatedSection";
import {
    fetchFinancials,
    calculateZScore,
    fetchCompanyInfo,
    runForensicAudit,
    type ZScoreResult,
    type ForensicAuditResponse,
} from "@/lib/api";

interface ReportData {
    ticker: string;
    companyName: string;
    timestamp: string;
    zScore: ZScoreResult | null;
    forensic: ForensicAuditResponse | null;
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
            const [financials, forensicResult] = await Promise.allSettled([
                fetchFinancials(ticker).then((fin) => calculateZScore(fin)),
                runForensicAudit(ticker),
            ]);

            let companyName = ticker;
            try {
                const info = await fetchCompanyInfo(ticker);
                companyName = info.name || ticker;
            } catch { /* optional */ }

            setReport({
                ticker: ticker.toUpperCase(),
                companyName,
                timestamp: new Date().toISOString(),
                zScore: financials.status === "fulfilled" ? financials.value : null,
                forensic: forensicResult.status === "fulfilled" ? forensicResult.value : null,
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : "Report generation failed.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    const handlePrint = () => window.print();

    const z = report?.zScore;
    const f = report?.forensic?.forensic;

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
                        Executive{" "}
                        <span style={{ color: "var(--green)" }}>Report</span>
                    </h2>
                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 14, color: "var(--ink-2)", maxWidth: 480, margin: "0 auto 32px" }}>
                        Generate a comprehensive risk assessment report combining Z-Score
                        analysis and forensic AI findings. Print-ready format.
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
                                Generating executive report...
                            </p>
                        </div>
                    </AnimatedSection>
                )}

                {/* ── Report ── */}
                {report && !isLoading && (
                    <FadeTransition transitionKey={`report-${report.ticker}`}>
                        <div>
                            {/* Action Buttons */}
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginBottom: 16 }} className="print:hidden">
                                <button
                                    id="report-download-pdf"
                                    onClick={async () => {
                                        try {
                                            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/reports/generate-pdf`, {
                                                method: "POST",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ ticker: report.ticker }),
                                            });
                                            if (!res.ok) throw new Error("PDF generation failed");
                                            const blob = await res.blob();
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = `AlphaGuard_${report.ticker}_Report.pdf`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        } catch {
                                            alert("PDF generation failed. Is the backend running?");
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
                                {/* Report Header */}
                                <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--rule)", background: "var(--paper)" }}>
                                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                                        <div>
                                            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                                                <span style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 22, fontWeight: 700, color: "var(--ink)" }}>
                                                    {report.ticker}
                                                </span>
                                                <span style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 14, color: "var(--ink-2)" }}>
                                                    {report.companyName}
                                                </span>
                                            </div>
                                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink-faint)" }}>
                                                Alpha-Guard Executive Risk Report · Confidential
                                            </p>
                                        </div>
                                        <div style={{ textAlign: "right" }}>
                                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, color: "var(--ink-faint)" }}>
                                                {new Date(report.timestamp).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
                                            </p>
                                            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 2 }}>
                                                {new Date(report.timestamp).toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Z-Score Section */}
                                <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--rule)" }}>
                                    <h3 style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 15, fontWeight: 600, color: "var(--ink)", marginBottom: 20 }}>
                                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", flexShrink: 0 }} />
                                        1. Altman Z-Score Analysis
                                    </h3>
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
                                                        {[
                                                            { label: "X1 — Working Capital / Assets", val: z.components.x1_working_capital_to_total_assets, w: 1.2 },
                                                            { label: "X2 — Retained Earnings / Assets", val: z.components.x2_retained_earnings_to_total_assets, w: 1.4 },
                                                            { label: "X3 — EBIT / Assets", val: z.components.x3_ebit_to_total_assets, w: 3.3 },
                                                            { label: "X4 — Market Cap / Liabilities", val: z.components.x4_market_cap_to_total_liabilities, w: 0.6 },
                                                            { label: "X5 — Revenue / Assets", val: z.components.x5_revenue_to_total_assets, w: 1.0 },
                                                        ].map((c) => (
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
                                            </div>
                                        </div>
                                    ) : (
                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 12, color: "var(--ink-faint)" }}>
                                            Z-Score data unavailable for this ticker.
                                        </p>
                                    )}
                                </div>

                                {/* Forensic Section */}
                                <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--rule)" }}>
                                    <h3 style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 15, fontWeight: 600, color: "var(--ink)", marginBottom: 20 }}>
                                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--red)", flexShrink: 0 }} />
                                        2. Forensic AI Analysis
                                    </h3>
                                    {f ? (
                                        <div>
                                            {/* Key Metrics */}
                                            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 0, border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden", marginBottom: 20 }}>
                                                {[
                                                    { label: "Truth Score", value: String(f.truth_score), sub: f.truth_zone, color: f.truth_score >= 70 ? "var(--green)" : f.truth_score >= 40 ? "var(--amber)" : "var(--red)" },
                                                    { label: "Hedging", value: f.linguistic_analysis.hedging_score.toFixed(1), sub: "%", color: "var(--ink)" },
                                                    { label: "Evasion", value: f.linguistic_analysis.evasion_score.toFixed(1), sub: "score", color: "var(--ink)" },
                                                    { label: "Sentiment", value: f.linguistic_analysis.sentiment.toUpperCase(), sub: "", color: f.linguistic_analysis.sentiment === "bullish" ? "var(--green)" : f.linguistic_analysis.sentiment === "bearish" ? "var(--red)" : "var(--amber)" },
                                                ].map((item, i, arr) => (
                                                    <div key={item.label} style={{ padding: "14px 16px", textAlign: "center", background: "var(--paper)", borderRight: i < arr.length - 1 ? "1px solid var(--rule)" : "none" }}>
                                                        <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>{item.label}</p>
                                                        <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 22, fontWeight: 600, color: item.color }}>{item.value}</p>
                                                        {item.sub && <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginTop: 2 }}>{item.sub}</p>}
                                                    </div>
                                                ))}
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
                                </div>

                                {/* Report Footer */}
                                <div style={{ padding: "10px 32px", background: "var(--paper)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                                        ALPHA-GUARD v0.3.0 · Confidential
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
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>ALPHA-GUARD v0.3.0 · Executive Reports</p>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>Powered by FastAPI · Next.js · SEC EDGAR · Google Gemini</p>
                </div>
            </footer>
        </div>
    );
}
