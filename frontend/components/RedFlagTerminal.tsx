"use client";

import React from "react";

interface RedFlagEntry {
    sentence: string;
    category: string;
    severity: number; // 1-10
    explanation: string;
}

interface RedFlagTerminalProps {
    flags?: RedFlagEntry[];
}

const MOCK_FLAGS: RedFlagEntry[] = [
    {
        sentence:
            "We believe our current liquidity position is adequate to meet foreseeable obligations.",
        category: "hedging",
        severity: 7,
        explanation:
            "Uses 'believe' and 'foreseeable' — classic hedging language that avoids commitment. Financially distressed companies frequently use this phrasing to downplay liquidity concerns.",
    },
    {
        sentence:
            "The impact of current market conditions on our operations cannot be fully determined at this time.",
        category: "evasion",
        severity: 8,
        explanation:
            "Deliberately vague — 'cannot be fully determined' evades disclosure of known material impacts. SEC guidance requires more specific risk quantification.",
    },
    {
        sentence:
            "Management remains optimistic about long-term growth prospects despite near-term headwinds.",
        category: "sentiment_gap",
        severity: 9,
        explanation:
            "Narrative diverges from financial reality: Z-Score indicates Distress Zone while management projects bullish outlook. Possible misrepresentation.",
    },
    {
        sentence:
            "Certain forward-looking statements are subject to risks and uncertainties that could cause actual results to differ materially.",
        category: "hedging",
        severity: 5,
        explanation:
            "Standard safe-harbor language, but the density of such disclaimers in this filing exceeds industry norms by 2.3×, suggesting intentional obfuscation.",
    },
    {
        sentence:
            "We may need to seek additional financing, although there can be no assurance such financing will be available on favorable terms.",
        category: "evasion",
        severity: 8,
        explanation:
            "Buried admission of potential financing difficulties. 'No assurance' combined with 'may need' downplays what could be a critical going-concern risk.",
    },
];

const severityConfig = (severity: number) => {
    if (severity >= 8) return {
        label: "CRITICAL",
        color: "var(--red)",
        tint: "var(--red-tint)",
        leftBorder: "var(--red)",
    };
    if (severity >= 5) return {
        label: "WARNING",
        color: "var(--amber)",
        tint: "var(--amber-tint)",
        leftBorder: "var(--amber)",
    };
    return {
        label: "NOTICE",
        color: "var(--blue)",
        tint: "var(--blue-tint)",
        leftBorder: "var(--blue)",
    };
};

const categoryLabels: Record<string, string> = {
    hedging: "HEDGING",
    evasion: "EVASION",
    sentiment_gap: "SENTIMENT GAP",
    inconsistency: "INCONSISTENCY",
};

export default function RedFlagTerminal({ flags = MOCK_FLAGS }: RedFlagTerminalProps) {
    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                overflow: "hidden",
            }}
        >
            {/* Document header */}
            <div
                style={{
                    padding: "14px 20px",
                    borderBottom: "1px solid var(--rule)",
                    background: "var(--paper)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                        style={{
                            width: 28,
                            height: 28,
                            borderRadius: 4,
                            background: "var(--paper-2)",
                            border: "1px solid var(--rule)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        <svg style={{ width: 13, height: 13 }} viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                            <line x1="12" y1="9" x2="12" y2="13" />
                            <line x1="12" y1="17" x2="12.01" y2="17" />
                        </svg>
                    </div>
                    <div>
                        <h3
                            style={{
                                fontFamily: "var(--font-source-serif, Georgia, serif)",
                                fontSize: 14,
                                fontWeight: 600,
                                color: "var(--ink)",
                                margin: 0,
                            }}
                        >
                            Forensic Evidence Log
                        </h3>
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                fontSize: 9,
                                fontWeight: 500,
                                letterSpacing: "0.14em",
                                textTransform: "uppercase",
                                color: "var(--ink-faint)",
                                margin: 0,
                            }}
                        >
                            Linguistic Stress Detection · 10-K Filing
                        </p>
                    </div>
                </div>
                <span
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 9,
                        color: flags.length > 0 ? "var(--red)" : "var(--ink-faint)",
                        fontWeight: flags.length > 0 ? 600 : 400,
                    }}
                >
                    {flags.length} flag{flags.length !== 1 ? "s" : ""} detected
                </span>
            </div>

            {/* Evidence log body */}
            <div style={{ padding: 16, maxHeight: 520, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
                {flags.map((flag, i) => {
                    const sev = severityConfig(flag.severity);
                    const timestamp = `${String(21 + Math.floor(i / 60)).padStart(2, "0")}:${String((i * 7 + 14) % 60).padStart(2, "0")}:${String((i * 13 + 42) % 60).padStart(2, "0")}`;

                    return (
                        <div
                            key={i}
                            style={{
                                background: "var(--paper-2)",
                                border: "1px solid var(--rule)",
                                borderLeft: `4px solid ${sev.leftBorder}`,
                                borderRadius: "0 4px 4px 0",
                                padding: "14px 16px",
                            }}
                        >
                            {/* Meta row */}
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                    marginBottom: 10,
                                    flexWrap: "wrap",
                                }}
                            >
                                <span
                                    style={{
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 9,
                                        color: "var(--ink-faint)",
                                    }}
                                >
                                    [{timestamp}]
                                </span>
                                <span
                                    style={{
                                        padding: "2px 7px",
                                        borderRadius: 3,
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 9,
                                        fontWeight: 600,
                                        letterSpacing: "0.1em",
                                        textTransform: "uppercase",
                                        background: sev.tint,
                                        color: sev.color,
                                    }}
                                >
                                    {sev.label}
                                </span>
                                <span
                                    style={{
                                        padding: "2px 7px",
                                        borderRadius: 3,
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 9,
                                        fontWeight: 500,
                                        letterSpacing: "0.1em",
                                        textTransform: "uppercase",
                                        background: "var(--paper)",
                                        color: "var(--ink-2)",
                                        border: "1px solid var(--rule)",
                                    }}
                                >
                                    {categoryLabels[flag.category] || flag.category.toUpperCase()}
                                </span>
                                <span
                                    style={{
                                        marginLeft: "auto",
                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                        fontSize: 9,
                                        color: "var(--ink-faint)",
                                    }}
                                >
                                    SEV {flag.severity}/10
                                </span>
                            </div>

                            {/* Filing excerpt — serif italic */}
                            <p
                                style={{
                                    fontFamily: "var(--font-source-serif, Georgia, serif)",
                                    fontStyle: "italic",
                                    fontSize: 13,
                                    color: "var(--ink)",
                                    lineHeight: 1.6,
                                    marginBottom: 10,
                                    margin: "0 0 10px 0",
                                }}
                            >
                                &quot;{flag.sentence}&quot;
                            </p>

                            {/* Hairline divider */}
                            <div style={{ height: 1, background: "var(--rule)", marginBottom: 10 }} />

                            {/* Analyst note */}
                            <p
                                style={{
                                    fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                    fontSize: 11,
                                    color: "var(--ink-2)",
                                    lineHeight: 1.55,
                                    margin: 0,
                                }}
                            >
                                {flag.explanation}
                            </p>
                        </div>
                    );
                })}

                {/* Log footer */}
                <div
                    style={{
                        padding: "8px 4px",
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 10,
                        color: "var(--ink-faint)",
                        borderTop: "1px solid var(--rule)",
                        marginTop: 4,
                    }}
                >
                    Analysis complete · {flags.length} finding{flags.length !== 1 ? "s" : ""} recorded
                </div>
            </div>
        </div>
    );
}
