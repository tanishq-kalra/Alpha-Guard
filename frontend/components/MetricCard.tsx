"use client";

import React from "react";

interface MetricCardProps {
    label: string;
    value: string;
    subtitle?: string;
    trend?: "up" | "down" | "neutral";
    accentColor?: "green" | "amber" | "red" | "cyan" | "blue";
}

const colorMap = {
    green: { text: "var(--green)",  tint: "var(--green-tint)" },
    amber: { text: "var(--amber)",  tint: "var(--amber-tint)" },
    red:   { text: "var(--red)",    tint: "var(--red-tint)"   },
    cyan:  { text: "var(--blue)",   tint: "var(--blue-tint)"  }, // cyan → blue in new palette
    blue:  { text: "var(--blue)",   tint: "var(--blue-tint)"  },
};

export default function MetricCard({
    label,
    value,
    subtitle,
    trend = "neutral",
    accentColor = "green",
}: MetricCardProps) {
    const colors = colorMap[accentColor] ?? colorMap.green;
    const isNegative = trend === "down";
    const isPositive = trend === "up";

    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                padding: "18px 20px",
                display: "flex",
                flexDirection: "column",
                gap: 6,
                transition: "box-shadow 0.15s ease, transform 0.15s ease",
                cursor: "default",
            }}
            onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-md)";
                (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = "";
                (e.currentTarget as HTMLElement).style.transform = "";
            }}
        >
            {/* Eyebrow label + trend indicator */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 9,
                        fontWeight: 500,
                        letterSpacing: "0.15em",
                        textTransform: "uppercase",
                        color: "var(--ink-faint)",
                    }}
                >
                    {label}
                </span>
                {trend !== "neutral" && (
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 3,
                            padding: "2px 6px",
                            borderRadius: 3,
                            background: isPositive ? "var(--green-tint)" : "var(--red-tint)",
                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                            fontSize: 9,
                            fontWeight: 600,
                            color: isPositive ? "var(--green)" : "var(--red)",
                        }}
                    >
                        <svg
                            style={{
                                width: 10,
                                height: 10,
                                transform: isNegative ? "rotate(180deg)" : "none",
                            }}
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2.5}
                        >
                            <polyline points="18 15 12 9 6 15" />
                        </svg>
                        {isPositive ? "+" : "−"}
                    </div>
                )}
            </div>

            {/* Large serif value */}
            <p
                style={{
                    fontFamily: "var(--font-source-serif, Georgia, serif)",
                    fontSize: 28,
                    fontWeight: 600,
                    lineHeight: 1,
                    letterSpacing: "-0.02em",
                    color: colors.text,
                    margin: 0,
                }}
            >
                {value}
            </p>

            {/* Formula / subtitle */}
            {subtitle && (
                <p
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 10,
                        color: "var(--ink-faint)",
                        margin: 0,
                        lineHeight: 1.4,
                    }}
                >
                    {subtitle}
                </p>
            )}

            {/* Inline SVG sparkline — decorative, represents trending data */}
            <div style={{ marginTop: 8 }}>
                <svg
                    viewBox="0 0 80 16"
                    style={{ width: "100%", height: 14, display: "block" }}
                    preserveAspectRatio="none"
                >
                    <polyline
                        points={
                            isPositive
                                ? "0,12 10,10 20,11 30,8 40,9 50,6 60,5 70,3 80,2"
                                : isNegative
                                ? "0,4 10,5 20,4 30,7 40,6 50,9 60,10 70,12 80,14"
                                : "0,8 10,7 20,9 30,8 40,7 50,9 60,8 70,7 80,8"
                        }
                        fill="none"
                        stroke={colors.text}
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        opacity="0.5"
                        vectorEffect="non-scaling-stroke"
                    />
                </svg>
            </div>
        </div>
    );
}
