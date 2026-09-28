"use client";

import React from "react";
import type { TruthScoreBreakdown } from "@/lib/api";

interface TruthBreakdownProps {
    breakdown: TruthScoreBreakdown | null | undefined;
    score: number | null;
    note?: string | null;
    /** Why Gemini's red-flag scan didn't run, if it didn't */
    aiNote?: string | null;
}

const MONO = "var(--font-ibm-plex-mono, monospace)";
const SERIF = "var(--font-source-serif, Georgia, serif)";
const SANS = "var(--font-ibm-plex-sans, system-ui, sans-serif)";

function colorFor(score: number): string {
    if (score >= 70) return "var(--green)";
    if (score >= 40) return "var(--amber)";
    return "var(--red)";
}

export default function TruthBreakdown({ breakdown, score, note, aiNote }: TruthBreakdownProps) {
    const components = breakdown?.components ?? [];

    return (
        <section style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--rule)", background: "var(--paper)", display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
                <h3 style={{ fontFamily: SERIF, fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                    How the Truth Score was built
                </h3>
                <span style={{ fontFamily: MONO, fontSize: 9, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)" }}>
                    Weighted evidence · 5 components
                </span>
                {score != null && components.length > 0 && (
                    <span style={{ marginLeft: "auto", fontFamily: MONO, fontSize: 10, color: "var(--ink-2)" }}>
                        {components.map((c) => `${c.score}×${Math.round(c.effective_weight * 100)}%`).join(" + ")} = <b style={{ color: colorFor(score) }}>{score}</b>
                    </span>
                )}
            </div>

            <div style={{ padding: 20 }}>
                {components.length === 0 ? (
                    <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-faint)" }}>No evidence available to score this company.</p>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                        {components.map((c) => (
                            <div key={c.key}>
                                <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 5 }}>
                                    <span style={{ fontFamily: SERIF, fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>{c.label}</span>
                                    <span style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)" }}>
                                        weight {Math.round(c.effective_weight * 100)}%
                                    </span>
                                    <span style={{ marginLeft: "auto", fontFamily: SERIF, fontSize: 16, fontWeight: 600, color: colorFor(c.score) }}>
                                        {c.score}
                                    </span>
                                </div>
                                <div style={{ height: 6, background: "var(--rule)", borderRadius: 3, overflow: "hidden", marginBottom: 5 }}>
                                    <div style={{ width: `${c.score}%`, height: "100%", background: colorFor(c.score), transition: "width 0.8s ease-out" }} />
                                </div>
                                <p style={{ fontFamily: SANS, fontSize: 11, color: "var(--ink-2)", lineHeight: 1.5, margin: 0 }}>{c.detail}</p>
                            </div>
                        ))}
                    </div>
                )}

                {(note || aiNote) && (
                    <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--rule)" }}>
                        {note && <p style={{ fontFamily: SANS, fontSize: 11, color: "var(--ink-faint)", margin: 0 }}>{note}</p>}
                        {aiNote && (
                            <p style={{ fontFamily: MONO, fontSize: 10, color: "var(--ink-faint)", marginTop: note ? 4 : 0 }}>
                                AI red-flag scan: {aiNote}
                            </p>
                        )}
                    </div>
                )}
            </div>
        </section>
    );
}
