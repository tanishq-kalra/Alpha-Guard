"use client";

import React from "react";
import DashboardHeader from "@/components/DashboardHeader";
import { AnimatedSection, AnimatedList } from "@/components/AnimatedSection";
import { TEAM } from "@/lib/team";

const MONO = "var(--font-ibm-plex-mono, monospace)";
const SERIF = "var(--font-source-serif, Georgia, serif)";
const SANS = "var(--font-ibm-plex-sans, system-ui, sans-serif)";

const AVATAR_COLORS = [
    { color: "var(--green)", tint: "var(--green-tint)" },
    { color: "var(--blue)", tint: "var(--blue-tint)" },
    { color: "var(--amber)", tint: "var(--amber-tint)" },
    { color: "var(--red)", tint: "var(--red-tint)" },
];

function initials(name: string): string {
    const parts = name.trim().split(/\s+/);
    return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

const MODULES = [
    { title: "Altman Z-Score", desc: "Bankruptcy-risk model from SEC filings, auto-selecting the original Z or Z'' model; capital strength for banks." },
    { title: "Truth Score", desc: "Credibility Index from five kinds of evidence: financial health, filing language, earnings-call candor, narrative consistency and earnings quality." },
    { title: "Earnings Call Analysis", desc: "Splits conference calls into scripted remarks and analyst Q&A, detecting deflected questions and tone drops." },
    { title: "Investment Conviction", desc: "Six-pillar view of whether a company is a sound investment: strength, profitability, growth, credibility, valuation and cash quality." },
    { title: "Revenue Stress Test", desc: "1,000-path Monte Carlo simulation using each company's own historical growth and volatility." },
    { title: "Research Reports", desc: "Multi-page reports and PDFs with trends, risk register, methodology and academic references." },
];

const STACK = [
    { title: "Frontend", color: "var(--green)", tint: "var(--green-tint)", items: ["Next.js", "React", "TypeScript", "Tailwind CSS", "Recharts", "Framer Motion"] },
    { title: "Backend", color: "var(--blue)", tint: "var(--blue-tint)", items: ["Python", "FastAPI", "Pydantic", "NumPy", "ReportLab", "pytest"] },
    { title: "Data Sources", color: "var(--green)", tint: "var(--green-tint)", items: ["SEC EDGAR (XBRL & 10-K)", "Yahoo Finance", "Alpha Vantage transcripts", "Google Gemini"] },
    { title: "Research Methods", color: "var(--blue)", tint: "var(--blue-tint)", items: ["Altman (1968, 2000)", "Sloan accruals (1996)", "Loughran–McDonald lexicon (2011)", "Larcker–Zakolyukina (2012)", "Monte Carlo GBM"] },
];

function SectionHeader({ title, color }: { title: string; color: string }) {
    return (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, paddingBottom: 12, borderBottom: "1px solid var(--rule)" }}>
            <div style={{ width: 3, height: 20, background: color, borderRadius: 2 }} />
            <h3 style={{ fontFamily: SERIF, fontSize: 16, fontWeight: 600, color: "var(--ink)", margin: 0 }}>{title}</h3>
        </div>
    );
}

export default function AboutPage() {
    return (
        <div style={{ minHeight: "100vh", background: "var(--paper)", display: "flex", flexDirection: "column" }}>
            <DashboardHeader />

            <main style={{ flex: 1, width: "100%", maxWidth: 1480, margin: "0 auto", padding: "40px 24px" }}>

                {/* ── Hero ── */}
                <AnimatedSection className="text-center mb-10">
                    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px", borderRadius: 3, background: "var(--green-tint)", marginBottom: 14 }}>
                        <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)" }} />
                        <span style={{ fontFamily: MONO, fontSize: 9, fontWeight: 600, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--green)" }}>
                            The Team
                        </span>
                    </div>
                    <h2 style={{ fontFamily: SERIF, fontSize: "clamp(26px, 4vw, 42px)", fontWeight: 700, color: "var(--ink)", lineHeight: 1.15, letterSpacing: "-0.02em", marginBottom: 12 }}>
                        Built by{" "}<span style={{ color: "var(--green)" }}>Team Alpha-Guard</span>
                    </h2>
                    <p style={{ fontFamily: SANS, fontSize: 14, color: "var(--ink-2)", maxWidth: 520, margin: "0 auto" }}>
                        A capstone project combining financial modelling, forensic text analysis and full-stack engineering
                        to judge whether a company&apos;s story matches its numbers.
                    </p>
                </AnimatedSection>

                {/* ── Team ── */}
                <AnimatedSection delay={0.1} className="mb-10">
                    <SectionHeader title="Team Members" color="var(--green)" />
                    <AnimatedList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {TEAM.map((member, i) => {
                            const palette = AVATAR_COLORS[i % AVATAR_COLORS.length];
                            return (
                                <div
                                    key={member.rollNo}
                                    style={{
                                        background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4,
                                        padding: "24px 20px", textAlign: "center",
                                    }}
                                >
                                    <div
                                        aria-hidden="true"
                                        style={{
                                            width: 72, height: 72, borderRadius: "50%", margin: "0 auto 14px",
                                            display: "flex", alignItems: "center", justifyContent: "center",
                                            background: palette.tint, border: `1px solid ${palette.color}`,
                                            fontFamily: SERIF, fontSize: 24, fontWeight: 700, color: palette.color,
                                        }}
                                    >
                                        {initials(member.name)}
                                    </div>
                                    <h4 style={{ fontFamily: SERIF, fontSize: 16, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
                                        {member.name}
                                    </h4>
                                    <p style={{ fontFamily: MONO, fontSize: 11, color: "var(--ink-2)", letterSpacing: "0.04em" }}>
                                        {member.rollNo}
                                    </p>
                                </div>
                            );
                        })}
                    </AnimatedList>
                </AnimatedSection>

                {/* ── What Alpha-Guard does ── */}
                <AnimatedSection delay={0.2} className="mb-10">
                    <SectionHeader title="What Alpha-Guard Does" color="var(--blue)" />
                    <AnimatedList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {MODULES.map((m) => (
                            <div key={m.title} style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: "16px 18px" }}>
                                <h4 style={{ fontFamily: SERIF, fontSize: 13, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>{m.title}</h4>
                                <p style={{ fontFamily: SANS, fontSize: 11.5, color: "var(--ink-2)", lineHeight: 1.55, margin: 0 }}>{m.desc}</p>
                            </div>
                        ))}
                    </AnimatedList>
                </AnimatedSection>

                {/* ── Tech stack ── */}
                <AnimatedSection delay={0.3} className="mb-10">
                    <SectionHeader title="Tech Stack & Methods" color="var(--green)" />
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }} className="grid-cols-1 md:grid-cols-2">
                        {STACK.map((cat) => (
                            <div key={cat.title} style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: "18px 20px" }}>
                                <h4 style={{ fontFamily: MONO, fontSize: 10, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: cat.color, margin: "0 0 12px" }}>
                                    {cat.title}
                                </h4>
                                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                                    {cat.items.map((item) => (
                                        <span key={item} style={{ padding: "4px 10px", borderRadius: 3, fontFamily: MONO, fontSize: 10, color: "var(--ink-2)", background: "var(--paper)", border: "1px solid var(--rule)" }}>
                                            {item}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </AnimatedSection>

                {/* ── Attribution ── */}
                <AnimatedSection delay={0.4} className="mb-8">
                    <div style={{ background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 4, padding: "20px 24px", textAlign: "center" }}>
                        <p style={{ fontFamily: SANS, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.6, margin: 0 }}>
                            Alpha-Guard was designed and built by {TEAM.map((m) => m.name).join(", ").replace(/, ([^,]*)$/, " and $1")} as
                            their capstone project.
                        </p>
                        <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)", marginTop: 10 }}>
                            VIT-AP University · Capstone Project
                        </p>
                    </div>
                </AnimatedSection>
            </main>

            <footer style={{ borderTop: "1px solid var(--rule)", padding: "14px 24px" }}>
                <div style={{ maxWidth: 1480, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)" }}>ALPHA-GUARD v0.5.0 · Team Alpha-Guard</p>
                    <p style={{ fontFamily: MONO, fontSize: 9, color: "var(--ink-faint)" }}>Powered by FastAPI · Next.js · SEC EDGAR · Alpha Vantage · Google Gemini</p>
                </div>
            </footer>
        </div>
    );
}
