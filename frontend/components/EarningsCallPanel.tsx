"use client";

import React from "react";
import type { CallSegmentMetrics, EarningsCallAnalysis } from "@/lib/api";

interface EarningsCallPanelProps {
    call: EarningsCallAnalysis | null | undefined;
}

const MONO = "var(--font-ibm-plex-mono, monospace)";
const SERIF = "var(--font-source-serif, Georgia, serif)";
const SANS = "var(--font-ibm-plex-sans, system-ui, sans-serif)";

function sentimentColor(sentiment: string | undefined): string {
    if (sentiment === "bullish") return "var(--green)";
    if (sentiment === "bearish") return "var(--red)";
    return "var(--amber)";
}

function candorColor(score: number): string {
    if (score >= 75) return "var(--green)";
    if (score >= 50) return "var(--amber)";
    return "var(--red)";
}

function formatTone(tone: number | null | undefined): string {
    if (tone == null) return "—";
    return `${tone > 0 ? "+" : ""}${tone.toFixed(2)}`;
}

function Label({ children }: { children: React.ReactNode }) {
    return (
        <p style={{ fontFamily: MONO, fontSize: 8, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 6 }}>
            {children}
        </p>
    );
}

/** Hedging/evasion bar, 0-100 */
function Bar({ label, value }: { label: string; value: number }) {
    const color = value > 30 ? "var(--red)" : value > 15 ? "var(--amber)" : "var(--green)";
    return (
        <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 10, color: "var(--ink-2)", marginBottom: 4 }}>
                <span>{label}</span>
                <span style={{ color }}>{value.toFixed(1)}</span>
            </div>
            <div style={{ height: 6, background: "var(--rule)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${Math.min(100, value)}%`, height: "100%", background: color, transition: "width 0.8s ease-out" }} />
            </div>
        </div>
    );
}

function SegmentCard({ title, subtitle, seg }: { title: string; subtitle: string; seg: CallSegmentMetrics | null }) {
    return (
        <div style={{ padding: "16px 18px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4 }}>
            <p style={{ fontFamily: SERIF, fontSize: 13, fontWeight: 600, color: "var(--ink)", margin: 0 }}>{title}</p>
            <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", marginBottom: 14 }}>{subtitle}</p>
            {seg ? (
                <>
                    <div style={{ display: "flex", gap: 20, marginBottom: 14 }}>
                        <div>
                            <Label>Tone</Label>
                            <p style={{ fontFamily: SERIF, fontSize: 18, fontWeight: 600, color: sentimentColor(seg.sentiment), margin: 0 }}>
                                {seg.sentiment.toUpperCase()}
                            </p>
                            <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)" }}>net {formatTone(seg.net_tone)}</p>
                        </div>
                        <div>
                            <Label>Words</Label>
                            <p style={{ fontFamily: SERIF, fontSize: 18, fontWeight: 600, color: "var(--ink)", margin: 0 }}>{seg.words.toLocaleString()}</p>
                        </div>
                        {seg.provider_sentiment != null && (
                            <div>
                                <Label>Provider Sentiment</Label>
                                <p style={{ fontFamily: SERIF, fontSize: 18, fontWeight: 600, color: "var(--ink)", margin: 0 }}>{seg.provider_sentiment.toFixed(2)}</p>
                            </div>
                        )}
                    </div>
                    <Bar label="Hedging" value={seg.hedging_score} />
                    <Bar label="Evasion" value={seg.evasion_score} />
                </>
            ) : (
                <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-faint)" }}>Not available for this source.</p>
            )}
        </div>
    );
}

export default function EarningsCallPanel({ call }: EarningsCallPanelProps) {
    const available = !!call?.available;
    const isTranscript = call?.source === "alpha_vantage";

    return (
        <section style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden" }}>
            {/* Header */}
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--rule)", background: "var(--paper)", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <svg style={{ width: 15, height: 15, color: "var(--ink-faint)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="23" />
                </svg>
                <div>
                    <h3 style={{ fontFamily: SERIF, fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: 0 }}>Earnings Call Analysis</h3>
                    <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", margin: 0 }}>
                        Conference call · Prepared remarks vs analyst Q&amp;A
                    </p>
                </div>
                {available && call?.source_label && (
                    <span style={{ marginLeft: "auto", fontFamily: MONO, fontSize: 10, color: "var(--ink-2)", padding: "3px 10px", background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 3 }}>
                        {call.url ? (
                            <a href={call.url} target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>{call.source_label}</a>
                        ) : call.source_label}
                    </span>
                )}
            </div>

            {!available ? (
                <div style={{ padding: 20 }}>
                    <p style={{ fontFamily: SANS, fontSize: 13, color: "var(--ink-2)" }}>No earnings call data available for this company.</p>
                    {call?.note && <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginTop: 6 }}>{call.note}</p>}
                </div>
            ) : (
                <div style={{ padding: 20 }}>
                    {/* Headline metrics */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden", marginBottom: 16 }} className="grid-cols-2 sm:grid-cols-4">
                        {[
                            {
                                label: "Call Candor Score",
                                value: call!.candor_score != null ? String(call!.candor_score) : "N/A",
                                sub: call!.candor_score != null ? "/ 100" : "needs Q&A",
                                color: call!.candor_score != null ? candorColor(call!.candor_score) : "var(--ink-faint)",
                            },
                            {
                                label: "Analyst Questions",
                                value: isTranscript ? String(call!.analyst_questions) : "—",
                                sub: isTranscript ? "answered" : "press release",
                                color: "var(--ink)",
                            },
                            {
                                label: "Deflection Rate",
                                value: call!.deflection_rate != null && isTranscript ? `${Math.round(call!.deflection_rate * 100)}%` : "—",
                                sub: "answers declining to answer",
                                color: (call!.deflection_rate ?? 0) > 0.2 ? "var(--red)" : (call!.deflection_rate ?? 0) > 0 ? "var(--amber)" : "var(--green)",
                            },
                            {
                                label: "Tone Shift",
                                value: formatTone(call!.tone_shift),
                                sub: "Q&A vs prepared",
                                color: (call!.tone_shift ?? 0) <= -0.25 ? "var(--red)" : (call!.tone_shift ?? 0) < 0 ? "var(--amber)" : "var(--green)",
                            },
                        ].map((m, i, arr) => (
                            <div key={m.label} style={{ padding: "14px 16px", textAlign: "center", background: "var(--paper)", borderRight: i < arr.length - 1 ? "1px solid var(--rule)" : "none" }}>
                                <Label>{m.label}</Label>
                                <p style={{ fontFamily: SERIF, fontSize: 24, fontWeight: 600, color: m.color, margin: 0 }}>{m.value}</p>
                                <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", marginTop: 2 }}>{m.sub}</p>
                            </div>
                        ))}
                    </div>

                    {/* Prepared vs Q&A */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }} className="grid-cols-1 md:grid-cols-2">
                        <SegmentCard
                            title={isTranscript ? "Prepared Remarks" : "Management Commentary"}
                            subtitle={isTranscript ? "Scripted — CEO / CFO opening statements" : "From the earnings press release"}
                            seg={call!.prepared}
                        />
                        <SegmentCard
                            title="Analyst Q&A"
                            subtitle="Unscripted — executives' answers"
                            seg={call!.qa}
                        />
                    </div>

                    {/* Flags */}
                    {call!.flags.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                            <Label>Findings</Label>
                            <ul style={{ margin: 0, paddingLeft: 18 }}>
                                {call!.flags.map((f) => (
                                    <li key={f} style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.6 }}>{f}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Notable exchanges */}
                    {call!.exchanges.length > 0 && (
                        <div style={{ marginBottom: 16 }}>
                            <Label>Notable Q&amp;A Exchanges</Label>
                            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                                {call!.exchanges.map((ex, i) => {
                                    const flagged = !!ex.deflection_phrase || ex.brief;
                                    return (
                                        <div
                                            key={i}
                                            style={{
                                                padding: "12px 14px",
                                                background: "var(--paper)",
                                                border: "1px solid var(--rule)",
                                                borderLeft: `3px solid ${ex.deflection_phrase ? "var(--red)" : ex.brief ? "var(--amber)" : "var(--green)"}`,
                                                borderRadius: 4,
                                            }}
                                        >
                                            <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginBottom: 4 }}>
                                                Q · {ex.analyst}
                                            </p>
                                            <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink)", marginBottom: 8, lineHeight: 1.5 }}>
                                                {ex.question.length > 220 ? `${ex.question.slice(0, 220)}…` : ex.question}
                                            </p>
                                            <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginBottom: 4 }}>
                                                A · {ex.respondents.join(", ")} · {ex.answer_words} words
                                                {flagged && (
                                                    <span style={{ marginLeft: 8, color: ex.deflection_phrase ? "var(--red)" : "var(--amber)", fontWeight: 600 }}>
                                                        {ex.deflection_phrase ? `DEFLECTION: “${ex.deflection_phrase}”` : "BRIEF ANSWER"}
                                                    </span>
                                                )}
                                            </p>
                                            <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5, fontStyle: "italic" }}>
                                                {ex.answer_excerpt}
                                            </p>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Speakers + note */}
                    {call!.executives.length > 0 && (
                        <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)" }}>
                            Executives on the call: {call!.executives.join(" · ")}
                        </p>
                    )}
                    {call!.note && (
                        <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginTop: 6 }}>{call!.note}</p>
                    )}
                </div>
            )}
        </section>
    );
}
