"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
    { label: "Dashboard", href: "/" },
    { label: "Forensic", href: "/forensic" },
    { label: "Reports", href: "/reports" },
    { label: "Architect", href: "/about" },
];

/** Polygraph / seismograph signature line — one-time decorative element,
 *  appears ONLY here beneath the masthead. Do not reuse elsewhere. */
function TruthLine() {
    return (
        <div aria-hidden="true" style={{ overflow: "hidden", lineHeight: 0 }}>
            <svg
                viewBox="0 0 1440 20"
                preserveAspectRatio="none"
                style={{ width: "100%", height: 20, display: "block" }}
                xmlns="http://www.w3.org/2000/svg"
            >
                {/* Base seismograph line */}
                <polyline
                    points="0,10 120,10 180,10 220,4 240,16 260,2 280,18 300,10 400,10 520,10 560,7 580,13 600,10 700,10 760,10 800,5 820,15 840,8 860,12 880,10 1000,10 1100,10 1160,8 1180,12 1200,10 1440,10"
                    fill="none"
                    stroke="var(--rule-strong)"
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                />
                {/* Green "spike" accent dots — credibility pulse markers */}
                <circle cx="260" cy="2"  r="2" fill="var(--green)" opacity="0.7" />
                <circle cx="800" cy="5"  r="2" fill="var(--green)" opacity="0.6" />
                <circle cx="1160" cy="8" r="1.5" fill="var(--green)" opacity="0.5" />
            </svg>
        </div>
    );
}

export default function DashboardHeader() {
    const pathname = usePathname();

    return (
        <header
            className="w-full sticky top-0 z-50"
            style={{
                background: "rgba(248,247,243,0.92)",
                backdropFilter: "blur(12px)",
                WebkitBackdropFilter: "blur(12px)",
            }}
        >
            <div
                style={{ borderBottom: "1px solid var(--rule)" }}
            >
                <div className="max-w-[1480px] mx-auto px-6 h-14 flex items-center justify-between">
                    {/* Logo / Wordmark */}
                    <Link href="/" className="flex items-center gap-3 group" id="header-logo">
                        {/* Solid green square mark */}
                        <div
                            className="flex items-center justify-center flex-shrink-0"
                            style={{
                                width: 28,
                                height: 28,
                                background: "var(--green)",
                                borderRadius: 4,
                            }}
                        >
                            <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                style={{ width: 14, height: 14 }}
                                stroke="white"
                                strokeWidth={2}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                                <path d="M9 12l2 2 4-4" />
                            </svg>
                        </div>
                        {/* Wordmark */}
                        <div>
                            <h1
                                style={{
                                    fontFamily: "var(--font-source-serif, Georgia, serif)",
                                    fontSize: 15,
                                    fontWeight: 600,
                                    color: "var(--ink)",
                                    lineHeight: 1,
                                    letterSpacing: "-0.01em",
                                }}
                            >
                                Alpha-Guard
                            </h1>
                            <p
                                style={{
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    fontWeight: 500,
                                    color: "var(--ink-faint)",
                                    letterSpacing: "0.18em",
                                    textTransform: "uppercase",
                                    marginTop: 2,
                                }}
                            >
                                Forensic Research Division
                            </p>
                        </div>
                    </Link>

                    {/* Nav + Status */}
                    <div className="flex items-center gap-4">
                        <nav className="hidden md:flex items-center gap-1" role="navigation" aria-label="Main navigation">
                            {NAV_ITEMS.map((item) => {
                                const isActive =
                                    item.href === "/"
                                        ? pathname === "/"
                                        : pathname.startsWith(item.href) && item.href !== "#";

                                return (
                                    <Link
                                        key={item.label}
                                        href={item.href}
                                        id={`nav-${item.label.toLowerCase()}`}
                                        style={{
                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                            fontSize: 10,
                                            fontWeight: 600,
                                            letterSpacing: "0.1em",
                                            textTransform: "uppercase",
                                            padding: "5px 12px",
                                            borderRadius: 4,
                                            transition: "background 0.15s ease, color 0.15s ease",
                                            background: isActive ? "var(--green)" : "transparent",
                                            color: isActive ? "#ffffff" : "var(--ink-2)",
                                            border: isActive ? "1px solid var(--green)" : "1px solid transparent",
                                            textDecoration: "none",
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isActive) {
                                                (e.target as HTMLElement).style.color = "var(--ink)";
                                                (e.target as HTMLElement).style.borderColor = "var(--rule-strong)";
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isActive) {
                                                (e.target as HTMLElement).style.color = "var(--ink-2)";
                                                (e.target as HTMLElement).style.borderColor = "transparent";
                                            }
                                        }}
                                    >
                                        {item.label}
                                    </Link>
                                );
                            })}
                        </nav>

                        {/* Live status dot */}
                        <div
                            className="flex items-center gap-2"
                            style={{
                                paddingLeft: 12,
                                borderLeft: "1px solid var(--rule)",
                            }}
                        >
                            <div
                                style={{
                                    width: 6,
                                    height: 6,
                                    borderRadius: "50%",
                                    background: "var(--green)",
                                }}
                            />
                            <span
                                className="hidden sm:inline"
                                style={{
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    fontWeight: 500,
                                    color: "var(--ink-faint)",
                                    letterSpacing: "0.12em",
                                    textTransform: "uppercase",
                                }}
                            >
                                Live
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Signature truth line — unique decorative element, only here */}
            <TruthLine />
        </header>
    );
}
