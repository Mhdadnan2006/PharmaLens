from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "PharmaLens_Documentation.md"
OUTPUT = ROOT / "PharmaLens_Documentation.pdf"
ASSETS = ROOT / "documentation_assets"

PAGE_WIDTH, PAGE_HEIGHT = A4
FRAME_LEFT = 72.0
FRAME_RIGHT = 37.7
FRAME_TOP = 72.0
FRAME_BOTTOM = 82.344
BODY_WIDTH = 485.6

FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_FILES = {
    "TimesNewRoman": "times.ttf",
    "TimesNewRoman-Bold": "timesbd.ttf",
    "TimesNewRoman-Italic": "timesi.ttf",
    "TimesNewRoman-BoldItalic": "timesbi.ttf",
    "Calibri": "calibri.ttf",
}
for font_name, filename in FONT_FILES.items():
    font_path = FONT_DIR / filename
    if font_path.exists():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

SERIF = "TimesNewRoman" if "TimesNewRoman" in pdfmetrics.getRegisteredFontNames() else "Times-Roman"
SERIF_BOLD = "TimesNewRoman-Bold" if "TimesNewRoman-Bold" in pdfmetrics.getRegisteredFontNames() else "Times-Bold"
SERIF_ITALIC = "TimesNewRoman-Italic" if "TimesNewRoman-Italic" in pdfmetrics.getRegisteredFontNames() else "Times-Italic"
SERIF_BOLD_ITALIC = "TimesNewRoman-BoldItalic" if "TimesNewRoman-BoldItalic" in pdfmetrics.getRegisteredFontNames() else "Times-BoldItalic"
FOOTER_FONT = "Calibri" if "Calibri" in pdfmetrics.getRegisteredFontNames() else "Helvetica"


def esc(value: str) -> str:
    return html.escape(value, quote=False)


def inline_markup(value: str) -> str:
    value = esc(value)
    value = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", value)
    return value


class ReportDocument(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=FRAME_LEFT,
            rightMargin=PAGE_WIDTH - 557.62,
            topMargin=FRAME_TOP,
            bottomMargin=FRAME_BOTTOM,
            title="PharmaLens Documentation",
            author="PharmaLens project",
        )
        frame = Frame(
            FRAME_LEFT,
            FRAME_BOTTOM,
            BODY_WIDTH,
            PAGE_HEIGHT - FRAME_TOP - FRAME_BOTTOM,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="academic", frames=[frame], onPage=draw_page)] )


def draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.black)
    canvas.setFont(SERIF_BOLD_ITALIC, 12)
    canvas.drawString(72.0, 794.8, "B.Voc Data Science")
    canvas.drawCentredString(PAGE_WIDTH / 2, 794.8, "Main Project")
    canvas.drawRightString(547.7, 794.8, "Batch 2023 - 2026")

    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.72)
    # The reference uses a narrow double frame with reinforced corners.
    for x in (63.624, 66.624, 67.344):
        canvas.line(x, 82.344, x, 770.88)
    for x in (557.62, 560.62, 561.34):
        canvas.line(x, 82.344, x, 770.88)
    for y in (770.88, 772.32, 775.32):
        canvas.line(68.064, y, 557.62, y)
    for y in (77.904, 79.344, 82.344):
        canvas.line(68.064, y, 557.62, y)

    canvas.setFont(SERIF_BOLD_ITALIC, 11)
    canvas.drawString(77.8, 60.3, "DEPARTMENT OF DATA SCIENCE")
    canvas.setFont(FOOTER_FONT, 9)
    canvas.drawString(543.3, 61.0, str(doc.page))
    canvas.restoreState()


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=SERIF_BOLD, fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=10),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=SERIF_BOLD_ITALIC, fontSize=12, leading=16, alignment=TA_CENTER, spaceAfter=8),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=SERIF_BOLD, fontSize=15, leading=18, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8, keepWithNext=True),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=SERIF_BOLD, fontSize=12, leading=16, alignment=TA_LEFT, spaceBefore=5, spaceAfter=3, keepWithNext=True),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName=SERIF_BOLD, fontSize=12, leading=16, spaceBefore=4, spaceAfter=2, keepWithNext=True),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=SERIF, fontSize=12, leading=16, alignment=TA_JUSTIFY, firstLineIndent=36, spaceAfter=5),
        "body_no_indent": ParagraphStyle("body_no_indent", parent=base["BodyText"], fontName=SERIF, fontSize=12, leading=16, alignment=TA_JUSTIFY, spaceAfter=5),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontName=SERIF, fontSize=12, leading=16, leftIndent=18, firstLineIndent=-10, spaceAfter=2),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName=SERIF_ITALIC, fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
        "code": ParagraphStyle("code", parent=base["Code"], fontName="Courier", fontSize=7.2, leading=9.2, leftIndent=4, rightIndent=4, backColor=colors.HexColor("#f3f4f6"), borderColor=colors.HexColor("#d1d5db"), borderWidth=0.4, borderPadding=5, spaceBefore=3, spaceAfter=5),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName=SERIF, fontSize=9.5, leading=12, alignment=TA_LEFT),
    }


def table_from_lines(lines, sty):
    rows = []
    for line in lines:
        if not line.strip() or set(line.strip()) <= {"-", "|", ":", " "}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append([Paragraph(inline_markup(cell), sty["small"]) for cell in cells])
    if not rows:
        return None
    count = max(len(row) for row in rows)
    rows = [row + [""] * (count - len(row)) for row in rows]
    widths = [BODY_WIDTH / count] * count
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def build():
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines()
    sty = styles()
    story = []
    in_code = False
    code_lines = []
    table_lines = []
    i = 0
    title_done = False
    started_report = False

    def flush_table():
        nonlocal table_lines
        if table_lines:
            table = table_from_lines(table_lines, sty)
            if table:
                story.extend([Spacer(1, 3), table, Spacer(1, 8)])
            table_lines = []

    while i < len(lines):
        raw = lines[i].rstrip()
        if raw.startswith("```"):
            flush_table()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), sty["code"]))
                code_lines = []
            in_code = not in_code
            i += 1
            continue
        if in_code:
            code_lines.append(raw)
            i += 1
            continue
        if raw.startswith("|"):
            table_lines.append(raw)
            i += 1
            continue
        flush_table()
        if not raw.strip():
            i += 1
            continue
        if raw == "---":
            story.append(Spacer(1, 4))
            i += 1
            continue
        image_match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", raw)
        if image_match:
            caption, rel = image_match.groups()
            image_path = ROOT / rel
            if image_path.exists():
                image = Image(str(image_path))
                image._restrictSize(BODY_WIDTH, 125 * mm)
                story.extend([Spacer(1, 4), image, Paragraph(inline_markup(caption), sty["caption"])])
            i += 1
            continue
        if raw.startswith("# "):
            heading = raw[2:].strip()
            if not started_report and heading.upper() != "ABSTRACT":
                i += 1
                continue
            if not started_report:
                started_report = True
            elif title_done:
                story.append(PageBreak())
            title_done = True
            heading = re.sub(r"^\d+\.\s+", "", heading)
            story.append(Paragraph(inline_markup(heading.upper()), sty["h1"]))
            i += 1
            continue
        if not started_report:
            i += 1
            continue
        if raw.startswith("## "):
            story.append(Paragraph(inline_markup(raw[3:].strip()), sty["h2"]))
            i += 1
            continue
        if raw.startswith("### "):
            story.append(Paragraph(inline_markup(raw[4:].strip()), sty["h3"]))
            i += 1
            continue
        if raw.startswith("**") and raw.endswith("**"):
            story.append(Paragraph(inline_markup(raw), sty["subtitle"]))
            i += 1
            continue
        if raw.startswith("- ") or re.match(r"\d+\. ", raw):
            marker, item = (raw.split(" ", 1) if raw.startswith("- ") else re.split(r"\. ", raw, maxsplit=1))
            prefix = "&#8226;" if raw.startswith("- ") else f"{marker}."
            story.append(Paragraph(f"{prefix} {inline_markup(item)}", sty["bullet"]))
            i += 1
            continue
        story.append(Paragraph(inline_markup(raw), sty["body"]))
        i += 1

    flush_table()
    flowable_count = len(story)
    doc = ReportDocument(str(OUTPUT))
    doc.build(story)
    print(f"Wrote {OUTPUT} with {flowable_count} flowables")


if __name__ == "__main__":
    build()
