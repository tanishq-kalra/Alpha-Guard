"use client";

import React from "react";

interface TruthScoreGaugeProps {
    score: number | null;
    zone: string | null;
    deceptionAlert?: boolean;
    deceptionReason?: string;
    aiConfidenceScore?: number | null;
}

export default function TruthScoreGauge({
    score,
    zone,
    deceptionAlert = false,
    deceptionReason,
    aiConfidenceScore,
}: TruthScoreGaugeProps) {
    const isPending = score === null || zone === null;

    const radius = 80;
    const cx = 100;
    const cy = 100;
    const circumference = Math.PI * radius;
    const fillPercent = isPending ? 0 : (score ?? 0) / 100;
    const dashOffset = circumference * (1 - fillPercent);

    const zoneConfig: Record<string, { color: string; tint: string }> = {
        Credible:   { color: "var(--green)", tint: "var(--green-tint)" },
        Suspicious: { color: "var(--amber)", tint: "var(--amber-tint)" },
        Deceptive:  { color: "var(--red)",   tint: "var(--red-tint)"   },
    };

    const config = isPending
        ? { color: "var(--rule-strong)", tint: "var(--paper)" }
        : zoneConfig[zone!] || zoneConfig.Suspicious;

    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                padding: 24,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
            }}
        >
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, width: "100%" }}>
                <div
                    style={{
                        width: 28,
                        height: 28,
                        borderRadius: 4,
                        background: "var(--paper)",
                        border: "1px solid var(--rule)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                    }}
                >
                    <svg style={{ width: 13, height: 13, color: "var(--ink-faint)" }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
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
                        Truth Score
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
                        Credibility Index
                    </p>
                </div>
                {aiConfidenceScore != null && (
                    <span
                        style={{
                            marginLeft: "auto",
                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                            fontSize: 9,
                            color: "var(--ink-faint)",
                        }}
                    >
                        AI Conf: {(aiConfidenceScore * 100).toFixed(0)}%
                    </span>
                )}
            </div>

            {/* SVG Gauge Arc */}
            <div style={{ position: "relative", width: 200, height: 120, marginBottom: 16 }}>
                <svg viewBox="0 0 200 120" style={{ width: "100%", height: "100%" }}>
                    {/* Background arc */}
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke="var(--rule)"
                        strokeWidth="8"
                        strokeLinecap="round"
                    />
                    {/* Tinted zone underlays */}
                    {!isPending && (
                        <>
                            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="var(--red-tint)" strokeWidth="6" strokeLinecap="round" strokeDasharray={`${circumference * 0.33} ${circumference}`} />
                            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="var(--amber-tint)" strokeWidth="6" strokeLinecap="round"
                                strokeDasharray={`${circumference * 0.15} ${circumference}`}
                                strokeDashoffset={-circumference * 0.33}
                            />
                        </>
                    )}
                    {/* Filled arc */}
                    {!isPending && (
                        <path
                            d="M 20 100 A 80 80 0 0 1 180 100"
                            fill="none"
                            stroke={config.color}
                            strokeWidth="8"
                            strokeLinecap="round"
                            strokeDasharray={circumference}
                            strokeDashoffset={dashOffset}
                            style={{ transition: "stroke-dashoffset 1s ease-out" }}
                        />
                    )}
                    {/* Score number */}
                    {isPending ? (
                        <foreignObject x={cx - 15} y={cy - 20} width="30" height="30">
                            <div
                                style={{
                                    width: 20,
                                    height: 20,
                                    border: `2px solid var(--rule)`,
                                    borderTopColor: "var(--ink-faint)",
                                    borderRadius: "50%",
                                    animation: "spin 0.8s linear infinite",
                                    margin: "auto",
                                }}
                            />
                        </foreignObject>
                    ) : (
                        <text
                            x={cx}
                            y={cy - 8}
                            textAnchor="middle"
                            fontFamily="var(--font-source-serif, Georgia, serif)"
                            fontWeight="700"
                            fill={config.color}
                            fontSize="38"
                        >
                            {score}
                        </text>
                    )}
                    <text
                        x={cx}
                        y={cx + 12}
                        textAnchor="middle"
                        fontFamily="var(--font-ibm-plex-mono, monospace)"
                        fill="var(--ink-faint)"
                        fontSize="10"
                    >
                        {isPending ? "PENDING" : "/ 100"}
                    </text>
                </svg>
            </div>

            {/* Zone Badge */}
            <div
                style={{
                    padding: "5px 14px",
                    borderRadius: 3,
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    background: isPending ? "var(--paper)" : config.tint,
                    color: isPending ? "var(--ink-faint)" : config.color,
                    border: `1px solid ${isPending ? "var(--rule)" : config.tint}`,
                    marginBottom: 14,
                }}
            >
                {isPending ? "Pending Analysis" : zone}
            </div>

            {/* Zone scale bar */}
            <div style={{ display: "flex", alignItems: "center", gap: 2, width: "100%", maxWidth: 200, marginBottom: 8 }}>
                <div style={{ flex: 1, height: 3, borderRadius: 1, background: "var(--red-tint)", border: "1px solid var(--red)" }} />
                <div style={{ flex: 1, height: 3, borderRadius: 1, background: "var(--amber-tint)", border: "1px solid var(--amber)" }} />
                <div style={{ flex: 1, height: 3, borderRadius: 1, background: "var(--green-tint)", border: "1px solid var(--green)" }} />
            </div>
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    width: "100%",
                    maxWidth: 200,
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 8,
                    color: "var(--ink-faint)",
                }}
            >
                <span>Deceptive</span>
                <span>Suspicious</span>
                <span>Credible</span>
            </div>

            {/* Deception Alert — annotation style, not a toast */}
            {deceptionAlert && (
                <div
                    style={{
                        marginTop: 16,
                        width: "100%",
                        padding: "10px 14px",
                        background: "var(--red-tint)",
                        borderLeft: "4px solid var(--red)",
                        borderRadius: "0 4px 4px 0",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <span
                            style={{
                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                fontSize: 9,
                                fontWeight: 600,
                                letterSpacing: "0.14em",
                                textTransform: "uppercase",
                                color: "var(--red)",
                            }}
                        >
                            ⚠ Deception Alert
                        </span>
                    </div>
                    {deceptionReason && (
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                fontSize: 11,
                                color: "var(--ink-2)",
                                lineHeight: 1.5,
                                margin: 0,
                            }}
                        >
                            {deceptionReason}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
