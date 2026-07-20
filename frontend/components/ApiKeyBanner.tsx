"use client";

import React, { useState } from "react";

interface ApiKeyBannerProps {
    show: boolean;
}

export default function ApiKeyBanner({ show }: ApiKeyBannerProps) {
    const [dismissed, setDismissed] = useState(false);

    if (!show || dismissed) return null;

    return (
        <div style={{ width: "100%", maxWidth: 1480, margin: "0 auto", padding: "0 24px 16px" }}>
            <div
                style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 12,
                    background: "var(--amber-tint)",
                    borderLeft: "4px solid var(--amber)",
                    borderRadius: "0 4px 4px 0",
                    padding: "10px 14px",
                }}
            >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10, minWidth: 0 }}>
                    <svg
                        style={{ width: 14, height: 14, flexShrink: 0, marginTop: 1, color: "var(--amber)" }}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                        <line x1="12" y1="9" x2="12" y2="13" />
                        <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <div style={{ minWidth: 0 }}>
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                fontSize: 10,
                                fontWeight: 600,
                                letterSpacing: "0.12em",
                                textTransform: "uppercase",
                                color: "var(--amber)",
                                margin: 0,
                            }}
                        >
                            AI Analysis Unavailable
                        </p>
                        <p
                            style={{
                                fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                fontSize: 12,
                                color: "var(--ink-2)",
                                marginTop: 3,
                                margin: "3px 0 0",
                            }}
                        >
                            GEMINI_API_KEY not configured — forensic analysis will use heuristic mode only.{" "}
                            <a
                                href="https://aistudio.google.com/app/apikey"
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: "var(--amber)", textDecoration: "underline", textUnderlineOffset: 2 }}
                            >
                                Get an API key →
                            </a>
                        </p>
                    </div>
                </div>
                <button
                    id="banner-dismiss"
                    onClick={() => setDismissed(true)}
                    aria-label="Dismiss"
                    style={{
                        flexShrink: 0,
                        padding: 4,
                        borderRadius: 4,
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--ink-faint)",
                        lineHeight: 0,
                    }}
                >
                    <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
