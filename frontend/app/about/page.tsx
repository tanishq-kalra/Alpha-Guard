"use client";

import React, { useState } from "react";
import Image from "next/image";
import DashboardHeader from "@/components/DashboardHeader";
import { AnimatedSection, AnimatedList } from "@/components/AnimatedSection";

const SKILL_CATEGORIES = [
    {
        title: "Languages",
        icon: (
            <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
            </svg>
        ),
        skills: ["Java", "Python", "SQL", "HTML/CSS", "JavaScript"],
        color: "var(--green)",
        tint: "var(--green-tint)",
    },
    {
        title: "Frameworks",
        icon: (
            <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="9" x2="21" y2="9" />
                <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
        ),
        skills: ["Streamlit", "Bootstrap", "Servlets", "JSP", "Git / GitHub"],
        color: "var(--blue)",
        tint: "var(--blue-tint)",
    },
    {
        title: "Data & AI",
        icon: (
            <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
            </svg>
        ),
        skills: ["NLP (TextBlob)", "Plotly", "Google Analytics", "MS Excel (Advanced)", "Postman"],
        color: "var(--green)",
        tint: "var(--green-tint)",
    },
    {
        title: "Strategy",
        icon: (
            <svg style={{ width: 14, height: 14 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
        ),
        skills: ["SEO", "Content Marketing", "PR Strategy", "Market Analytics", "Financial Modeling"],
        color: "var(--blue)",
        tint: "var(--blue-tint)",
    },
];

const CREDENTIALS = [
    { icon: "🤖", title: "AI Project Developer", desc: "Building production-grade AI systems including forensic financial analysis platforms." },
    { icon: "📖", title: "Published Author", desc: '"Collection of a Novice Wordsmith" — Anthology of Hindi & English poems.' },
    { icon: "🏆", title: "Top 14 in NEC (IIT Bombay)", desc: "Selected from 500+ teams for data-driven problem solving at the national level." },
    { icon: "🥈", title: "2nd in India — National Quiz", desc: "National Quiz conducted by Wednesday Time Magazine. Competed against thousands." },
    { icon: "✍️", title: "Published Contributor", desc: "Short stories in Everscribe Magazine and 50-Word Story." },
];

export default function AboutPage() {
    const [hoveredSkill, setHoveredSkill] = useState<string | null>(null);

    return (
        <div style={{ minHeight: "100vh", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
            <DashboardHeader />

            <main style={{ flex: 1, width: "100%", maxWidth: 1480, margin: "0 auto", padding: "40px 24px" }}>

                {/* ── Hero Badge ── */}
                <AnimatedSection className="text-center mb-10">
                    <div style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 12px",
                        borderRadius: 3,
                        background: "var(--green-tint)",
                        marginBottom: 14,
                    }}>
                        <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)" }} />
                        <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--green)" }}>
                            The Architect
                        </span>
                    </div>

                    <h2 style={{
                        fontFamily: "var(--font-source-serif, Georgia, serif)",
                        fontSize: "clamp(26px, 4vw, 42px)",
                        fontWeight: 700,
                        color: "var(--ink)",
                        lineHeight: 1.15,
                        letterSpacing: "-0.02em",
                        marginBottom: 12,
                    }}>
                        Built by{" "}
                        <span style={{ color: "var(--green)" }}>Tanishq Kalra</span>
                    </h2>
                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 14, color: "var(--ink-2)", maxWidth: 440, margin: "0 auto" }}>
                        The mind behind Alpha-Guard — student, developer, author, strategist.
                    </p>
                </AnimatedSection>

                {/* ── Profile Card ── */}
                <AnimatedSection delay={0.1} className="mb-10">
                    <div style={{
                        background: "var(--paper-2)",
                        border: "1px solid var(--rule)",
                        borderRadius: 4,
                        overflow: "hidden",
                    }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 0 }} className="flex-col md:flex-row">
                            <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 32, padding: "32px 40px", flexWrap: "wrap" }}>

                                {/* Avatar */}
                                <div style={{ position: "relative", flexShrink: 0 }}>
                                    <div style={{
                                        position: "relative",
                                        width: 140,
                                        height: 140,
                                        borderRadius: "50%",
                                        overflow: "hidden",
                                        border: "3px solid var(--green-tint)",
                                        outline: "1px solid var(--green)",
                                    }}>
                                        <Image
                                            src="/architect.jpg"
                                            alt="Tanishq Kalra"
                                            fill
                                            style={{ objectFit: "cover" }}
                                            priority
                                        />
                                    </div>
                                    {/* Status badge */}
                                    <div style={{
                                        position: "absolute",
                                        bottom: 4,
                                        right: 4,
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 4,
                                        padding: "3px 8px",
                                        borderRadius: 3,
                                        background: "var(--green-tint)",
                                        border: "1px solid var(--green)",
                                    }}>
                                        <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)" }} />
                                        <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 8, fontWeight: 600, color: "var(--green)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                                            Online
                                        </span>
                                    </div>
                                </div>

                                {/* Info */}
                                <div style={{ flex: 1 }}>
                                    <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 26, fontWeight: 700, color: "var(--ink)", marginBottom: 4, letterSpacing: "-0.01em" }}>
                                        Tanishq Kalra
                                    </h3>
                                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 11, fontWeight: 500, color: "var(--green)", marginBottom: 2 }}>
                                        Student · VIT-AP University
                                    </p>
                                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)", marginBottom: 20, letterSpacing: "0.05em" }}>
                                        Developer · Published Author · National Achiever
                                    </p>

                                    {/* Portfolio CTA — solid primary */}
                                    <a
                                        id="portfolio-cta"
                                        href="https://tanishq-kalra.github.io/portfoliotanishq/"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style={{
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: 8,
                                            padding: "9px 20px",
                                            borderRadius: 4,
                                            background: "var(--green)",
                                            color: "#ffffff",
                                            border: "1px solid var(--green)",
                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                            fontSize: 10,
                                            fontWeight: 600,
                                            letterSpacing: "0.1em",
                                            textTransform: "uppercase",
                                            textDecoration: "none",
                                            transition: "background 0.15s ease",
                                        }}
                                    >
                                        <svg style={{ width: 11, height: 11 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                                            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                                            <polyline points="15 3 21 3 21 9" />
                                            <line x1="10" y1="14" x2="21" y2="3" />
                                        </svg>
                                        View Portfolio
                                        <svg style={{ width: 10, height: 10 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                                            <polyline points="9 18 15 12 9 6" />
                                        </svg>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </AnimatedSection>

                {/* ── Credentials ── */}
                <AnimatedSection delay={0.2} className="mb-10">
                    {/* Section header */}
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, paddingBottom: 12, borderBottom: "1px solid var(--rule)" }}>
                        <div style={{ width: 3, height: 20, background: "var(--green)", borderRadius: 2 }} />
                        <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 16, fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                            Credentials & Achievements
                        </h3>
                    </div>
                    <AnimatedList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {CREDENTIALS.map((cred) => (
                            <div
                                key={cred.title}
                                style={{
                                    background: "var(--paper-2)",
                                    border: "1px solid var(--rule)",
                                    borderRadius: 4,
                                    padding: "16px 18px",
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 12,
                                    transition: "border-color 0.15s ease, box-shadow 0.15s ease",
                                    cursor: "default",
                                }}
                                onMouseEnter={(e) => {
                                    (e.currentTarget as HTMLElement).style.borderColor = "var(--green)";
                                    (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow)";
                                }}
                                onMouseLeave={(e) => {
                                    (e.currentTarget as HTMLElement).style.borderColor = "var(--rule)";
                                    (e.currentTarget as HTMLElement).style.boxShadow = "";
                                }}
                            >
                                <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>{cred.icon}</span>
                                <div>
                                    <h4 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
                                        {cred.title}
                                    </h4>
                                    <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 11, color: "var(--ink-2)", lineHeight: 1.55 }}>
                                        {cred.desc}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </AnimatedList>
                </AnimatedSection>

                {/* ── Skill Matrix ── */}
                <AnimatedSection delay={0.3} className="mb-10">
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, paddingBottom: 12, borderBottom: "1px solid var(--rule)" }}>
                        <div style={{ width: 3, height: 20, background: "var(--blue)", borderRadius: 2 }} />
                        <h3 style={{ fontFamily: "var(--font-source-serif, Georgia, serif)", fontSize: 16, fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                            Tech Stack · Skill Matrix
                        </h3>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }} className="grid-cols-1 md:grid-cols-2">
                        {SKILL_CATEGORIES.map((cat) => (
                            <div
                                key={cat.title}
                                style={{
                                    background: "var(--paper-2)",
                                    border: "1px solid var(--rule)",
                                    borderRadius: 4,
                                    padding: "18px 20px",
                                    transition: "border-color 0.15s ease",
                                }}
                            >
                                {/* Category header */}
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                                    <div style={{
                                        width: 28, height: 28, borderRadius: 4,
                                        background: cat.tint,
                                        border: `1px solid ${cat.tint}`,
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        color: cat.color,
                                    }}>
                                        {cat.icon}
                                    </div>
                                    <h4 style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink)", margin: 0 }}>
                                        {cat.title}
                                    </h4>
                                </div>
                                {/* Skill tags */}
                                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                                    {cat.skills.map((skill) => (
                                        <span
                                            key={skill}
                                            onMouseEnter={() => setHoveredSkill(skill)}
                                            onMouseLeave={() => setHoveredSkill(null)}
                                            style={{
                                                padding: "4px 10px",
                                                borderRadius: 3,
                                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                fontSize: 10,
                                                cursor: "default",
                                                transition: "all 0.15s ease",
                                                background: hoveredSkill === skill ? cat.tint : "var(--paper)",
                                                color: hoveredSkill === skill ? cat.color : "var(--ink-2)",
                                                border: `1px solid ${hoveredSkill === skill ? cat.color : "var(--rule)"}`,
                                            }}
                                        >
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </AnimatedSection>

                {/* ── Attribution ── */}
                <AnimatedSection delay={0.4} className="mb-8">
                    <div style={{
                        background: "var(--paper-2)",
                        border: "1px solid var(--rule)",
                        borderRadius: 4,
                        padding: "20px 24px",
                        textAlign: "center",
                    }}>
                        <p style={{ fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)", fontSize: 12, color: "var(--ink-2)", lineHeight: 1.6 }}>
                            Alpha-Guard was conceptualized and architected by Tanishq Kalra as a demonstration
                            of full-stack engineering, financial modeling, and AI integration capabilities.
                        </p>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, marginTop: 12 }}>
                            <a
                                href="https://tanishq-kalra.github.io/portfoliotanishq/"
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 10, color: "var(--green)", textDecoration: "none" }}
                            >
                                Portfolio ↗
                            </a>
                            <div style={{ width: 1, height: 14, background: "var(--rule)" }} />
                            <span style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                                VIT-AP University · 2023–2027
                            </span>
                        </div>
                    </div>
                </AnimatedSection>
            </main>

            <footer style={{ borderTop: "1px solid var(--rule)", padding: "14px 24px" }}>
                <div style={{ maxWidth: 1480, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                        ALPHA-GUARD v0.3.0 · Designed by Tanishq Kalra
                    </p>
                    <p style={{ fontFamily: "var(--font-ibm-plex-mono, monospace)", fontSize: 9, color: "var(--ink-faint)" }}>
                        Powered by FastAPI · Next.js · SEC EDGAR · Google Gemini
                    </p>
                </div>
            </footer>
        </div>
    );
}
