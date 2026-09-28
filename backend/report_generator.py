"""
Alpha-Guard — PDF Research Report
==================================
Generates a multi-page, branded research report with ReportLab:

  Cover (key metrics, team, contents)
  Executive Summary — Should you invest?
  1. Company Snapshot        5. Earnings Conference Call
  2. Financial Trends        6. Revenue Stress Test (Monte Carlo)
  3. Financial Health        7. Risk Register
  4. Truth Score & Forensics 8. Methodology & References
                             9. Data Sources & Disclaimer
"""

import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import REPORT_TEAM, VERSION
from models import ForensicAuditResponse, MonteCarloResult
from security import rate_limit

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# ──────────────────────────────────────────────
#  Brand
# ──────────────────────────────────────────────

BRAND_DARK = colors.HexColor("#06080f")
BRAND_GREEN = colors.HexColor("#0f9d58")
BRAND_RED = colors.HexColor("#dc2626")
BRAND_AMBER = colors.HexColor("#d97706")
BRAND_GRAY = colors.HexColor("#94a3b8")
BRAND_INK2 = colors.HexColor("#334155")
BRAND_RULE = colors.HexColor("#e2e8f0")
BRAND_TINT = colors.HexColor("#f8fafc")
CHART_BLUE = colors.HexColor("#2563eb")
CHART_TEAL = colors.HexColor("#0d9488")
CHART_SLATE = colors.HexColor("#94a3b8")

SECTIONS = [
    "Executive Summary — Should You Invest?",
    "1. Company Snapshot",
    "2. Financial Trends",
    "3. Financial Health (Altman Z-Score)",
    "4. Truth Score & Forensic Analysis",
    "5. Earnings Conference Call",
    "6. Revenue Stress Test (Monte Carlo)",
    "7. Risk Register",
    "8. Methodology & References",
    "9. Data Sources & Disclaimer",
]

REFERENCES = [
    ("Altman, E. I. (1968)", "Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy. "
                             "Journal of Finance, 23(4), 589–609."),
    ("Altman, E. I. (2000)", "Predicting Financial Distress of Companies: Revisiting the Z-Score and ZETA Models "
                             "(Z'' model for non-manufacturers and emerging markets). NYU Stern working paper."),
    ("Sloan, R. G. (1996)", "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future "
                            "Earnings? The Accounting Review, 71(3), 289–315."),
    ("Loughran, T. & McDonald, B. (2011)", "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, "
                                           "and 10-Ks. Journal of Finance, 66(1), 35–65."),
    ("Larcker, D. F. & Zakolyukina, A. A. (2012)", "Detecting Deceptive Discussions in Conference Calls. "
                                                   "Journal of Accounting Research, 50(2), 495–540."),
    ("Glasserman, P. (2003)", "Monte Carlo Methods in Financial Engineering. Springer (geometric Brownian motion)."),
]

METHODS = [
    ("Altman Z-Score", "Weighted ratios of working capital, retained earnings, EBIT, equity and sales to assets. "
                       "The original model is used for US manufacturers; Z'' (book equity, no sales term) for "
                       "other companies. Banks and insurers are judged on capital strength (equity / assets) and "
                       "return on assets instead."),
    ("Truth Score", "Credibility Index combining financial health (30%), filing language (20%), earnings-call "
                    "candor (20%), narrative consistency (15%) and earnings quality (15%). Missing evidence is "
                    "excluded and weights re-balanced."),
    ("Filing language", "Whole-word dictionaries count hedging (e.g. 'may', 'uncertain') and evasive phrases "
                        "(e.g. 'we believe') in the 10-K MD&A, or in the earnings press release when no MD&A "
                        "is found. Only language above normal filing levels is penalised."),
    ("Earnings call", "Transcripts are split into scripted remarks and analyst Q&A. Refusals to answer, "
                      "very short answers and a tone drop from script to Q&A lower the Call Candor Score."),
    ("Earnings quality", "Accruals = (net income − operating cash flow) / total assets. Profits not backed by "
                         "cash are a classic warning sign of aggressive accounting."),
    ("Investment conviction", "Six pillars: financial strength, profitability, growth, credibility, valuation "
                              "(P/E) and earnings quality. A deception alert caps conviction at 45%."),
    ("Stress test", "1,000 revenue paths simulated with geometric Brownian motion, using the company's own "
                    "historical revenue growth and volatility."),
]


def _styles():
    s = getSampleStyleSheet()
    add = s.add
    add(ParagraphStyle("CoverBrand", parent=s["Title"], fontName="Helvetica-Bold", fontSize=30,
                       leading=36, textColor=BRAND_DARK, alignment=0, spaceAfter=6))
    add(ParagraphStyle("CoverTitle", parent=s["Normal"], fontName="Helvetica", fontSize=13,
                       textColor=BRAND_INK2, spaceAfter=18))
    add(ParagraphStyle("CoverCompany", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=20,
                       textColor=BRAND_DARK, leading=24, spaceAfter=4))
    add(ParagraphStyle("Section", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=14,
                       textColor=BRAND_DARK, spaceBefore=4, spaceAfter=8))
    add(ParagraphStyle("Sub", parent=s["Heading3"], fontName="Helvetica-Bold", fontSize=10,
                       textColor=BRAND_DARK, spaceBefore=8, spaceAfter=4))
    add(ParagraphStyle("Body", parent=s["Normal"], fontName="Helvetica", fontSize=9.5,
                       textColor=BRAND_INK2, leading=13.5))
    add(ParagraphStyle("Small", parent=s["Normal"], fontName="Helvetica", fontSize=8,
                       textColor=BRAND_GRAY, leading=11))
    add(ParagraphStyle("Cell", parent=s["Normal"], fontName="Helvetica", fontSize=7.5,
                       textColor=BRAND_INK2, leading=9.5))
    add(ParagraphStyle("Big", parent=s["Normal"], fontName="Helvetica-Bold", fontSize=22,
                       textColor=BRAND_DARK, leading=26, alignment=1))
    add(ParagraphStyle("BigLabel", parent=s["Normal"], fontName="Helvetica", fontSize=7.5,
                       textColor=BRAND_GRAY, alignment=1))
    return s


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _money(v: float | None) -> str:
    if v is None:
        return "—"
    a, sign = abs(v), "-" if v < 0 else ""
    if a >= 1e12:
        return f"{sign}${a / 1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}${a / 1e9:.1f}B"
    if a >= 1e6:
        return f"{sign}${a / 1e6:.0f}M"
    return f"{sign}${a:,.0f}"


def _pct(v: float | None, digits: int = 1) -> str:
    return "—" if v is None else f"{v * 100:.{digits}f}%"


def _score_color(score: float | None, good: float = 70, fair: float = 40) -> colors.Color:
    if score is None:
        return BRAND_GRAY
    return BRAND_GREEN if score >= good else BRAND_AMBER if score >= fair else BRAND_RED


def _hex(c: colors.Color) -> str:
    return "#" + c.hexval()[2:]


def _table(rows, widths, header_bg=BRAND_TINT, mono_body=False, align_right_from=None, zebra=True):
    t = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), BRAND_INK2),
        ("GRID", (0, 0), (-1, -1), 0.5, BRAND_RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if mono_body:
        style.append(("FONTNAME", (0, 1), (-1, -1), "Courier"))
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
    if zebra:
        style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_TINT]))
    t.setStyle(TableStyle(style))
    return t


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(text), style)


def _metric_tiles(tiles: list[tuple[str, str, colors.Color, str]], st) -> Table:
    """Row of big-number tiles: (label, value, colour, caption)."""
    cells = [[
        [Paragraph(f'<font color="{_hex(color)}">{escape(value)}</font>', st["Big"]),
         Paragraph(escape(label.upper()), st["BigLabel"]),
         Paragraph(escape(caption), st["BigLabel"])]
        for label, value, color, caption in tiles
    ]]
    width = (A4[0] - 40 * mm) / len(tiles)
    t = Table(cells, colWidths=[width] * len(tiles))
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, BRAND_RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, BRAND_RULE),
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_TINT),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _trend_chart(history) -> Drawing | None:
    """Grouped bars: revenue, net income and operating cash flow per fiscal year ($B)."""
    points = [h for h in reversed(history) if h.revenue]
    if len(points) < 2:
        return None
    series = [
        [(h.revenue or 0) / 1e9 for h in points],
        [(h.net_income or 0) / 1e9 for h in points],
        [(h.operating_cash_flow or 0) / 1e9 for h in points],
    ]
    d = Drawing(460, 190)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 45, 30, 400, 135
    chart.data = series
    chart.categoryAxis.categoryNames = [f"FY{h.fiscal_period_end[:4]}" for h in points]
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "$%.0fB"
    low = min(min(s) for s in series)
    chart.valueAxis.valueMin = min(0, low * 1.15)
    chart.valueAxis.gridStrokeColor = BRAND_RULE
    chart.valueAxis.visibleGrid = True
    chart.barSpacing = 1
    chart.groupSpacing = 8
    for i, col in enumerate((CHART_BLUE, CHART_TEAL, CHART_SLATE)):
        chart.bars[i].fillColor = col
        chart.bars[i].strokeColor = None
    d.add(chart)
    legend = Legend()
    legend.x, legend.y = 50, 185
    legend.fontName, legend.fontSize = "Helvetica", 7
    legend.alignment = "right"
    legend.columnMaximum = 1
    legend.deltax = 110
    legend.colorNamePairs = [(CHART_BLUE, "Revenue"), (CHART_TEAL, "Net income"), (CHART_SLATE, "Operating cash flow")]
    d.add(legend)
    return d


def _on_page(canvas, doc, ticker: str, company: str):
    """Running header and page-numbered footer on every page after the cover."""
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(BRAND_RULE)
    canvas.setLineWidth(0.6)
    canvas.line(20 * mm, h - 14 * mm, w - 20 * mm, h - 14 * mm)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(BRAND_DARK)
    canvas.drawString(20 * mm, h - 12 * mm, "ALPHA-GUARD")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(BRAND_GRAY)
    canvas.drawRightString(w - 20 * mm, h - 12 * mm, f"{company} ({ticker}) — Research Report")
    canvas.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)
    canvas.drawString(20 * mm, 10 * mm, f"Alpha-Guard v{VERSION} · Educational analysis — not financial advice")
    canvas.drawRightString(w - 20 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ──────────────────────────────────────────────
#  Sections
# ──────────────────────────────────────────────

def _cover(audit: ForensicAuditResponse, st) -> list:
    f = audit.forensic
    z = f.z_score_result
    conv = audit.conviction
    generated = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    out = [
        Spacer(1, 18 * mm),
        _p("ALPHA-GUARD", st["CoverBrand"]),
        _p("Forensic Credit & Investment Research Report", st["CoverTitle"]),
        HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=14),
        _p(audit.company_name or audit.ticker, st["CoverCompany"]),
        _p(f"Ticker {audit.ticker} · Generated {generated}", st["Small"]),
        Spacer(1, 12 * mm),
        _metric_tiles([
            ("Investment conviction", f"{conv.score}%" if conv and conv.score is not None else "N/A",
             _score_color(conv.score if conv else None, 65, 50), (conv.verdict or "") if conv else ""),
            ("Truth Score", str(f.truth_score) if f.truth_score is not None else "N/A",
             _score_color(f.truth_score), f.truth_zone or ""),
            ("Altman Z-Score", f"{z.score:.2f}" if z else "N/A",
             {"Safe": BRAND_GREEN, "Gray": BRAND_AMBER, "Distress": BRAND_RED}.get(z.zone, BRAND_GRAY) if z else BRAND_GRAY,
             f"{z.zone} zone" if z else "not applicable"),
        ], st),
        Spacer(1, 12 * mm),
        _p("Contents", st["Sub"]),
    ]
    out += [_p(s, st["Body"]) for s in SECTIONS]
    out += [Spacer(1, 12 * mm), _p("Prepared by", st["Sub"])]
    team_rows = [["Name", "Roll number"]] + [[n, r] for n, r in REPORT_TEAM]
    out.append(_table(team_rows, [3.2 * inch, 1.6 * inch]))
    out += [Spacer(1, 6), _p("Capstone Project · Alpha-Guard Forensic Credit Risk Platform", st["Small"]), PageBreak()]
    return out


def _executive_summary(audit: ForensicAuditResponse, st) -> list:
    conv = audit.conviction
    out = [_p(SECTIONS[0], st["Section"])]
    if not conv or conv.score is None:
        out.append(_p(conv.headline if conv else "Investment conviction unavailable for this ticker.", st["Body"]))
        return out
    color = _score_color(conv.score, 65, 50)
    out.append(Paragraph(
        f'Investment conviction <font color="{_hex(color)}"><b>{conv.score}%</b></font> — <b>{escape(conv.verdict or "")}</b>',
        st["Body"],
    ))
    out.append(_p(conv.headline, st["Body"]))
    if conv.capped_reason:
        out.append(Paragraph(f'<font color="{_hex(BRAND_RED)}">{escape(conv.capped_reason)}</font>', st["Body"]))
    out.append(Spacer(1, 6))
    rows = [["Pillar", "Score", "Weight", "Key figure", "Evidence"]] + [
        [p.label, str(p.score), f"{p.effective_weight * 100:.0f}%", _p(p.metric or "—", st["Cell"]), _p(p.detail, st["Cell"])]
        for p in conv.pillars
    ]
    out.append(_table(rows, [1.45 * inch, 0.5 * inch, 0.55 * inch, 1.2 * inch, 2.55 * inch], header_bg=colors.HexColor("#f0fdf4")))
    for title, items, color in (("Strengths", conv.strengths, BRAND_GREEN), ("Concerns", conv.concerns, BRAND_RED)):
        if items:
            out.append(Paragraph(f'<font color="{_hex(color)}">{title}</font>', st["Sub"]))
            out += [_p(f"• {i}", st["Body"]) for i in items]
    out += [Spacer(1, 6), _p(conv.disclaimer, st["Small"])]
    return out


def _snapshot(audit: ForensicAuditResponse, st) -> list:
    fin = audit.financials
    out = [_p(SECTIONS[1], st["Section"])]
    if fin is None:
        return out + [_p("Financial statement data unavailable for this ticker.", st["Body"])]
    equity = fin.total_assets - fin.total_liabilities
    rows = [
        ["Fiscal year ending", fin.fiscal_period_end or "—", "Market capitalisation", _money(fin.market_cap)],
        ["Revenue", _money(fin.revenue), "Net income", _money(fin.net_income)],
        ["Operating cash flow", _money(fin.operating_cash_flow), "Total assets", _money(fin.total_assets)],
        ["Total liabilities", _money(fin.total_liabilities), "Shareholders' equity (book)", _money(equity)],
    ]
    ratios = [
        ["Net margin", _pct(fin.net_income / fin.revenue if fin.net_income is not None and fin.revenue else None)],
        ["Return on assets", _pct(fin.net_income / fin.total_assets if fin.net_income is not None else None, 2)],
        ["Revenue growth (YoY)", _pct(fin.revenue / fin.revenue_prior_year - 1 if fin.revenue_prior_year else None)],
        ["Liabilities / assets", _pct(fin.total_liabilities / fin.total_assets)],
        ["Price / earnings", f"{fin.market_cap / fin.net_income:.1f}x" if fin.market_cap and fin.net_income and fin.net_income > 0 else "—"],
        ["Cash conversion (OCF / net income)",
         f"{fin.operating_cash_flow / fin.net_income:.2f}x" if fin.operating_cash_flow is not None and fin.net_income else "—"],
    ]
    out.append(_p("Key figures", st["Sub"]))
    out.append(_table([["Item", "Value", "Item", "Value"]] + rows, [1.6 * inch, 1.3 * inch, 1.9 * inch, 1.3 * inch]))
    out.append(_p("Key ratios", st["Sub"]))
    out.append(_table([["Ratio", "Value"]] + ratios, [3.2 * inch, 1.5 * inch], mono_body=True))
    sector = fin.sector if fin.sector and fin.sector != "Unknown" else (f"SIC {fin.sic_code}" if fin.sic_code else "—")
    out.append(_p(f"Classification: {sector}. Figures in reporting currency as filed.", st["Small"]))
    return out


def _trends(audit: ForensicAuditResponse, st) -> list:
    fin = audit.financials
    out = [_p(SECTIONS[2], st["Section"])]
    history = fin.history if fin else []
    if len(history) < 2:
        return out + [_p("Not enough annual history available to show trends.", st["Body"])]
    chart = _trend_chart(history)
    if chart:
        out.append(chart)
    rows = [["Fiscal year", "Revenue", "Growth", "Net income", "Margin", "Operating CF", "Total assets"]]
    ordered = list(reversed(history))
    for i, h in enumerate(ordered):
        prev = ordered[i - 1].revenue if i > 0 else None
        rows.append([
            f"FY{h.fiscal_period_end[:4]}",
            _money(h.revenue),
            _pct(h.revenue / prev - 1) if h.revenue and prev else "—",
            _money(h.net_income),
            _pct(h.net_income / h.revenue) if h.net_income is not None and h.revenue else "—",
            _money(h.operating_cash_flow),
            _money(h.total_assets),
        ])
    out.append(_table(rows, [0.9 * inch, 0.95 * inch, 0.7 * inch, 0.95 * inch, 0.7 * inch, 0.95 * inch, 0.95 * inch],
                      mono_body=True, align_right_from=1))
    if len(ordered) >= 3 and ordered[0].revenue and ordered[-1].revenue and ordered[0].revenue > 0:
        years = len(ordered) - 1
        cagr = (ordered[-1].revenue / ordered[0].revenue) ** (1 / years) - 1
        out.append(_p(f"Revenue compound annual growth over {years} years: {cagr * 100:+.1f}%.", st["Small"]))
    return out


def _health(audit: ForensicAuditResponse, st) -> list:
    z = audit.forensic.z_score_result
    out = [_p(SECTIONS[3], st["Section"])]
    if z is None:
        note = next((s for s in audit.data_sources if s.startswith(("Z-Score not computed", "Financial data unavailable"))), None)
        out.append(_p(note or "Z-Score unavailable for this ticker.", st["Body"]))
        health = next((c for c in (audit.forensic.truth_score_breakdown.components if audit.forensic.truth_score_breakdown else [])
                       if c.key == "financial_health"), None)
        if health:
            out.append(_p(f"Alternative health measure (score {health.score}/100): {health.detail}", st["Body"]))
        return out
    color = {"Safe": BRAND_GREEN, "Gray": BRAND_AMBER, "Distress": BRAND_RED}.get(z.zone, BRAND_GRAY)
    out.append(Paragraph(
        f'Z-Score <font color="{_hex(color)}"><b>{z.score:.2f}</b> — {z.zone.upper()} ZONE</font> '
        f'<font color="{_hex(BRAND_GRAY)}">({escape(z.model_label)}; Distress &lt; {z.distress_threshold}, Safe &gt; {z.safe_threshold})</font>',
        st["Body"],
    ))
    c, w = z.components, z.weights or {"x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0}
    x4 = "X4 — Market cap / liabilities" if z.x4_basis == "market" else "X4 — Book equity / liabilities"
    comp = [
        ("X1 — Working capital / assets", c.x1_working_capital_to_total_assets, w["x1"]),
        ("X2 — Retained earnings / assets", c.x2_retained_earnings_to_total_assets, w["x2"]),
        ("X3 — EBIT / assets", c.x3_ebit_to_total_assets, w["x3"]),
        (x4, c.x4_market_cap_to_total_liabilities, w["x4"]),
        ("X5 — Revenue / assets", c.x5_revenue_to_total_assets, w["x5"]),
    ]
    rows = [["Component", "Ratio", "Weight", "Weighted"]] + [
        [label, f"{val:.4f}", f"×{weight:g}", f"{val * weight:.4f}"] for label, val, weight in comp if weight
    ]
    out += [Spacer(1, 4), _table(rows, [3 * inch, 1.1 * inch, 0.8 * inch, 1.1 * inch], mono_body=True, align_right_from=1),
            Spacer(1, 4), _p(z.interpretation, st["Body"])]
    return out


def _forensics(audit: ForensicAuditResponse, st) -> list:
    f = audit.forensic
    out = [_p(SECTIONS[4], st["Section"])]
    color = _score_color(f.truth_score)
    out.append(Paragraph(
        f'Truth Score <font color="{_hex(color)}"><b>{f.truth_score if f.truth_score is not None else "N/A"}</b></font>'
        f' — {escape(f.truth_zone or "not enough evidence")}',
        st["Body"],
    ))
    comps = f.truth_score_breakdown.components if f.truth_score_breakdown else []
    if comps:
        rows = [["Component", "Score", "Weight", "Evidence"]] + [
            [c.label, str(c.score), f"{c.effective_weight * 100:.0f}%", _p(c.detail, st["Cell"])] for c in comps
        ]
        out += [Spacer(1, 4), _table(rows, [1.5 * inch, 0.55 * inch, 0.6 * inch, 3.6 * inch])]
    if f.analysis_note:
        out.append(_p(f.analysis_note, st["Small"]))

    la = f.linguistic_analysis
    if la.total_words_analyzed:
        out.append(_p(f"Language metrics — {f.language_source or '10-K MD&A'}", st["Sub"]))
        tone = "—" if la.net_tone is None else f"{la.net_tone:+.2f}"
        rows = [["Metric", "Value"],
                ["Hedging score (0–100)", f"{la.hedging_score:.1f}"],
                ["Evasion score (0–100)", f"{la.evasion_score:.1f}"],
                ["Tone", f"{la.sentiment.upper()} (net {tone}, {la.sentiment_source or 'n/a'})"],
                ["Words analysed", f"{la.total_words_analyzed:,}"]]
        out.append(_table(rows, [2.6 * inch, 2.6 * inch], mono_body=True))
        top = [w for w in la.hedging_words_found[:8]]
        if top:
            out.append(_p("Most frequent hedging terms: " + ", ".join(top), st["Small"]))

    if f.deception_alert and f.deception_reason:
        out.append(Spacer(1, 4))
        out.append(Paragraph(f'<font color="{_hex(BRAND_RED)}"><b>DECEPTION ALERT:</b> {escape(f.deception_reason)}</font>', st["Body"]))
    if f.red_flags:
        out.append(_p(f"Red flags ({len(f.red_flags)})", st["Sub"]))
        rows = [["#", "Sev.", "Category", "Explanation"]]
        for i, flag in enumerate(f.red_flags[:10], 1):
            cat = flag.category + (" (unverified quote)" if flag.verified is False else "")
            rows.append([str(i), str(flag.severity), _p(cat, st["Cell"]), _p(flag.explanation[:300], st["Cell"])])
        out.append(_table(rows, [0.3 * inch, 0.45 * inch, 1.2 * inch, 4.3 * inch], header_bg=colors.HexColor("#fef2f2")))
    return out


def _call(audit: ForensicAuditResponse, st) -> list:
    call = audit.earnings_call
    out = [_p(SECTIONS[5], st["Section"])]
    if not call or not call.available:
        return out + [_p((call.note if call else None) or "Earnings call data unavailable for this ticker.", st["Body"])]
    out.append(_p(call.source_label or "", st["Small"]))
    transcript = call.source == "alpha_vantage"

    def cells(seg):
        if seg is None:
            return ["—"] * 5
        tone = "—" if seg.net_tone is None else f"{seg.net_tone:+.2f}"
        return [seg.sentiment.upper(), tone, f"{seg.hedging_score:.1f}", f"{seg.evasion_score:.1f}", f"{seg.words:,}"]

    rows = [["Section", "Tone", "Net tone", "Hedging", "Evasion", "Words"],
            ["Prepared remarks" if transcript else "Press release", *cells(call.prepared)]]
    if transcript:
        rows.append(["Analyst Q&A answers", *cells(call.qa)])
    out += [Spacer(1, 4), _table(rows, [1.8 * inch, 0.9 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch],
                                 header_bg=colors.HexColor("#fffbeb"), mono_body=True)]
    tiles = [("Call candor", str(call.candor_score) if call.candor_score is not None else "N/A",
              _score_color(call.candor_score, 75, 50), "out of 100")]
    if transcript:
        tiles += [
            ("Analyst questions", str(call.analyst_questions), BRAND_DARK, "answered"),
            ("Deflection rate", _pct(call.deflection_rate, 0), _score_color(100 - (call.deflection_rate or 0) * 100, 90, 80), "of answers"),
            ("Tone shift", f"{call.tone_shift:+.2f}" if call.tone_shift is not None else "—", BRAND_DARK, "Q&A vs script"),
        ]
    out += [Spacer(1, 8), _metric_tiles(tiles, st)]
    if call.flags:
        out.append(_p("Findings", st["Sub"]))
        out += [_p(f"• {flag}", st["Body"]) for flag in call.flags]
    if call.exchanges:
        out.append(_p("Notable analyst exchanges", st["Sub"]))
        rows = [["Analyst", "Question", "Answer (excerpt)"]]
        for e in call.exchanges:
            tag = f'[Deflection: "{e.deflection_phrase}"] ' if e.deflection_phrase else "[Brief answer] " if e.brief else ""
            rows.append([
                _p(e.analyst, st["Cell"]),
                _p(e.question[:260] + ("…" if len(e.question) > 260 else ""), st["Cell"]),
                _p(tag + e.answer_excerpt[:300], st["Cell"]),
            ])
        out.append(_table(rows, [1.1 * inch, 2.4 * inch, 2.8 * inch]))
    if call.executives:
        out.append(_p("Executives on the call: " + " · ".join(call.executives), st["Small"]))
    return out


def _stress_test(mc: MonteCarloResult | None, st) -> list:
    out = [_p(SECTIONS[6], st["Section"])]
    if mc is None:
        return out + [_p("Stress test not run (no revenue data).", st["Body"])]
    if mc.parameter_source:
        out.append(_p(f"Assumptions — {mc.parameter_source}.", st["Body"]))
    out += [Spacer(1, 6), _metric_tiles([
        ("Median in 5 years", _money(mc.median_final_revenue), BRAND_DARK, f"from {_money(mc.initial_revenue)} today"),
        ("Bad case (5th pct.)", _money(mc.percentile_5), BRAND_RED, "1 in 20 paths below this"),
        ("Good case (95th pct.)", _money(mc.percentile_95), BRAND_GREEN, "1 in 20 paths above this"),
        ("Decline > 20%", _pct(mc.probability_of_decline), _score_color(100 - (mc.probability_of_decline or 0) * 100, 85, 70),
         "probability"),
    ], st)]
    rows = [["Year", "5th pct.", "25th pct.", "Median", "75th pct.", "95th pct."]] + [
        [str(p["year"]), _money(p["p5"]), _money(p["p25"]), _money(p["median"]), _money(p["p75"]), _money(p["p95"])]
        for p in mc.sample_paths
    ]
    out += [_p("Revenue percentile bands by year", st["Sub"]),
            _table(rows, [0.6 * inch] + [1.1 * inch] * 5, mono_body=True, align_right_from=1),
            _p(f"{mc.num_simulations:,} simulated paths; geometric Brownian motion with annual drift "
               f"{(mc.growth_mean or 0) * 100:.1f}% and volatility {(mc.growth_std or 0) * 100:.1f}%.", st["Small"])]
    return out


def _risk_register(audit: ForensicAuditResponse, st) -> list:
    out = [_p(SECTIONS[7], st["Section"])]
    if not audit.risk_register:
        return out + [_p("No material risks were flagged by any of the analyses.", st["Body"])]
    sev_color = {"high": BRAND_RED, "medium": BRAND_AMBER, "low": BRAND_GRAY}
    rows = [["Severity", "Area", "Finding"]] + [
        [Paragraph(f'<font color="{_hex(sev_color[r.severity])}"><b>{r.severity.upper()}</b></font>', st["Cell"]),
         _p(r.area, st["Cell"]), _p(r.finding, st["Cell"])]
        for r in audit.risk_register
    ]
    counts = {s: sum(1 for r in audit.risk_register if r.severity == s) for s in ("high", "medium", "low")}
    out.append(_p(f"{counts['high']} high, {counts['medium']} medium and {counts['low']} low severity findings.", st["Body"]))
    out += [Spacer(1, 4), _table(rows, [0.8 * inch, 1.4 * inch, 4.1 * inch])]
    return out


def _methodology(st) -> list:
    out = [_p(SECTIONS[8], st["Section"])]
    rows = [["Model", "How it works"]] + [[_p(m, st["Cell"]), _p(d, st["Cell"])] for m, d in METHODS]
    out += [_table(rows, [1.4 * inch, 4.9 * inch]), _p("References", st["Sub"])]
    out += [Paragraph(f"<b>{escape(a)}</b> {escape(t)}", st["Body"]) for a, t in REFERENCES]
    return out


def _sources(audit: ForensicAuditResponse, st) -> list:
    out = [_p(SECTIONS[9], st["Section"])]
    out += [_p(f"• {s}", st["Body"]) for s in audit.data_sources]
    if not audit.gemini_active and audit.ai_error:
        out.append(_p(f"• AI red-flag scan not used: {audit.ai_error}", st["Body"]))
    out += [Spacer(1, 8), _p(
        "Disclaimer: this report is generated automatically from public data (SEC EDGAR, Yahoo Finance, Alpha "
        "Vantage) by rule-based models for educational purposes. It is not investment advice. Figures may contain "
        "errors from source data or extraction; verify against the original filings before relying on them.",
        st["Small"],
    )]
    return out


def generate_pdf_report(audit: ForensicAuditResponse) -> bytes:
    """Build the research report for a completed audit and return the PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
        title=f"Alpha-Guard Research Report — {audit.ticker}",
        author=", ".join(n for n, _ in REPORT_TEAM),
    )
    st = _styles()
    company = audit.company_name or audit.ticker

    def section(flowables: list) -> list:
        # Keep each heading with the content that follows it, so no heading is
        # stranded at the bottom of a page
        return [KeepTogether(flowables[:3])] + flowables[3:] + [Spacer(1, 14)]

    body = [
        _executive_summary(audit, st),
        _snapshot(audit, st),
        _trends(audit, st),
        _health(audit, st),
        _forensics(audit, st),
        _call(audit, st),
        _stress_test(audit.monte_carlo, st),
        _risk_register(audit, st),
    ]
    story = _cover(audit, st)
    for flowables in body:
        story += section(flowables)
    story += [PageBreak()] + section(_methodology(st))
    story += [KeepTogether(_sources(audit, st))]

    def later(canvas, d):
        _on_page(canvas, d, audit.ticker, company)

    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=later)
    return buffer.getvalue()


# ──────────────────────────────────────────────
#  API Endpoint
# ──────────────────────────────────────────────

class PDFReportRequest(BaseModel):
    """Request to generate a downloadable PDF report."""
    ticker: str = Field(..., description="Stock ticker symbol")
    include_monte_carlo: bool = Field(default=True, description="Include the revenue stress test")
    mc_simulations: int = Field(default=1000, ge=100, le=10000)
    mc_horizon_years: int = Field(default=5, ge=1, le=10)


@router.post(
    "/generate-pdf",
    summary="Generate PDF Research Report",
    description=(
        "Generates a multi-page research report: investment conviction, company snapshot, financial "
        "trends, Z-Score, Truth Score, earnings call, stress test, risk register and methodology."
    ),
    dependencies=[Depends(rate_limit)],
)
async def api_generate_pdf(request: PDFReportRequest):
    """Generate and return a PDF report."""
    from forensic_analyzer import company_stress_test, run_forensic_pipeline

    # Same pipeline as the dashboard, so US and international tickers both work
    audit, financials = await run_forensic_pipeline(request.ticker)
    if not request.include_monte_carlo:
        audit.monte_carlo = None
    elif (request.mc_simulations, request.mc_horizon_years) != (1000, 5):
        audit.monte_carlo = company_stress_test(
            audit.ticker, financials, request.mc_simulations, request.mc_horizon_years,
        )

    pdf_bytes = generate_pdf_report(audit)
    safe_ticker = "".join(ch for ch in audit.ticker if ch.isalnum() or ch in ".-_")
    filename = f"AlphaGuard_{safe_ticker}_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
