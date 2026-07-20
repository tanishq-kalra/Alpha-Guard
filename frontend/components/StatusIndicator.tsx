"use client";

import React, { useState, useEffect } from "react";
import { healthCheck } from "@/lib/api";

export default function StatusIndicator() {
    const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
    const [flagCount, setFlagCount] = useState(0);
    const [version, setVersion] = useState("");

    useEffect(() => {
        let mounted = true;

        const checkHealth = async () => {
            try {
                const health = await healthCheck();
                if (mounted) {
                    setBackendStatus("connected");
                    setVersion(health.version);
                }
            } catch {
                if (mounted) setBackendStatus("disconnected");
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 30000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    useEffect(() => {
        const handler = (e: Event) => {
            const detail = (e as CustomEvent).detail;
            if (typeof detail?.flagCount === "number") {
                setFlagCount(detail.flagCount);
            }
        };
        window.addEventListener("alpha-guard:flags", handler);
        return () => window.removeEventListener("alpha-guard:flags", handler);
    }, []);

    const dotColor = {
        checking:     "var(--amber)",
        connected:    "var(--green)",
        disconnected: "var(--red)",
    }[backendStatus];

    const statusText = {
        checking:     "Connecting...",
        connected:    `Online${version ? ` · v${version}` : ""}`,
        disconnected: "Offline",
    }[backendStatus];

    return (
        <div
            style={{
                position: "fixed",
                bottom: 16,
                left: 16,
                zIndex: 50,
                display: "flex",
                alignItems: "center",
                gap: 8,
            }}
        >
            {/* Backend status pill */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 7,
                    padding: "5px 10px",
                    borderRadius: 4,
                    background: "var(--paper-2)",
                    border: "1px solid var(--rule)",
                    boxShadow: "var(--shadow)",
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 9,
                }}
            >
                <div
                    style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: dotColor,
                        flexShrink: 0,
                    }}
                />
                <span style={{ color: "var(--ink-faint)" }}>{statusText}</span>
            </div>

            {/* Flag count badge */}
            {flagCount > 0 && (
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        padding: "5px 10px",
                        borderRadius: 4,
                        background: "var(--red-tint)",
                        border: "1px solid var(--red-tint)",
                        borderLeft: "3px solid var(--red)",
                        boxShadow: "var(--shadow)",
                        fontFamily: "var(--font-ibm-plex-mono, monospace)",
                        fontSize: 9,
                        fontWeight: 600,
                        color: "var(--red)",
                    }}
                >
                    {flagCount} FLAG{flagCount !== 1 ? "S" : ""}
                </div>
            )}
        </div>
    );
}
