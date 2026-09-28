"use client";

import React from "react";
import type { InvestmentConviction } from "@/lib/api";

interface ConvictionPanelProps {
    conviction: InvestmentConviction | null | undefined;
}

const MONO = "var(--font-ibm-plex-mono, monospace)";
const SERIF = "var(--font-source-serif, Georgia, serif)";
const SANS = "var(--font-ibm-plex-sans, system-ui, sans-serif)";

function colorFor(score: number): string {
    if (score >= 80) return "var(--green)";
    if (score >= 65) return "var(--green)";
    if (score >= 50) return "var(--amber)";
    return "var(--red)";
}

function tintFor(score: number): string {
    if (score >= 65) return "var(--green-tint)";
    if (score >= 50) return "var(--amber-tint)";
    return "var(--red-tint)";
}

/** Circular conviction meter */
function Meter({ score }: { score: number }) {
    const r = 54;
    const c = 2 * Math.PI * r;
    return (
        <svg viewBox="0 0 140 140" style={{ width: 150, height: 150 }} role="img" aria-label={`Conviction ${score}%`}>
            <circle cx="70" cy="70" r={r} fill="none" stroke="var(--rule)" strokeWidth="10" />
            <circle
                cx="70" cy="70" r={r} fill="none" stroke={colorFor(score)} strokeWidth="10" strokeLinecap="round"
                strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} transform="rotate(-90 70 70)"
                style={{ transition: "stroke-dashoffset 1s ease-out" }}
            />
            <text x="70" y="74" textAnchor="middle" fontFamily="var(--font-source-serif, Georgia, serif)" fontWeight="700" fontSize="34" fill={colorFor(score)}>
                {score}%
            </text>
            <text x="70" y="94" textAnchor="middle" fontFamily="var(--font-ibm-plex-mono, monospace)" fontSize="8" letterSpacing="1.5" fill="var(--ink-faint)">
                CONVICTION
            </text>
        </svg>
    );
}

export default function ConvictionPanel({ conviction }: ConvictionPanelProps) {
    if (!conviction) return null;
    const score = conviction.score;

    return (
        <div>
            {/* Verdict */}
            <div
                style={{
                    display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap",
                    padding: 20, borderRadius: 4, marginBottom: 20,
                    background: score != null ? tintFor(score) : "var(--paper)",
                    border: "1px solid var(--rule)",
                }}
            >
                {score != null && <Meter score={score} />}
                <div style={{ flex: 1, minWidth: 240 }}>
                    {conviction.verdict && (
                        <p style={{ fontFamily: MONO, fontSize: 10, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: score != null ? colorFor(score) : "var(--ink-faint)", marginBottom: 6 }}>
                            {conviction.verdict}
                        </p>
                    )}
                    <p style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 600, color: "var(--ink)", lineHeight: 1.3, margin: 0 }}>
                        {conviction.headline}
                    </p>
                    {conviction.capped_reason && (
                        <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--red)", marginTop: 8 }}>{conviction.capped_reason}</p>
                    )}
                </div>
            </div>

            {/* Pillars */}
            {conviction.pillars.length > 0 && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 20 }} className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                    {conviction.pillars.map((p) => (
                        <div key={p.key} style={{ padding: "12px 14px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4 }}>
                            <div style={{ display: "flex", alignItems: "baseline", marginBottom: 6 }}>
                                <span style={{ fontFamily: SERIF, fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>{p.label}</span>
                                <span style={{ marginLeft: "auto", fontFamily: SERIF, fontSize: 18, fontWeight: 700, color: colorFor(p.score) }}>{p.score}</span>
                            </div>
                            <div style={{ height: 5, background: "var(--rule)", borderRadius: 3, overflow: "hidden", marginBottom: 6 }}>
                                <div style={{ width: `${p.score}%`, height: "100%", background: colorFor(p.score) }} />
                            </div>
                            {p.metric && (
                                <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-2)", margin: "0 0 2px" }}>{p.metric}</p>
                            )}
                            <p style={{ fontFamily: SANS, fontSize: 11, color: "var(--ink-faint)", lineHeight: 1.45, margin: 0 }}>
                                {p.detail} <span style={{ fontFamily: MONO, fontSize: 9 }}>· weight {Math.round(p.effective_weight * 100)}%</span>
                            </p>
                        </div>
                    ))}
                </div>
            )}

            {/* Strengths & concerns */}
            {(conviction.strengths.length > 0 || conviction.concerns.length > 0) && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }} className="grid-cols-1 md:grid-cols-2">
                    {[
                        { title: "Strengths", items: conviction.strengths, color: "var(--green)", empty: "No standout strengths." },
                        { title: "Concerns", items: conviction.concerns, color: "var(--red)", empty: "No major concerns found." },
                    ].map((col) => (
                        <div key={col.title} style={{ padding: "12px 14px", background: "var(--paper)", border: "1px solid var(--rule)", borderTop: `3px solid ${col.color}`, borderRadius: 4 }}>
                            <p style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: col.color, marginBottom: 8 }}>
                                {col.title}
                            </p>
                            {col.items.length === 0 ? (
                                <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-faint)" }}>{col.empty}</p>
                            ) : (
                                <ul style={{ margin: 0, paddingLeft: 16 }}>
                                    {col.items.map((item) => (
                                        <li key={item} style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.55 }}>{item}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    ))}
                </div>
            )}

            <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", lineHeight: 1.5 }}>{conviction.disclaimer}</p>
        </div>
    );
}
