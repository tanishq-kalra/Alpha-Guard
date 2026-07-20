"use client";

import React from "react";

interface RadarDataPoint {
    label: string;
    financial: number; // 0-100
    narrative: number; // 0-100
}

interface RiskRadarProps {
    data?: RadarDataPoint[];
}

const DEFAULT_DATA: RadarDataPoint[] = [
    { label: "Financial Health", financial: 85, narrative: 60 },
    { label: "Hedging Level",    financial: 30, narrative: 72 },
    { label: "Evasion Level",    financial: 20, narrative: 55 },
    { label: "Sentiment Align",  financial: 90, narrative: 45 },
    { label: "Truth Score",      financial: 80, narrative: 52 },
];

export default function RiskRadar({ data = DEFAULT_DATA }: RiskRadarProps) {
    const cx = 150;
    const cy = 150;
    const maxRadius = 110;
    const levels = 4;
    const numPoints = data.length;
    const angleStep = (2 * Math.PI) / numPoints;
    const startAngle = -Math.PI / 2;

    const getPoint = (index: number, value: number): [number, number] => {
        const angle = startAngle + index * angleStep;
        const r = (value / 100) * maxRadius;
        return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
    };

    const getPolygonPath = (values: number[]): string => {
        const points = values.map((v, i) => getPoint(i, v));
        return points.map((p) => `${p[0]},${p[1]}`).join(" ");
    };

    const gridRings = Array.from({ length: levels }, (_, i) => {
        const r = ((i + 1) / levels) * maxRadius;
        const points = Array.from({ length: numPoints }, (_, j) => {
            const angle = startAngle + j * angleStep;
            return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
        });
        return points.join(" ");
    });

    const axisLines = Array.from({ length: numPoints }, (_, i) => {
        const angle = startAngle + i * angleStep;
        return { x2: cx + maxRadius * Math.cos(angle), y2: cy + maxRadius * Math.sin(angle) };
    });

    const labelPositions = data.map((d, i) => {
        const angle = startAngle + i * angleStep;
        const labelR = maxRadius + 24;
        return { x: cx + labelR * Math.cos(angle), y: cy + labelR * Math.sin(angle), label: d.label };
    });

    const financialValues = data.map((d) => d.financial);
    const narrativeValues = data.map((d) => d.narrative);

    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                padding: 24,
            }}
        >
            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
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
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                        <path d="M2 12h20" />
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
                        Risk Radar
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
                        Financial vs Narrative Risk
                    </p>
                </div>
            </div>

            {/* SVG Radar */}
            <div style={{ display: "flex", justifyContent: "center" }}>
                <svg viewBox="0 0 300 300" style={{ width: "100%", maxWidth: 340 }}>
                    {/* Grid rings — rule color */}
                    {gridRings.map((points, i) => (
                        <polygon
                            key={`ring-${i}`}
                            points={points}
                            fill={i % 2 === 0 ? "var(--paper)" : "var(--paper-2)"}
                            stroke="var(--rule)"
                            strokeWidth="1"
                        />
                    ))}

                    {/* Axis lines — rule-strong */}
                    {axisLines.map((line, i) => (
                        <line
                            key={`axis-${i}`}
                            x1={cx}
                            y1={cy}
                            x2={line.x2}
                            y2={line.y2}
                            stroke="var(--rule-strong)"
                            strokeWidth="0.8"
                        />
                    ))}

                    {/* Financial polygon — green muted fill */}
                    <polygon
                        points={getPolygonPath(financialValues)}
                        fill="var(--green-tint)"
                        fillOpacity={0.7}
                        stroke="var(--green)"
                        strokeWidth="1.5"
                    />

                    {/* Narrative polygon — blue muted fill, dashed */}
                    <polygon
                        points={getPolygonPath(narrativeValues)}
                        fill="var(--blue-tint)"
                        fillOpacity={0.5}
                        stroke="var(--blue)"
                        strokeWidth="1.5"
                        strokeDasharray="4 2"
                    />

                    {/* Data points — Financial */}
                    {financialValues.map((v, i) => {
                        const [px, py] = getPoint(i, v);
                        return (
                            <circle key={`fin-${i}`} cx={px} cy={py} r="3" fill="var(--green)" stroke="var(--paper-2)" strokeWidth="1.5" />
                        );
                    })}

                    {/* Data points — Narrative */}
                    {narrativeValues.map((v, i) => {
                        const [px, py] = getPoint(i, v);
                        return (
                            <circle key={`nar-${i}`} cx={px} cy={py} r="3" fill="var(--blue)" stroke="var(--paper-2)" strokeWidth="1.5" />
                        );
                    })}

                    {/* Axis labels — mono, ink-2 */}
                    {labelPositions.map((lp, i) => (
                        <text
                            key={`label-${i}`}
                            x={lp.x}
                            y={lp.y}
                            textAnchor="middle"
                            dominantBaseline="central"
                            fill="var(--ink-2)"
                            fontSize="8"
                            fontFamily="var(--font-ibm-plex-mono, monospace)"
                        >
                            {lp.label}
                        </text>
                    ))}
                </svg>
            </div>

            {/* Legend */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 24, marginTop: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 16, height: 2, background: "var(--green)", borderRadius: 1 }} />
                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-2)" }}>Financial Risk</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <svg width="16" height="4">
                        <line x1="0" y1="2" x2="16" y2="2" stroke="var(--blue)" strokeWidth="2" strokeDasharray="4 2" />
                    </svg>
                    <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-2)" }}>Narrative Risk</span>
                </div>
            </div>
        </div>
    );
}
