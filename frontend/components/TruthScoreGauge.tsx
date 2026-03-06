"use client";

import React from "react";

interface TruthScoreGaugeProps {
    score: number; // 0-100
    zone: string;  // "Credible" | "Suspicious" | "Deceptive"
    deceptionAlert?: boolean;
    deceptionReason?: string;
}

export default function TruthScoreGauge({
    score,
    zone,
    deceptionAlert = false,
    deceptionReason,
}: TruthScoreGaugeProps) {
    // SVG arc parameters
    const radius = 80;
    const cx = 100;
    const cy = 100;
    const circumference = Math.PI * radius; // Half circle
    const fillPercent = score / 100;
    const dashOffset = circumference * (1 - fillPercent);

    // Color based on zone
    const zoneConfig: Record<string, { color: string; glow: string; bg: string }> = {
        Credible: { color: "#00e67a", glow: "drop-shadow(0 0 12px rgba(0,230,122,0.4))", bg: "bg-ag-green/8" },
        Suspicious: { color: "#f59e0b", glow: "drop-shadow(0 0 12px rgba(245,158,11,0.4))", bg: "bg-ag-amber/8" },
        Deceptive: { color: "#ef4444", glow: "drop-shadow(0 0 12px rgba(239,68,68,0.4))", bg: "bg-ag-red/8" },
    };

    const config = zoneConfig[zone] || zoneConfig.Suspicious;

    return (
        <div className="card-glass p-6 flex flex-col items-center">
            {/* Header */}
            <div className="flex items-center gap-2 mb-4 w-full">
                <div className="w-8 h-8 rounded-lg bg-ag-surface flex items-center justify-center">
                    <svg className="w-4 h-4 text-ag-text2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                </div>
                <div>
                    <h3 className="text-sm font-semibold text-ag-text">Truth Score</h3>
                    <p className="text-[10px] font-mono text-ag-muted uppercase tracking-wider">
                        CREDIBILITY INDEX
                    </p>
                </div>
            </div>

            {/* SVG Gauge */}
            <div className="relative w-[200px] h-[120px] mb-4">
                <svg
                    viewBox="0 0 200 120"
                    className="w-full h-full"
                    style={{ filter: config.glow }}
                >
                    {/* Background arc */}
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke="var(--border-dim)"
                        strokeWidth="8"
                        strokeLinecap="round"
                    />
                    {/* Filled arc */}
                    <path
                        d="M 20 100 A 80 80 0 0 1 180 100"
                        fill="none"
                        stroke={config.color}
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={dashOffset}
                        className="transition-all duration-1000 ease-out"
                    />
                    {/* Score text */}
                    <text
                        x={cx}
                        y={cy - 10}
                        textAnchor="middle"
                        className="font-mono font-bold"
                        fill={config.color}
                        fontSize="36"
                    >
                        {score}
                    </text>
                    <text
                        x={cx}
                        y={cy + 12}
                        textAnchor="middle"
                        className="font-mono"
                        fill="var(--text-muted)"
                        fontSize="10"
                    >
                        / 100
                    </text>
                </svg>
            </div>

            {/* Zone Badge */}
            <div
                className={`
          px-4 py-1.5 rounded-full text-xs font-mono font-semibold uppercase tracking-widest
          border mb-3
          ${zone === "Credible" ? "text-ag-green bg-ag-green/10 border-ag-green/30" : ""}
          ${zone === "Suspicious" ? "text-ag-amber bg-ag-amber/10 border-ag-amber/30" : ""}
          ${zone === "Deceptive" ? "text-ag-red bg-ag-red/10 border-ag-red/30" : ""}
        `}
            >
                {zone}
            </div>

            {/* Zone scale */}
            <div className="flex items-center gap-1 w-full max-w-[200px] mb-4">
                <div className="flex-1 h-1 rounded-full bg-ag-red/40" />
                <div className="flex-1 h-1 rounded-full bg-ag-amber/40" />
                <div className="flex-1 h-1 rounded-full bg-ag-green/40" />
            </div>
            <div className="flex justify-between w-full max-w-[200px] text-[9px] font-mono text-ag-muted">
                <span>Deceptive</span>
                <span>Suspicious</span>
                <span>Credible</span>
            </div>

            {/* Deception Alert */}
            {deceptionAlert && (
                <div className="mt-4 w-full p-3 rounded-lg bg-ag-red/8 border border-ag-red/20">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-ag-red animate-pulse" />
                        <span className="text-xs font-mono font-semibold text-ag-red uppercase tracking-wider">
                            Deception Alert
                        </span>
                    </div>
                    {deceptionReason && (
                        <p className="text-[11px] text-ag-text2 leading-relaxed">
                            {deceptionReason}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
