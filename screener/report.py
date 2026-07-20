"""PDF report generation (reportlab)."""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

F = "Helvetica"
ST_TITLE = ParagraphStyle("t", fontName=F, fontSize=17, leading=22, spaceAfter=6)
ST_H = ParagraphStyle("h", fontName=F, fontSize=12.5, leading=17,
                      spaceBefore=10, spaceAfter=4)
ST_P = ParagraphStyle("p", fontName=F, fontSize=9.5, leading=14)
ST_SMALL = ParagraphStyle("s", fontName=F, fontSize=7.5, leading=10,
                          textColor=colors.grey)


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), F, 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f2f6fa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build_pdf(data: dict, out_path: str) -> None:
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    story = []
    story.append(Paragraph(
        f"S&amp;P 500 Dual-List Screen — {data['date']}", ST_TITLE))
    st = data.get("stats", {})
    failed = st.get("failed", [])
    story.append(Paragraph(
        f"Scanned {st.get('total', 0)} constituents, {st.get('ok', 0)} OK, "
        f"{len(failed)} skipped"
        + (f" ({', '.join(failed[:15])})" if failed else "")
        + ". Timeframe: 2-hour bars synthesized from Yahoo Finance 1-hour "
          "data (regular session only).", ST_P))
    story.append(Spacer(1, 4))

    cross = data.get("cross", [])
    g = [c for c in cross if c["type"] == "golden"]
    d = [c for c in cross if c["type"] == "death"]
    story.append(Paragraph(
        f"List 1 · EMA36(close) × EMA90(open) cross within last trading day "
        f"— golden {len(g)} / death {len(d)}", ST_H))
    if cross:
        rows = [["Ticker", "Company", "Type", "Bar time", "EMA36", "EMA90", "Close"]]
        for c in sorted(cross, key=lambda x: (x["type"], x["ticker"])):
            rows.append([c["ticker"], c["name"][:28], c["type"],
                         c["barTime"].replace("T", " "),
                         f"{c['ema36']:.2f}", f"{c['ema90']:.2f}",
                         f"{c['close']:.2f}"])
        story.append(_table(rows, [16 * mm, 52 * mm, 14 * mm, 30 * mm,
                                   20 * mm, 20 * mm, 20 * mm]))
    else:
        story.append(Paragraph("No qualifying crosses today.", ST_P))

    bb = data.get("bb", [])
    up = [b for b in bb if b["type"] == "above"]
    dn = [b for b in bb if b["type"] == "below"]
    story.append(Paragraph(
        f"List 2 · Close beyond BB(90, SMA, 3) with Beta(300) regime "
        f"confirmation — above {len(up)} / below {len(dn)}", ST_H))
    if bb:
        rows = [["Ticker", "Company", "Side", "Close", "Upper", "Lower",
                 "Beta", "Beta mean"]]
        for b in sorted(bb, key=lambda x: (x["type"], x["ticker"])):
            rows.append([b["ticker"], b["name"][:24], b["type"],
                         f"{b['close']:.2f}", f"{b['upper']:.2f}",
                         f"{b['lower']:.2f}", f"{b['beta']:.3f}",
                         f"{b['betaMean']:.3f}"])
        story.append(_table(rows, [16 * mm, 46 * mm, 14 * mm, 19 * mm,
                                   19 * mm, 19 * mm, 17 * mm, 17 * mm]))
    else:
        story.append(Paragraph(
            "No qualifying breakouts today (±3σ Bollinger breaks with beta "
            "confirmation are rare by design; an empty list is normal).", ST_P))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Data: Yahoo Finance 1h bars resampled to 2h (regular session). "
        "List 2 condition: close above upper band AND Beta(300) above its "
        "252-bar mean, or close below lower band AND beta below its mean. "
        "This report is a mechanical screening output, not investment advice.",
        ST_SMALL))
    doc.build(story)
