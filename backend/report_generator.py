"""
Alpha-Guard — PDF Report Generator
====================================
Generates professional branded PDF reports using ReportLab.
Compiles Z-Score, Forensic AI, and Monte Carlo results.
"""

import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import VERSION
from models import ZScoreResult, MonteCarloResult
from security import rate_limit
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# ──────────────────────────────────────────────
#  Brand Colors
# ──────────────────────────────────────────────

BRAND_DARK = colors.HexColor("#06080f")
BRAND_GREEN = colors.HexColor("#00e67a")
BRAND_CYAN = colors.HexColor("#22d3ee")
BRAND_RED = colors.HexColor("#ef4444")
BRAND_AMBER = colors.HexColor("#f59e0b")
BRAND_GRAY = colors.HexColor("#94a3b8")
BRAND_LIGHT = colors.HexColor("#f1f5f9")


def _build_styles():
    """Build custom paragraph styles for the Alpha-Guard brand."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "AG_Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=BRAND_DARK,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "AG_Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=BRAND_GRAY,
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        "AG_SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=BRAND_DARK,
        spaceBefore=16,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "AG_Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        leading=14,
    ))
    styles.add(ParagraphStyle(
        "AG_Mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        textColor=BRAND_DARK,
    ))
    styles.add(ParagraphStyle(
        "AG_Footer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=BRAND_GRAY,
        alignment=1,  # Center
    ))

    return styles


def _zone_color(zone: str) -> colors.HexColor:
    """Return brand color for a risk zone."""
    if zone == "Safe":
        return BRAND_GREEN
    elif zone == "Distress":
        return BRAND_RED
    return BRAND_AMBER


def generate_pdf_report(
    ticker: str,
    company_name: str,
    z_score: ZScoreResult | None = None,
    forensic_data: dict | None = None,
    monte_carlo: MonteCarloResult | None = None,
    data_sources: list[str] | None = None,
    z_score_note: str | None = None,
) -> bytes:
    """Generate a PDF report and return it as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = _build_styles()
    story = []

    # ─── Header ───
    story.append(Paragraph("ALPHA-GUARD", styles["AG_Title"]))
    story.append(Paragraph(
        escape(f"Executive Risk Report — {ticker} ({company_name})"),
        styles["AG_Subtitle"],
    ))
    story.append(Paragraph(
        f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}",
        styles["AG_Subtitle"],
    ))
    story.append(HRFlowable(
        width="100%", thickness=1, color=BRAND_GREEN,
        spaceAfter=12, spaceBefore=4,
    ))

    # ─── Z-Score Section ───
    story.append(Paragraph("1. ALTMAN Z-SCORE ANALYSIS", styles["AG_SectionHeader"]))
    if z_score:
        zone_color = _zone_color(z_score.zone)

        # Score badge
        story.append(Paragraph(
            f'Z-Score: <font color="#{zone_color.hexval()[2:]}">'
            f"<b>{z_score.score:.2f}</b></font> — "
            f'<font color="#{zone_color.hexval()[2:]}">{z_score.zone.upper()} ZONE</font>',
            styles["AG_Body"],
        ))
        story.append(Spacer(1, 8))

        story.append(Paragraph(escape(z_score.model_label), styles["AG_Subtitle"]))

        # Components table — weights come from the model actually used
        c = z_score.components
        w = z_score.weights or {"x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0}
        x4_label = "X4 — Market Cap / Liabilities" if z_score.x4_basis == "market" else "X4 — Book Equity / Liabilities"
        rows = [
            ("X1 — Working Capital / Assets", c.x1_working_capital_to_total_assets, w["x1"]),
            ("X2 — Retained Earnings / Assets", c.x2_retained_earnings_to_total_assets, w["x2"]),
            ("X3 — EBIT / Assets", c.x3_ebit_to_total_assets, w["x3"]),
            (x4_label, c.x4_market_cap_to_total_liabilities, w["x4"]),
            ("X5 — Revenue / Assets", c.x5_revenue_to_total_assets, w["x5"]),
        ]
        comp_data = [["Component", "Ratio", "Weight", "Weighted"]] + [
            [label, f"{val:.4f}", f"×{weight:g}", f"{val * weight:.4f}"]
            for label, val, weight in rows
            if weight
        ]

        comp_table = Table(comp_data, colWidths=[3 * inch, 1.1 * inch, 0.8 * inch, 1.1 * inch])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_DARK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Courier"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 8))
        story.append(Paragraph(escape(z_score.interpretation), styles["AG_Body"]))
    else:
        story.append(Paragraph(escape(z_score_note or "Z-Score data unavailable for this ticker."), styles["AG_Body"]))

    story.append(Spacer(1, 12))

    # ─── Forensic AI Section ───
    story.append(Paragraph("2. FORENSIC AI ANALYSIS", styles["AG_SectionHeader"]))
    if forensic_data:
        f = forensic_data
        truth = f.get("truth_score")
        if truth is None:
            story.append(Paragraph("Truth Score: <b>N/A</b>", styles["AG_Body"]))
        else:
            truth_color = _zone_color("Safe" if truth >= 70 else "Distress" if truth < 40 else "Gray")
            story.append(Paragraph(
                f'Truth Score: <font color="#{truth_color.hexval()[2:]}"><b>{truth}</b></font> '
                f'— {escape(f.get("truth_zone") or "Unknown")}',
                styles["AG_Body"],
            ))
            breakdown = f.get("truth_score_breakdown") or {}
            if breakdown.get("basis") == "demo":
                story.append(Paragraph(
                    "DEMO SCORE — simulated value, fixed per ticker; not an analysis result.",
                    styles["AG_Subtitle"],
                ))
            elif breakdown:
                story.append(Paragraph(
                    f"100 − hedging {breakdown.get('hedging_penalty', 0):g} − evasion {breakdown.get('evasion_penalty', 0):g} "
                    f"− red flags {breakdown.get('red_flag_penalty', 0):g} − sentiment gap {breakdown.get('sentiment_gap_penalty', 0):g} "
                    f"(basis: {escape(breakdown.get('basis', ''))})",
                    styles["AG_Subtitle"],
                ))
        if f.get("analysis_note"):
            story.append(Paragraph(escape(f["analysis_note"]), styles["AG_Subtitle"]))

        la = f.get("linguistic_analysis", {})
        if la:
            metrics_data = [
                ["Metric", "Value"],
                ["Hedging Score", f"{la.get('hedging_score', 0):.1f}"],
                ["Evasion Score", f"{la.get('evasion_score', 0):.1f}"],
                ["Sentiment", (la.get("sentiment") or "N/A").upper()],
                ["Confidence", f"{la.get('sentiment_confidence', 0):.0%}"],
                ["Words Analyzed", f"{la.get('total_words_analyzed', 0):,}"],
            ]
            metrics_table = Table(metrics_data, colWidths=[2.5 * inch, 1.5 * inch])
            metrics_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Courier"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(Spacer(1, 6))
            story.append(metrics_table)

        # Deception alert
        if f.get("deception_alert"):
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                f'DECEPTION ALERT: {escape(f.get("deception_reason") or "")}',
                ParagraphStyle(
                    "alert", parent=styles["AG_Body"],
                    textColor=BRAND_RED, fontName="Helvetica-Bold", fontSize=9,
                ),
            ))

        # Red flags
        red_flags = f.get("red_flags", [])
        if red_flags:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Red Flags ({len(red_flags)})", styles["AG_Body"]))
            cell_style = ParagraphStyle("flag_cell", parent=styles["AG_Body"], fontSize=7, leading=9)
            flag_data = [["#", "Severity", "Category", "Explanation"]]
            for i, flag in enumerate(red_flags[:10], 1):
                category = flag.get("category", "")
                if flag.get("verified") is False:
                    category += " (unverified quote)"
                flag_data.append([
                    str(i),
                    str(flag.get("severity", "?")),
                    Paragraph(escape(category), cell_style),
                    Paragraph(escape(flag.get("explanation", "")[:300]), cell_style),
                ])
            flag_table = Table(flag_data, colWidths=[0.3 * inch, 0.6 * inch, 1 * inch, 4 * inch])
            flag_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(flag_table)
    else:
        story.append(Paragraph("Forensic analysis unavailable.", styles["AG_Body"]))

    story.append(Spacer(1, 12))

    # ─── Monte Carlo Section ───
    story.append(Paragraph("3. MONTE CARLO STRESS TEST", styles["AG_SectionHeader"]))
    if monte_carlo:
        def fmt_rev(v):
            if v and v >= 1e9: return f"${v / 1e9:.1f}B"
            if v and v >= 1e6: return f"${v / 1e6:.0f}M"
            return f"${v:,.0f}" if v else "N/A"

        mc_data = [
            ["Metric", "Value"],
            ["Simulations", f"{monte_carlo.num_simulations:,}"],
            ["Time Horizon", f"{monte_carlo.time_horizon_years} years"],
            ["Initial Revenue", fmt_rev(monte_carlo.initial_revenue)],
            ["Mean Final Revenue", fmt_rev(monte_carlo.mean_final_revenue)],
            ["Median Final Revenue", fmt_rev(monte_carlo.median_final_revenue)],
            ["5th Percentile (Worst)", fmt_rev(monte_carlo.percentile_5)],
            ["95th Percentile (Best)", fmt_rev(monte_carlo.percentile_95)],
            ["P(Decline >20%)", f"{(monte_carlo.probability_of_decline or 0) * 100:.1f}%"],
        ]
        mc_table = Table(mc_data, colWidths=[2.5 * inch, 2 * inch])
        mc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0fdfa")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Courier"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(mc_table)
    else:
        story.append(Paragraph("Monte Carlo simulation not run for this report.", styles["AG_Body"]))

    # ─── Footer ───
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GRAY, spaceAfter=6))
    story.append(Paragraph(
        f"ALPHA-GUARD v{VERSION} · Confidential · Generated by Alpha-Guard Forensic Credit Risk Platform",
        styles["AG_Footer"],
    ))
    story.append(Paragraph(
        escape("Data sources: " + (" · ".join(data_sources) if data_sources else "n/a")),
        styles["AG_Footer"],
    ))

    doc.build(story)
    return buffer.getvalue()


# ──────────────────────────────────────────────
#  API Endpoint
# ──────────────────────────────────────────────

class PDFReportRequest(BaseModel):
    """Request to generate a downloadable PDF report."""
    ticker: str = Field(..., description="Stock ticker symbol")
    include_monte_carlo: bool = Field(default=True, description="Include MC stress test in report")
    mc_simulations: int = Field(default=1000, ge=100, le=10000)
    mc_horizon_years: int = Field(default=5, ge=1, le=10)


@router.post(
    "/generate-pdf",
    summary="Generate PDF Executive Report",
    description=(
        "Generates a branded PDF report compiling Z-Score analysis, "
        "Forensic AI findings, and Monte Carlo stress test results. "
        "Returns the PDF as a downloadable file."
    ),
    dependencies=[Depends(rate_limit)],
)
async def api_generate_pdf(request: PDFReportRequest):
    """Generate and return a PDF report."""
    from forensic_analyzer import run_forensic_pipeline
    from risk_engine import run_monte_carlo_simulation
    from models import MonteCarloInput

    # Same pipeline as the dashboard, so US and international tickers both work
    audit, financials = await run_forensic_pipeline(request.ticker)
    ticker = audit.ticker
    forensic = audit.forensic

    z_score_note = next(
        (s for s in audit.data_sources if s.startswith(("Z-Score not computed", "Financial data unavailable"))),
        None,
    )

    mc_result = None
    if request.include_monte_carlo and financials is not None and financials.revenue > 0:
        mc_result = run_monte_carlo_simulation(MonteCarloInput(
            ticker=ticker,
            num_simulations=request.mc_simulations,
            time_horizon_years=request.mc_horizon_years,
            initial_revenue=financials.revenue,
        ))

    pdf_bytes = generate_pdf_report(
        ticker=ticker,
        company_name=audit.company_name or ticker,
        z_score=forensic.z_score_result,
        forensic_data=(
            forensic.model_dump()
            if forensic.truth_score is not None or forensic.linguistic_analysis.total_words_analyzed
            else None
        ),
        monte_carlo=mc_result,
        data_sources=audit.data_sources,
        z_score_note=z_score_note,
    )

    safe_ticker = "".join(ch for ch in ticker if ch.isalnum() or ch in ".-_")
    filename = f"AlphaGuard_{safe_ticker}_Report_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
