"use client";

import React from "react";
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    CartesianGrid,
    ReferenceLine,
} from "recharts";

interface MonteCarloData {
    ticker: string;
    num_simulations: number;
    time_horizon_years: number;
    mean_final_revenue: number | null;
    median_final_revenue: number | null;
    percentile_5: number | null;
    percentile_95: number | null;
    probability_of_decline: number | null;
    initial_revenue: number | null;
    histogram: { range: string; count: number; pct: number; midpoint: number }[];
    sample_paths: { year: number; p5: number; p25: number; median: number; p75: number; p95: number; mean: number }[];
}

interface MonteCarloChartProps {
    data: MonteCarloData;
}

const formatRevenue = (value: number) => {
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
    if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                padding: "8px 12px",
                boxShadow: "var(--shadow-md)",
            }}
        >
            <p
                style={{
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 9,
                    color: "var(--ink-faint)",
                    marginBottom: 4,
                }}
            >
                Year {label}
            </p>
            {payload.map((entry: { name: string; value: number; color: string }, i: number) => (
                <p
                    key={i}
                    style={{
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 10,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        margin: "2px 0",
                    }}
                >
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: entry.color, display: "inline-block" }} />
                    <span style={{ color: "var(--ink-2)" }}>{entry.name}:</span>
                    <span style={{ color: "var(--ink)", fontWeight: 600 }}>{formatRevenue(entry.value)}</span>
                </p>
            ))}
        </div>
    );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const HistogramTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div
            style={{
                background: "var(--paper-2)",
                border: "1px solid var(--rule)",
                borderRadius: 4,
                padding: "8px 12px",
                boxShadow: "var(--shadow-md)",
            }}
        >
            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginBottom: 2 }}>{d.range}</p>
            <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, color: "var(--ink)" }}>
                <span style={{ color: "var(--blue)", fontWeight: 600 }}>{d.count}</span> simulations ({d.pct}%)
            </p>
        </div>
    );
};

export default function MonteCarloChart({ data }: MonteCarloChartProps) {
    const declinePercent = data.probability_of_decline
        ? (data.probability_of_decline * 100).toFixed(1)
        : "—";

    const declineColor =
        Number(declinePercent) > 30 ? "var(--red)" :
        Number(declinePercent) > 15 ? "var(--amber)" :
        "var(--green)";

    const statStyle: React.CSSProperties = {
        padding: "10px 14px",
        borderRadius: 4,
        background: "var(--paper)",
        border: "1px solid var(--rule)",
        textAlign: "center",
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Stats Row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }} className="grid-cols-2 sm:grid-cols-4">
                <div style={statStyle}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>Simulations</p>
                    <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 20, fontWeight: 600, color: "var(--ink)" }}>{data.num_simulations.toLocaleString()}</p>
                </div>
                <div style={statStyle}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>Mean Revenue</p>
                    <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 20, fontWeight: 600, color: "var(--green)" }}>
                        {data.mean_final_revenue ? formatRevenue(data.mean_final_revenue) : "—"}
                    </p>
                </div>
                <div style={statStyle}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>5th Percentile</p>
                    <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 20, fontWeight: 600, color: "var(--red)" }}>
                        {data.percentile_5 ? formatRevenue(data.percentile_5) : "—"}
                    </p>
                </div>
                <div style={statStyle}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: 4 }}>P(Decline &gt;20%)</p>
                    <p style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 20, fontWeight: 600, color: declineColor }}>
                        {declinePercent}%
                    </p>
                </div>
            </div>

            {/* Charts Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }} className="grid-cols-1 lg:grid-cols-2">
                {/* Revenue Path Fan Chart */}
                {data.sample_paths.length > 0 && (
                    <div
                        style={{
                            padding: 16,
                            borderRadius: 4,
                            background: "var(--paper)",
                            border: "1px solid var(--rule)",
                        }}
                    >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                            <h4 style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink)" }}>
                                Revenue Forecast — Percentile Bands
                            </h4>
                            <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>{data.time_horizon_years}Y horizon</span>
                        </div>
                        <ResponsiveContainer width="100%" height={220}>
                            <AreaChart data={data.sample_paths} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                                <defs>
                                    <linearGradient id="bandOuter" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#1D3B63" stopOpacity={0.12} />
                                        <stop offset="100%" stopColor="#1D3B63" stopOpacity={0.02} />
                                    </linearGradient>
                                    <linearGradient id="bandInner" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#1E4B3B" stopOpacity={0.18} />
                                        <stop offset="100%" stopColor="#1E4B3B" stopOpacity={0.04} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--rule)" />
                                <XAxis
                                    dataKey="year"
                                    tick={{ fill: "var(--ink-faint)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono, monospace)" }}
                                    tickFormatter={(v) => `Y${v}`}
                                    axisLine={{ stroke: "var(--rule)" }}
                                    tickLine={{ stroke: "var(--rule)" }}
                                />
                                <YAxis
                                    tick={{ fill: "var(--ink-faint)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono, monospace)" }}
                                    tickFormatter={formatRevenue}
                                    axisLine={{ stroke: "var(--rule)" }}
                                    tickLine={{ stroke: "var(--rule)" }}
                                    width={60}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Area type="monotone" dataKey="p95" stroke="none" fill="url(#bandOuter)" name="P95" />
                                <Area type="monotone" dataKey="p5" stroke="none" fill="var(--paper)" name="P5" />
                                <Area type="monotone" dataKey="p75" stroke="none" fill="url(#bandInner)" name="P75" />
                                <Area type="monotone" dataKey="p25" stroke="none" fill="var(--paper)" name="P25" />
                                <Area
                                    type="monotone"
                                    dataKey="median"
                                    stroke="var(--green)"
                                    strokeWidth={2}
                                    fill="none"
                                    name="Median"
                                    dot={{ fill: "var(--green)", r: 2, strokeWidth: 0 }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="mean"
                                    stroke="var(--blue)"
                                    strokeWidth={1.5}
                                    strokeDasharray="4 4"
                                    fill="none"
                                    name="Mean"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                )}

                {/* Distribution Histogram */}
                {data.histogram.length > 0 && (
                    <div
                        style={{
                            padding: 16,
                            borderRadius: 4,
                            background: "var(--paper)",
                            border: "1px solid var(--rule)",
                        }}
                    >
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                            <h4 style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--ink)" }}>
                                Final Revenue Distribution
                            </h4>
                            <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>{data.num_simulations.toLocaleString()} paths</span>
                        </div>
                        <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={data.histogram} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--rule)" vertical={false} />
                                <XAxis
                                    dataKey="range"
                                    tick={{ fill: "var(--ink-faint)", fontSize: 8, fontFamily: "var(--font-ibm-plex-mono, monospace)" }}
                                    axisLine={{ stroke: "var(--rule)" }}
                                    tickLine={{ stroke: "var(--rule)" }}
                                    interval="preserveStartEnd"
                                    angle={-35}
                                    textAnchor="end"
                                    height={50}
                                />
                                <YAxis
                                    tick={{ fill: "var(--ink-faint)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono, monospace)" }}
                                    axisLine={{ stroke: "var(--rule)" }}
                                    tickLine={{ stroke: "var(--rule)" }}
                                    width={40}
                                />
                                <Tooltip content={<HistogramTooltip />} />
                                {data.initial_revenue && (
                                    <ReferenceLine
                                        x={data.histogram.findIndex((h) => h.midpoint >= (data.initial_revenue || 0))}
                                        stroke="var(--amber)"
                                        strokeDasharray="4 3"
                                        label={{ value: "Current", fill: "var(--amber)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono, monospace)" }}
                                    />
                                )}
                                <Bar
                                    dataKey="count"
                                    fill="var(--blue)"
                                    fillOpacity={0.5}
                                    radius={[2, 2, 0, 0]}
                                    name="Simulations"
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </div>
        </div>
    );
}
