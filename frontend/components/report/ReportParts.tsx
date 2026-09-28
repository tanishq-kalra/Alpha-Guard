"use client";

import React from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import type { FinancialData, ForensicAuditResponse, HistoryPoint, RiskItem } from "@/lib/api";
import { TEAM } from "@/lib/team";

const MONO = "var(--font-ibm-plex-mono, monospace)";
const SERIF = "var(--font-source-serif, Georgia, serif)";
const SANS = "var(--font-ibm-plex-sans, system-ui, sans-serif)";

export const REPORT_SECTIONS = [
    { id: "summary", title: "Executive Summary — Should You Invest?" },
    { id: "snapshot", title: "1. Company Snapshot" },
    { id: "trends", title: "2. Financial Trends" },
    { id: "health", title: "3. Financial Health (Altman Z-Score)" },
    { id: "forensic", title: "4. Truth Score & Forensic Analysis" },
    { id: "call", title: "5. Earnings Conference Call" },
    { id: "stress", title: "6. Revenue Stress Test (Monte Carlo)" },
    { id: "risks", title: "7. Risk Register" },
    { id: "methodology", title: "8. Methodology & References" },
    { id: "sources", title: "9. Data Sources & Disclaimer" },
] as const;

export type SectionId = (typeof REPORT_SECTIONS)[number]["id"];

export function money(v: number | null | undefined): string {
    if (v == null) return "—";
    const a = Math.abs(v);
    const sign = v < 0 ? "-" : "";
    if (a >= 1e12) return `${sign}$${(a / 1e12).toFixed(2)}T`;
    if (a >= 1e9) return `${sign}$${(a / 1e9).toFixed(1)}B`;
    if (a >= 1e6) return `${sign}$${(a / 1e6).toFixed(0)}M`;
    return `${sign}$${a.toLocaleString()}`;
}

function pct(v: number | null | undefined, digits = 1): string {
    return v == null || !isFinite(v) ? "—" : `${(v * 100).toFixed(digits)}%`;
}

const cellStyle: React.CSSProperties = { padding: "7px 10px", borderTop: "1px solid var(--rule)", fontFamily: MONO, fontSize: 11, color: "var(--ink-2)" };
const headStyle: React.CSSProperties = { padding: "0 10px 8px", fontFamily: MONO, fontSize: 9, fontWeight: 500, color: "var(--ink-faint)", textAlign: "left", letterSpacing: "0.06em", textTransform: "uppercase" };

/** Numbered section wrapper with an anchor for the table of contents. */
export function ReportSection({ id, accent = "var(--ink)", children }: { id: SectionId; accent?: string; children: React.ReactNode }) {
    const title = REPORT_SECTIONS.find((s) => s.id === id)!.title;
    return (
        <section id={`report-${id}`} style={{ padding: "24px 32px", borderBottom: "1px solid var(--rule)", scrollMarginTop: 80, breakInside: "avoid-page" }}>
            <h3 style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: SERIF, fontSize: 16, fontWeight: 600, color: "var(--ink)", marginBottom: 18 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: accent, flexShrink: 0 }} />
                {title}
            </h3>
            {children}
        </section>
    );
}

// ── Cover ──

function Tile({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
    return (
        <div style={{ padding: "16px 12px", textAlign: "center", background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4 }}>
            <p style={{ fontFamily: SERIF, fontSize: 30, fontWeight: 700, color, margin: 0, lineHeight: 1.1 }}>{value}</p>
            <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginTop: 6 }}>{label}</p>
            <p style={{ fontFamily: SANS, fontSize: 11, color: "var(--ink-2)", marginTop: 2 }}>{sub}</p>
        </div>
    );
}

function scoreColor(score: number | null | undefined, good = 70, fair = 40): string {
    if (score == null) return "var(--ink-faint)";
    return score >= good ? "var(--green)" : score >= fair ? "var(--amber)" : "var(--red)";
}

export function ReportCover({ audit }: { audit: ForensicAuditResponse }) {
    const f = audit.forensic;
    const z = f.z_score_result;
    const conv = audit.conviction;
    const zColor = z ? (z.zone === "Safe" ? "var(--green)" : z.zone === "Distress" ? "var(--red)" : "var(--amber)") : "var(--ink-faint)";
    const date = new Date(audit.timestamp);

    return (
        <div style={{ padding: "32px", borderBottom: "1px solid var(--rule)", background: "var(--paper)" }}>
            <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--green)", marginBottom: 6 }}>
                Alpha-Guard · Forensic Credit &amp; Investment Research Report
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap", marginBottom: 4 }}>
                <h2 style={{ fontFamily: SERIF, fontSize: 30, fontWeight: 700, color: "var(--ink)", margin: 0 }}>{audit.company_name || audit.ticker}</h2>
                <span style={{ fontFamily: MONO, fontSize: 14, color: "var(--ink-2)" }}>{audit.ticker}</span>
            </div>
            <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginBottom: 22 }}>
                Generated {date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} at {date.toLocaleTimeString()}
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 26 }} className="grid-cols-1 sm:grid-cols-3">
                <Tile label="Investment conviction" value={conv?.score != null ? `${conv.score}%` : "N/A"} sub={conv?.verdict ?? "not enough data"} color={scoreColor(conv?.score, 65, 50)} />
                <Tile label="Truth Score" value={f.truth_score != null ? String(f.truth_score) : "N/A"} sub={f.truth_zone ?? "not enough evidence"} color={scoreColor(f.truth_score)} />
                <Tile label="Altman Z-Score" value={z ? z.score.toFixed(2) : "N/A"} sub={z ? `${z.zone} zone` : "not applicable"} color={zColor} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 28 }} className="grid-cols-1 md:grid-cols-2">
                <nav aria-label="Report contents">
                    <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>Contents</p>
                    <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
                        {REPORT_SECTIONS.map((s) => (
                            <li key={s.id} style={{ margin: "3px 0" }}>
                                <a href={`#report-${s.id}`} style={{ fontFamily: SANS, fontSize: 13, color: "var(--ink-2)", textDecoration: "none" }}>
                                    {s.title}
                                </a>
                            </li>
                        ))}
                    </ol>
                </nav>
                <div>
                    <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>Prepared by</p>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                        <tbody>
                            {TEAM.map((m) => (
                                <tr key={m.rollNo}>
                                    <td style={{ ...cellStyle, fontFamily: SANS, fontSize: 13, color: "var(--ink)" }}>{m.name}</td>
                                    <td style={{ ...cellStyle, textAlign: "right" }}>{m.rollNo}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", marginTop: 8 }}>Capstone Project · Alpha-Guard</p>
                </div>
            </div>
        </div>
    );
}

// ── 1. Company snapshot ──

export function CompanySnapshot({ fin }: { fin: FinancialData | null | undefined }) {
    if (!fin) return <p style={{ fontFamily: MONO, fontSize: 12, color: "var(--ink-faint)" }}>Financial statement data unavailable for this ticker.</p>;
    const equity = fin.total_assets - fin.total_liabilities;
    const ni = fin.net_income ?? null;
    const figures: [string, string][] = [
        ["Fiscal year ending", fin.fiscal_period_end ?? "—"],
        ["Market capitalisation", money(fin.market_cap)],
        ["Revenue", money(fin.revenue)],
        ["Net income", money(ni)],
        ["Operating cash flow", money(fin.operating_cash_flow)],
        ["Total assets", money(fin.total_assets)],
        ["Total liabilities", money(fin.total_liabilities)],
        ["Shareholders' equity (book)", money(equity)],
    ];
    const ratios: [string, string, string][] = [
        ["Net margin", pct(ni != null && fin.revenue ? ni / fin.revenue : null), "Profit kept from each dollar of sales"],
        ["Return on assets", pct(ni != null ? ni / fin.total_assets : null, 2), "Profit generated per dollar of assets"],
        ["Revenue growth (YoY)", pct(fin.revenue_prior_year ? fin.revenue / fin.revenue_prior_year - 1 : null), "Change vs the previous fiscal year"],
        ["Liabilities / assets", pct(fin.total_liabilities / fin.total_assets), "Share of assets funded by debt and other liabilities"],
        ["Price / earnings", fin.market_cap && ni && ni > 0 ? `${(fin.market_cap / ni).toFixed(1)}x` : "—", "Years of current profit the market price represents"],
        ["Cash conversion", fin.operating_cash_flow != null && ni ? `${(fin.operating_cash_flow / ni).toFixed(2)}x` : "—", "Operating cash flow ÷ net income (≥ 1 is healthy)"],
    ];
    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 24 }} className="grid-cols-1 lg:grid-cols-2">
            <div>
                <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>Key figures</p>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <tbody>
                        {figures.map(([k, v]) => (
                            <tr key={k}>
                                <td style={{ ...cellStyle, fontFamily: SANS, fontSize: 12 }}>{k}</td>
                                <td style={{ ...cellStyle, textAlign: "right", color: "var(--ink)", fontWeight: 600 }}>{v}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div>
                <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>Key ratios</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
                    {ratios.map(([k, v, hint]) => (
                        <div key={k} style={{ padding: "10px 12px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4 }}>
                            <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", textTransform: "uppercase", letterSpacing: "0.08em", margin: 0 }}>{k}</p>
                            <p style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 600, color: "var(--ink)", margin: "2px 0" }}>{v}</p>
                            <p style={{ fontFamily: SANS, fontSize: 10, color: "var(--ink-faint)", margin: 0 }}>{hint}</p>
                        </div>
                    ))}
                </div>
                <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", marginTop: 8 }}>
                    Classification: {fin.sector && fin.sector !== "Unknown" ? fin.sector : fin.sic_code ? `SIC ${fin.sic_code}` : "—"}
                </p>
            </div>
        </div>
    );
}

// ── 2. Financial trends ──

export function FinancialTrends({ history }: { history: HistoryPoint[] | undefined }) {
    const points = [...(history ?? [])].reverse().filter((h) => h.revenue != null);
    if (points.length < 2) {
        return <p style={{ fontFamily: MONO, fontSize: 12, color: "var(--ink-faint)" }}>Not enough annual history available to show trends.</p>;
    }
    const data = points.map((h) => ({
        year: `FY${h.fiscal_period_end.slice(0, 4)}`,
        Revenue: (h.revenue ?? 0) / 1e9,
        "Net income": (h.net_income ?? 0) / 1e9,
        "Operating cash flow": (h.operating_cash_flow ?? 0) / 1e9,
    }));
    const first = points[0].revenue!;
    const last = points[points.length - 1].revenue!;
    const cagr = first > 0 ? Math.pow(last / first, 1 / (points.length - 1)) - 1 : null;

    return (
        <div>
            <div style={{ width: "100%", height: 280, marginBottom: 16 }}>
                <ResponsiveContainer>
                    <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--rule)" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 11, fill: "var(--ink-2)", fontFamily: "monospace" }} axisLine={{ stroke: "var(--rule)" }} tickLine={false} />
                        <YAxis tickFormatter={(v: number) => `$${v.toFixed(0)}B`} tick={{ fontSize: 10, fill: "var(--ink-faint)", fontFamily: "monospace" }} axisLine={false} tickLine={false} width={60} />
                        <Tooltip formatter={(v) => `$${Number(v).toFixed(1)}B`} contentStyle={{ fontFamily: "monospace", fontSize: 11, borderRadius: 4 }} />
                        <Legend wrapperStyle={{ fontFamily: "monospace", fontSize: 11 }} />
                        <Bar dataKey="Revenue" fill="#2563eb" radius={[2, 2, 0, 0]} />
                        <Bar dataKey="Net income" fill="#0d9488" radius={[2, 2, 0, 0]} />
                        <Bar dataKey="Operating cash flow" fill="#94a3b8" radius={[2, 2, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
            <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
                    <thead>
                        <tr>{["Fiscal year", "Revenue", "Growth", "Net income", "Margin", "Operating CF", "Total assets"].map((h, i) => (
                            <th key={h} style={{ ...headStyle, textAlign: i === 0 ? "left" : "right" }}>{h}</th>
                        ))}</tr>
                    </thead>
                    <tbody>
                        {points.map((h, i) => {
                            const prev = i > 0 ? points[i - 1].revenue : null;
                            const cells = [
                                money(h.revenue),
                                prev && h.revenue ? pct(h.revenue / prev - 1) : "—",
                                money(h.net_income),
                                h.net_income != null && h.revenue ? pct(h.net_income / h.revenue) : "—",
                                money(h.operating_cash_flow),
                                money(h.total_assets),
                            ];
                            return (
                                <tr key={h.fiscal_period_end}>
                                    <td style={cellStyle}>FY{h.fiscal_period_end.slice(0, 4)}</td>
                                    {cells.map((c, j) => <td key={j} style={{ ...cellStyle, textAlign: "right" }}>{c}</td>)}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            {cagr != null && (
                <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginTop: 8 }}>
                    Revenue compound annual growth over {points.length - 1} years: {cagr >= 0 ? "+" : ""}{(cagr * 100).toFixed(1)}%
                </p>
            )}
        </div>
    );
}

// ── 7. Risk register ──

const SEVERITY_COLOR = { high: "var(--red)", medium: "var(--amber)", low: "var(--ink-faint)" } as const;

export function RiskRegister({ items }: { items: RiskItem[] | undefined }) {
    const list = items ?? [];
    if (list.length === 0) {
        return <p style={{ fontFamily: SANS, fontSize: 13, color: "var(--green)" }}>No material risks were flagged by any of the analyses.</p>;
    }
    const count = (s: RiskItem["severity"]) => list.filter((i) => i.severity === s).length;
    return (
        <div>
            <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
                {(["high", "medium", "low"] as const).map((s) => (
                    <span key={s} style={{ padding: "4px 12px", borderRadius: 3, border: `1px solid ${SEVERITY_COLOR[s]}`, fontFamily: MONO, fontSize: 10, fontWeight: 600, color: SEVERITY_COLOR[s], textTransform: "uppercase", letterSpacing: "0.1em" }}>
                        {count(s)} {s}
                    </span>
                ))}
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>{["Severity", "Area", "Finding"].map((h) => <th key={h} style={headStyle}>{h}</th>)}</tr>
                </thead>
                <tbody>
                    {list.map((r, i) => (
                        <tr key={i}>
                            <td style={{ ...cellStyle, color: SEVERITY_COLOR[r.severity], fontWeight: 700, textTransform: "uppercase", width: 90 }}>{r.severity}</td>
                            <td style={{ ...cellStyle, fontFamily: SANS, fontSize: 12, width: 180 }}>{r.area}</td>
                            <td style={{ ...cellStyle, fontFamily: SANS, fontSize: 12, lineHeight: 1.5 }}>{r.finding}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── 8. Methodology & references ──

const METHODS: [string, string][] = [
    ["Altman Z-Score", "Weighted ratios of working capital, retained earnings, EBIT, equity and sales to assets. The original model is used for US manufacturers; Z'' (book equity, no sales term) for other companies. Banks and insurers are judged on capital strength (equity ÷ assets) and return on assets instead."],
    ["Truth Score", "Credibility Index combining financial health (30%), filing language (20%), earnings-call candor (20%), narrative consistency (15%) and earnings quality (15%). Missing evidence is excluded and the weights re-balanced."],
    ["Filing language", "Whole-word dictionaries count hedging (e.g. 'may', 'uncertain') and evasive phrases (e.g. 'we believe') in the 10-K MD&A, or in the earnings press release when no MD&A is found. Only language above normal filing levels is penalised."],
    ["Earnings call", "Transcripts are split into scripted remarks and analyst Q&A. Refusals to answer, very short answers and a tone drop from script to Q&A lower the Call Candor Score."],
    ["Earnings quality", "Accruals = (net income − operating cash flow) ÷ total assets. Profits not backed by cash are a classic warning sign of aggressive accounting."],
    ["Investment conviction", "Six pillars: financial strength, profitability, growth, credibility, valuation (P/E) and earnings quality. A deception alert caps conviction at 45%."],
    ["Stress test", "1,000 revenue paths simulated with geometric Brownian motion, using the company's own historical revenue growth and volatility."],
];

const REFERENCES: [string, string][] = [
    ["Altman, E. I. (1968)", "Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy. Journal of Finance, 23(4), 589–609."],
    ["Altman, E. I. (2000)", "Predicting Financial Distress of Companies: Revisiting the Z-Score and ZETA Models. NYU Stern working paper."],
    ["Sloan, R. G. (1996)", "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings? The Accounting Review, 71(3), 289–315."],
    ["Loughran, T. & McDonald, B. (2011)", "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks. Journal of Finance, 66(1), 35–65."],
    ["Larcker, D. F. & Zakolyukina, A. A. (2012)", "Detecting Deceptive Discussions in Conference Calls. Journal of Accounting Research, 50(2), 495–540."],
    ["Glasserman, P. (2003)", "Monte Carlo Methods in Financial Engineering. Springer."],
];

export function Methodology() {
    return (
        <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, marginBottom: 20 }} className="grid-cols-1 md:grid-cols-2">
                {METHODS.map(([title, text]) => (
                    <div key={title} style={{ padding: "12px 14px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4 }}>
                        <p style={{ fontFamily: SERIF, fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>{title}</p>
                        <p style={{ fontFamily: SANS, fontSize: 11.5, color: "var(--ink-2)", lineHeight: 1.55, margin: 0 }}>{text}</p>
                    </div>
                ))}
            </div>
            <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 8 }}>References</p>
            <ol style={{ margin: 0, paddingLeft: 18 }}>
                {REFERENCES.map(([author, work]) => (
                    <li key={author} style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.6 }}>
                        <b style={{ color: "var(--ink)" }}>{author}</b> {work}
                    </li>
                ))}
            </ol>
        </div>
    );
}

// ── 9. Data sources ──

export function DataSources({ audit }: { audit: ForensicAuditResponse }) {
    return (
        <div>
            <ul style={{ margin: "0 0 14px", paddingLeft: 18 }}>
                {audit.data_sources.map((s) => (
                    <li key={s} style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.6 }}>{s}</li>
                ))}
                {!audit.gemini_active && audit.ai_error && (
                    <li style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-faint)", lineHeight: 1.6 }}>AI red-flag scan not used: {audit.ai_error}</li>
                )}
            </ul>
            <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", lineHeight: 1.6 }}>
                Disclaimer: this report is generated automatically from public data (SEC EDGAR, Yahoo Finance, Alpha Vantage) by
                rule-based models for educational purposes. It is not investment advice. Figures may contain errors from source data
                or extraction; verify against the original filings before relying on them.
            </p>
        </div>
    );
}
