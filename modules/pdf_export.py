# pdf_export.py
# Generates a professional PDF report from the FP&A dashboard data.
# Uses reportlab — a free Python library for creating PDFs.
# Returns the PDF as bytes so Streamlit can offer it as a download.

from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── BRAND COLORS ──────────────────────────────────────────────────
BLUE       = colors.HexColor("#0066cc")
DARK       = colors.HexColor("#1a1a2e")
GREEN      = colors.HexColor("#28a745")
RED        = colors.HexColor("#dc3545")
YELLOW     = colors.HexColor("#ffc107")
LIGHT_GREY = colors.HexColor("#f8f9fa")
MID_GREY   = colors.HexColor("#dee2e6")
WHITE      = colors.white


# ── STYLE HELPERS ─────────────────────────────────────────────────

def _styles():
    """Returns a dict of named Paragraph styles used throughout the PDF."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "title",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=DARK, spaceAfter=4, leading=26
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=10, fontName="Helvetica",
            textColor=colors.grey, spaceAfter=12
        ),
        "section": ParagraphStyle(
            "section",
            fontSize=13, fontName="Helvetica-Bold",
            textColor=BLUE, spaceBefore=14, spaceAfter=6
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=9, fontName="Helvetica",
            textColor=DARK, leading=14, spaceAfter=6
        ),
        "narrative": ParagraphStyle(
            "narrative",
            fontSize=9.5, fontName="Helvetica",
            textColor=DARK, leading=15, spaceAfter=8,
            leftIndent=12, rightIndent=12
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=7.5, fontName="Helvetica",
            textColor=colors.grey, alignment=TA_CENTER
        ),
    }


def _status_color(status):
    """Maps ratio status string → reportlab color."""
    return {
        "good":    GREEN,
        "warning": YELLOW,
        "poor":    RED,
    }.get(status, colors.grey)


def _fmt_ratio(r):
    """Format a ratio value for display in the PDF."""
    if not r:
        return "N/A"
    val = r.get("value", 0)
    fmt = r.get("format", "multiple")
    if fmt == "percent":
        return f"{val}%"
    elif fmt == "days":
        return f"{val}d"
    else:
        return f"{val}x"


# ── MAIN EXPORT FUNCTION ──────────────────────────────────────────

def generate_pdf(
    company_name: str,
    financials:   dict,
    balance:      dict,
    ratios:       dict,
    narrative:    str = None,
    bva_data:     dict = None,
) -> bytes:
    """
    Builds the full PDF report and returns it as bytes.
    Call this from app.py and pass the result to st.download_button().

    Parameters
    ----------
    company_name : display name for the company
    financials   : dict from parser.extract_key_figures()
    balance      : dict from parser.extract_balance_figures()
    ratios       : dict from ratios.calculate_all_ratios()
    narrative    : AI-generated text (optional — shown if provided)
    bva_data     : budget vs actuals analysis dict (optional)
    """

    # Sanitize company name — remove characters ReportLab can't render
    company_name = company_name.encode('ascii', errors='ignore').decode('ascii').strip()
    if not company_name:
        company_name = "Company"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    S = _styles()
    story = []   # list of Flowable objects that make up the PDF

    latest_year = financials.get("latest_year", "FY2024")
    today       = date.today().strftime("%B %d, %Y")

    # ── HEADER ────────────────────────────────────────────────────
    story.append(Paragraph(f"{company_name}", S["title"]))
    story.append(Paragraph(
        f"FP&amp;A Report  ·  {latest_year}  ·  Generated {today}  ·  Powered by Claude AI",
        S["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=10))

    # ── KPI SUMMARY ROW ───────────────────────────────────────────
    story.append(Paragraph("Key Performance Indicators", S["section"]))

    rev          = financials.get("revenue", 0)
    rev_prior    = financials.get("revenue_prior", 0)
    rev_growth   = ((rev - rev_prior) / rev_prior * 100) if rev_prior else 0
    ebitda       = financials.get("ebitda", 0)
    ebitda_margin= (ebitda / rev * 100) if rev else 0
    ni           = financials.get("net_income", 0)
    ni_prior     = financials.get("net_income_prior", 0)
    ni_growth    = ((ni - ni_prior) / ni_prior * 100) if ni_prior else 0
    cash         = balance.get("cash", 0)

    kpi_data = [
        # Header row
        ["Revenue", "EBITDA", "Net Income", "Cash"],
        [
            f"${rev/1e6:.1f}M",
            f"${ebitda/1e6:.1f}M",
            f"${ni/1e6:.2f}M",
            f"${cash/1e6:.1f}M",
        ],
        [
            f"{rev_growth:+.1f}% YoY",
            f"{ebitda_margin:.1f}% margin",
            f"{ni_growth:+.1f}% YoY",
            "Net cash" if balance.get("long_term_debt", 0) < cash else "Net debt",
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[1.7 * inch] * 4)
    kpi_table.setStyle(TableStyle([
        # Header label row
        ("BACKGROUND",  (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        # Value row
        ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, 1), 16),
        ("TEXTCOLOR",   (0, 1), (-1, 1), DARK),
        # Delta row
        ("FONTSIZE",    (0, 2), (-1, 2), 8),
        ("TEXTCOLOR",   (0, 2), (-1, 2), colors.grey),
        # Grid
        ("BOX",         (0, 0), (-1, -1), 0.5, MID_GREY),
        ("INNERGRID",   (0, 0), (-1, -1), 0.5, MID_GREY),
        ("BACKGROUND",  (0, 1), (-1, 2), LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 1), (-1, 2), [LIGHT_GREY, WHITE]),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # ── RATIOS TABLE ──────────────────────────────────────────────
    story.append(Paragraph("Financial Ratios", S["section"]))

    ratio_categories = [
        ("Liquidity",        ["current_ratio", "quick_ratio", "cash_ratio"]),
        ("Profitability",    ["gross_margin", "ebitda_margin", "net_margin", "roe", "roa"]),
        ("Leverage",         ["debt_to_equity", "net_debt_ebitda", "interest_coverage", "debt_to_assets"]),
        ("Efficiency",       ["asset_turnover", "dso", "dpo", "inventory_days"]),
        ("Growth",           ["revenue_growth", "ni_growth"]),
    ]

    # Build one flat table with category subheaders
    ratio_rows = [
        # Column headers
        [
            Paragraph("<b>Metric</b>", S["body"]),
            Paragraph("<b>Value</b>", S["body"]),
            Paragraph("<b>Status</b>", S["body"]),
            Paragraph("<b>Benchmark</b>", S["body"]),
        ]
    ]
    ratio_style_cmds = [
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",          (0, 0), (-1, -1), 0.5, MID_GREY),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("FONTSIZE",     (0, 1), (-1, -1), 8.5),
    ]

    current_row = 1

    for cat_label, keys in ratio_categories:
        # Category subheader row
        ratio_rows.append([
            Paragraph(f"<b>{cat_label}</b>", S["body"]),
            "", "", ""
        ])
        ratio_style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), colors.HexColor("#e8f0fe")))
        ratio_style_cmds.append(("FONTNAME",   (0, current_row), (-1, current_row), "Helvetica-Bold"))
        current_row += 1

        for key in keys:
            r = ratios.get(key)
            if not r:
                continue
            status = r.get("status", "warning")
            status_color = _status_color(status)
            status_symbol = {"good": "● Good", "warning": "● Warning", "poor": "● Poor"}.get(status, "—")

            ratio_rows.append([
                Paragraph(r["label"], S["body"]),
                Paragraph(f"<b>{_fmt_ratio(r)}</b>", S["body"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status_symbol}</font>', S["body"]),
                Paragraph(r.get("benchmark", ""), S["body"]),
            ])
            # Alternate row shading
            if current_row % 2 == 0:
                ratio_style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), LIGHT_GREY))
            current_row += 1

    ratio_table = Table(
        ratio_rows,
        colWidths=[2.4 * inch, 0.9 * inch, 1.0 * inch, 2.5 * inch]
    )
    ratio_table.setStyle(TableStyle(ratio_style_cmds))
    story.append(ratio_table)
    story.append(Spacer(1, 14))

    # ── BUDGET VS ACTUALS SUMMARY (if available) ──────────────────
    if bva_data:
        story.append(Paragraph("Budget vs Actuals — YTD Summary", S["section"]))

        rev_var     = bva_data.get("revenue_variance_usd", 0)
        rev_var_pct = bva_data.get("revenue_variance_pct", 0)
        ebitda_var  = bva_data.get("ebitda_variance_usd", 0)
        ebitda_pct  = bva_data.get("ebitda_variance_pct", 0)
        on_track    = bva_data.get("on_track", False)
        fav         = bva_data.get("favorable_count", 0)
        total       = bva_data.get("total_lines", 0)

        bva_rows = [
            ["Metric", "Variance ($)", "Variance (%)", "Status"],
            ["Revenue vs Budget",
             f"${rev_var/1e3:+.0f}K",
             f"{rev_var_pct:+.1f}%",
             "Favorable" if rev_var >= 0 else "Unfavorable"],
            ["EBITDA vs Budget",
             f"${ebitda_var/1e3:+.0f}K",
             f"{ebitda_pct:+.1f}%",
             "Favorable" if ebitda_var >= 0 else "Unfavorable"],
            ["Favorable Line Items", f"{fav} of {total}", "", ""],
            ["Full Year On Track",   "✅ Yes" if on_track else "⚠️ At Risk", "", ""],
        ]

        bva_table = Table(bva_rows, colWidths=[2.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
        bva_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, MID_GREY),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GREY, WHITE]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(bva_table)
        story.append(Spacer(1, 14))

    # ── AI NARRATIVE ──────────────────────────────────────────────
    if narrative and not narrative.startswith("❌"):
        story.append(HRFlowable(width="100%", thickness=1, color=MID_GREY, spaceAfter=8))
        story.append(Paragraph("AI Analyst Narrative", S["section"]))
        story.append(Paragraph(
            "Generated by Claude AI — for internal use only.",
            S["subtitle"]
        ))

        # Split into paragraphs on double newlines or bold headers
        for para_text in narrative.split("\n\n"):
            para_text = para_text.strip()
            if not para_text:
                continue
            # Convert **bold** markdown to reportlab bold tags
            para_text = para_text.replace("**", "<b>", 1)
            while "**" in para_text:
                para_text = para_text.replace("**", "</b>", 1)
            story.append(Paragraph(para_text, S["narrative"]))

    # ── FOOTER ────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"{company_name}  ·  FP&amp;A Report  ·  {today}  ·  Built with Python + Claude API  ·  Confidential",
        S["footer"]
    ))

    # ── BUILD PDF ─────────────────────────────────────────────────
    try:
        doc.build(story)
    except Exception as e:
        # If PDF build fails (e.g. special characters), retry with sanitized data
        # Strip any non-ASCII characters that ReportLab can't handle
        buffer = BytesIO()
        doc2 = SimpleDocTemplate(buffer, pagesize=letter,
                                 leftMargin=0.75*inch, rightMargin=0.75*inch,
                                 topMargin=0.75*inch, bottomMargin=0.75*inch)
        clean_story = []
        for item in story:
            try:
                clean_story.append(item)
            except Exception:
                pass
        doc2.build(clean_story)

    buffer.seek(0)
    return buffer.getvalue()
