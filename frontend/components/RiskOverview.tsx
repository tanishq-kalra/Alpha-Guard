"use client";

import React from "react";

// ── Types ──

export interface RiskOverviewData {
    ticker: string;
    companyName: string;
    score: number;
    zone: "Safe" | "Gray" | "Distress";
    components: {
        label: string;
        value: number;
        weight: number;
    }[];
}

interface RiskOverviewProps {
    data?: RiskOverviewData | null;
}

const PLACEHOLDER: RiskOverviewData = {
    ticker: "—",
    companyName: "Search a ticker to begin",
    score: 0,
    zone: "Gray",
    components: [
        { label: "X1 — Working Capital / Total Assets", value: 0, weight: 1.2 },
        { label: "X2 — Retained Earnings / Total Assets", value: 0, weight: 1.4 },
        { label: "X3 — EBIT / Total Assets", value: 0, weight: 3.3 },
        { label: "X4 — Market Cap / Total Liabilities", value: 0, weight: 0.6 },
        { label: "X5 — Revenue / Total Assets", value: 0, weight: 1.0 },
    ],
};

const zoneConfig = {
    Safe: {
        color: "var(--green)",
        tint: "var(--green-tint)",
        border: "var(--green)",
        barFill: "var(--green)",
        label: "SAFE ZONE",
        description: "Low bankruptcy probability. Strong financial health.",
    },
    Gray: {
        color: "var(--amber)",
        tint: "var(--amber-tint)",
        border: "var(--amber)",
        barFill: "var(--amber)",
        label: "GRAY ZONE",
        description: "Moderate risk. Further analysis recommended.",
    },
    Distress: {
        color: "var(--red)",
        tint: "var(--red-tint)",
        border: "var(--red)",
        barFill: "var(--red)",
        label: "DISTRESS ZONE",
        description: "Elevated bankruptcy risk within 2 years.",
    },
};

export default function RiskOverview({ data }: RiskOverviewProps) {
    const d = data || PLACEHOLDER;
    const zone = zoneConfig[d.zone];
    const hasData = d.ticker !== "—";

    // Normalize score: 0→-2 range, 100→6+ range
    const gaugePercent = Math.min(100, Math.max(0, ((d.score + 2) / 8) * 100));

    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                overflow: "hidden",
                transition: "border-color 0.2s ease",
            }}
        >
            {/* Header */}
            <div
                style={{
                    padding: "16px 24px",
                    borderBottom: "1px solid var(--rule)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                        style={{
                            width: 30,
                            height: 30,
                            borderRadius: 4,
                            background: "var(--paper)",
                            border: "1px solid var(--rule)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        <svg
                            style={{ width: 14, height: 14, color: "var(--ink-faint)" }}
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                        </svg>
                    </div>
                    <div>
                        <h2
                            style={{
                                fontFamily: "var(--font-source-serif, Georgia, serif)",
                                fontSize: 15,
                                fontWeight: 600,
                                color: "var(--ink)",
                                margin: 0,
                            }}
                        >
                            Risk Overview
                        </h2>
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
                            Altman Z-Score Analysis
                        </p>
                    </div>
                </div>

                {/* Zone Badge */}
                {hasData && (
                    <span
                        style={{
                            padding: "4px 10px",
                            borderRadius: 3,
                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                            fontSize: 9,
                            fontWeight: 600,
                            letterSpacing: "0.14em",
                            textTransform: "uppercase",
                            background: zone.tint,
                            color: zone.color,
                            border: `1px solid ${zone.tint}`,
                        }}
                    >
                        {zone.label}
                    </span>
                )}
            </div>

            {/* Score Display */}
            <div style={{ padding: "32px 24px" }}>
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 32,
                    }}
                    className="md:flex-row"
                >
                    {/* Large Score */}
                    <div
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: 12,
                            paddingBottom: 0,
                        }}
                        className="md:pr-8 md:border-r md:border-ag-border md:pb-0"
                    >
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                fontSize: 9,
                                fontWeight: 500,
                                letterSpacing: "0.18em",
                                textTransform: "uppercase",
                                color: "var(--ink-faint)",
                                margin: 0,
                            }}
                        >
                            Z-Score
                        </p>
                        <p
                            style={{
                                fontFamily: "var(--font-source-serif, Georgia, serif)",
                                fontSize: 64,
                                fontWeight: 700,
                                lineHeight: 1,
                                letterSpacing: "-0.03em",
                                color: hasData ? zone.color : "var(--rule-strong)",
                                transition: "color 0.5s ease",
                                margin: 0,
                            }}
                        >
                            {hasData ? d.score.toFixed(2) : "—.——"}
                        </p>
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                fontSize: 12,
                                color: "var(--ink-2)",
                                textAlign: "center",
                                maxWidth: 200,
                                margin: 0,
                            }}
                        >
                            {hasData ? zone.description : "Enter a ticker symbol to calculate the Altman Z-Score."}
                        </p>

                        {/* Company label */}
                        <div
                            style={{
                                marginTop: 4,
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                padding: "6px 12px",
                                borderRadius: 4,
                                background: "var(--paper)",
                                border: "1px solid var(--rule)",
                            }}
                        >
                            <span
                                style={{
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: "var(--ink)",
                                }}
                            >
                                {d.ticker}
                            </span>
                            <span
                                style={{
                                    fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                    fontSize: 11,
                                    color: "var(--ink-faint)",
                                }}
                            >
                                {d.companyName}
                            </span>
                        </div>
                    </div>

                    {/* Score Gauge Bar + Component Breakdown */}
                    <div style={{ flex: 1, width: "100%" }}>
                        {/* Three-zone gauge */}
                        <div style={{ marginBottom: 24 }}>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    fontWeight: 500,
                                    letterSpacing: "0.12em",
                                    textTransform: "uppercase",
                                    color: "var(--ink-faint)",
                                    marginBottom: 6,
                                }}
                            >
                                <span style={{ color: "var(--red)" }}>Distress</span>
                                <span style={{ color: "var(--amber)" }}>Gray</span>
                                <span style={{ color: "var(--green)" }}>Safe</span>
                            </div>
                            {/* 3-zone tinted bar */}
                            <div
                                style={{
                                    position: "relative",
                                    height: 10,
                                    width: "100%",
                                    border: "1px solid var(--rule-strong)",
                                    borderRadius: 2,
                                    overflow: "hidden",
                                    display: "flex",
                                }}
                            >
                                <div style={{ width: "23.8%", background: "var(--red-tint)" }} />
                                <div style={{ width: "14.9%", background: "var(--amber-tint)" }} />
                                <div style={{ flex: 1, background: "var(--green-tint)" }} />

                                {/* Score tick marker */}
                                {hasData && (
                                    <div
                                        style={{
                                            position: "absolute",
                                            top: 0,
                                            bottom: 0,
                                            left: `${gaugePercent}%`,
                                            width: 2,
                                            background: "var(--ink)",
                                            transform: "translateX(-1px)",
                                            transition: "left 1s cubic-bezier(0.33,1,0.68,1)",
                                        }}
                                    />
                                )}
                            </div>
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    color: "var(--ink-faint)",
                                    marginTop: 4,
                                }}
                            >
                                <span>0.00</span>
                                <span>1.81</span>
                                <span>2.99</span>
                                <span>6.00+</span>
                            </div>
                        </div>

                        {/* Component Breakdown */}
                        <div>
                            <p
                                style={{
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    fontWeight: 500,
                                    letterSpacing: "0.15em",
                                    textTransform: "uppercase",
                                    color: "var(--ink-faint)",
                                    marginBottom: 12,
                                }}
                            >
                                Component Breakdown
                            </p>
                            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                                {d.components.map((comp, i) => {
                                    const weighted = comp.value * comp.weight;
                                    const barWidth = Math.min(100, Math.abs(weighted) * 20);
                                    const isGood = weighted >= 0;
                                    return (
                                        <div key={i}>
                                            <div
                                                style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "space-between",
                                                    marginBottom: 4,
                                                }}
                                            >
                                                <span
                                                    style={{
                                                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                        fontSize: 10,
                                                        color: "var(--ink-2)",
                                                    }}
                                                >
                                                    {comp.label}
                                                </span>
                                                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                                    <span
                                                        style={{
                                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                            fontSize: 9,
                                                            color: "var(--ink-faint)",
                                                        }}
                                                    >
                                                        {comp.value.toFixed(4)} × {comp.weight}
                                                    </span>
                                                    <span
                                                        style={{
                                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                            fontSize: 11,
                                                            fontWeight: 600,
                                                            color: "var(--ink)",
                                                            minWidth: 52,
                                                            textAlign: "right",
                                                        }}
                                                    >
                                                        {weighted.toFixed(4)}
                                                    </span>
                                                </div>
                                            </div>
                                            {/* Flat progress track */}
                                            <div
                                                style={{
                                                    height: 3,
                                                    width: "100%",
                                                    background: "var(--rule)",
                                                    borderRadius: 1,
                                                    overflow: "hidden",
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        height: "100%",
                                                        borderRadius: 1,
                                                        background: isGood ? "var(--green)" : "var(--amber)",
                                                        width: hasData ? `${barWidth}%` : "0%",
                                                        opacity: 0.7,
                                                        transition: "width 0.8s ease",
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div
                style={{
                    padding: "10px 24px",
                    borderTop: "1px solid var(--rule)",
                    background: "var(--paper)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                }}
            >
                <span
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 9,
                        color: "var(--ink-faint)",
                    }}
                >
                    Source: SEC EDGAR 10-K · Annual Filing
                </span>
                <span
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 9,
                        color: "var(--ink-faint)",
                    }}
                >
                    Model: Altman (1968) · Public Mfg.
                </span>
            </div>
        </div>
    );
}
