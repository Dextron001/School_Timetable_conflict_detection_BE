"""Build a landscape GRID PDF timetable matching the institution PDF EXACTLY.

Matches the Precious Cornerstone University (PCU) lecture timetable format:
  - PCU logo at top-left
  - Title: Arial-Black 14pt black (3 lines) + "LECTURE TIME-TABLE (DRAFT ...)"
  - Two-row header: time slots (Times Bold 10pt) + "Course & Venue" (BoldItalic)
  - Day labels: MON, TUE, WED, THUR, FRI (Times Bold 10pt)
  - Cell format: COURSE_CODE (Venue) — Bold code + BoldItalic venue
  - BREAK column: "B R E A K" vertically
  - Empty cells: white space (breathing room)
  - Footer: "Signed: TTE committee" (Times Bold 12pt)
  - All colors: pure black (#000000) — no colored backgrounds
  - Page size: Letter landscape (792 × 612)
  - Grid lines: 1pt black borders
"""
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate, Image

from .models import CourseItem
from .seed import DAYS, FACULTIES

# ── Constants matching institution PDF ────────────────────────────────────
BLACK = colors.HexColor("#000000")
RED = colors.HexColor("#FF0000")  # For DRAFT label only

SLOT_HEADERS = [
    ("08:00", "09:00", "8 – 9am"),
    ("09:00", "10:00", "9 – 10am"),
    ("10:00", "11:00", "10 – 11am"),
    ("11:00", "12:00", "11 – 12 Noon"),
    ("12:00", "13:00", "12 – 1pm"),
    ("13:00", "14:00", "1 – 2pm"),
    ("14:00", "15:00", "2 – 3pm"),
    ("15:00", "16:00", "3 – 4pm"),
    ("16:00", "17:00", "4 – 5pm"),
]

TEACHING_SLOTS = [s for s in SLOT_HEADERS if s[2] != "12 – 1pm"]

DAY_SHORT = {"Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED",
             "Thursday": "THUR", "Friday": "FRI"}

# ── Locate logo (search multiple locations) ────────────────────────────────
_HERE = Path(__file__).resolve().parent  # .../backend/app/
_BACKEND = _HERE.parent                   # .../backend/
# Possible locations where the logo might be saved
_LOGO_SEARCH = [
    _BACKEND / "pcu logo update.png",           # backend/pcu_logo.png  (correct spot)
    _HERE / "pcu logo update.png",              # backend/app/pcu_logo.png  (common mistake)
    _BACKEND / "static" / "pcu logo update.png", # backend/static/pcu_logo.png
    _BACKEND / "assets" / "pcu logo update.png", # backend/assets/pcu_logo.png
]

LOGO_PATH = None
for candidate in _LOGO_SEARCH:
    if candidate.exists():
        LOGO_PATH = candidate
        print(f"[PDF] ✓ Logo found at: {candidate}")
        break

if LOGO_PATH is None:
    print(f"[PDF] ✗ Logo NOT found! Searching in: {_BACKEND}")
    print(f"[PDF]    Please save 'pcu logo update.png' in: {_BACKEND}")
    print(f"[PDF]    (or in: {_HERE})")
    print(f"[PDF]    PDF will be generated WITHOUT the logo.")


def _course_line(course, conflict_set):
    """Compact cell text matching institution format.
    COURSE_CODE in Bold + (Venue) in BoldItalic.
    """
    venue = course.description or "TBA"
    code = f'<font name="Times-Bold">{course.course_code}</font>'
    venue_part = f'<font name="Times-BoldItalic">({venue})</font>'
    if course.id in conflict_set:
        return f'<font color="#FF0000"><b>⚠ {course.course_code} ({venue})</b></font>'
    return f"{code} {venue_part}"


def build_timetable_pdf(
    courses: list[CourseItem],
    faculty_code: str,
    faculty_name: str,
    conflict_ids: list[int] | None = None,
) -> BytesIO:
    """Build a GRID-format PDF matching the institution timetable EXACTLY."""
    buffer = BytesIO()
    conflict_set = set(conflict_ids or [])

    page_w, page_h = landscape(letter)  # 792 × 612 — same as institution PDF

    margin_left = 20 * mm
    margin_right = 20 * mm
    margin_top = 10 * mm
    margin_bottom = 15 * mm
    usable_w = page_w - margin_left - margin_right

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=margin_left, rightMargin=margin_right,
        topMargin=margin_top, bottomMargin=margin_bottom,
    )

    story = []

    # ── Styles (matching institution PDF fonts) ────────────────────────
    title_style = ParagraphStyle(
        "Title", fontSize=14, leading=17, textColor=BLACK,
        fontName="Helvetica-Bold", alignment=1, spaceAfter=2,
    )
    draft_style = ParagraphStyle(
        "Draft", fontSize=16, leading=19, textColor=RED,
        fontName="Helvetica-Bold", alignment=1,
    )
    header_time_style = ParagraphStyle(
        "HeaderTime", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    header_sub_bold_style = ParagraphStyle(
        "HeaderSubBold", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    header_sub_italic_style = ParagraphStyle(
        "HeaderSubItalic", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-BoldItalic", alignment=1,
    )
    day_style = ParagraphStyle(
        "DayLabel", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    break_style = ParagraphStyle(
        "Break", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    cell_style = ParagraphStyle(
        "Cell", fontSize=10, leading=12, textColor=BLACK,
        fontName="Times-Roman",
    )
    footer_style = ParagraphStyle(
        "Footer", fontSize=12, leading=14, textColor=BLACK,
        fontName="Times-Bold", spaceBefore=12,
    )

    # ── Logo + Title block ────────────────────────────────────────────
    # Insert logo if it was found at startup
    if LOGO_PATH is not None and LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=65, height=60)
        # Place logo left, title text right — use a mini table
        title1 = Paragraph("PRECIOUS CORNERSTONE UNIVERSITY, IBADAN", title_style)
        title2 = Paragraph(
            f"{faculty_name} SECOND SEMESTER, 2025/2026 ACADEMIC SESSION", title_style)
        title3 = Paragraph("LECTURE TIME-TABLE <font color='#FF0000' size='16'><b>(DRAFT)</b></font>", title_style)

        title_table = Table(
            [[logo, [title1, Spacer(1, 2), title2, Spacer(1, 4), title3]]],
            colWidths=[70, usable_w - 70],
        )
        title_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(title_table)
    else:
        story.append(Paragraph("PRECIOUS CORNERSTONE UNIVERSITY, IBADAN", title_style))
        story.append(Paragraph(
            f"{faculty_name} SECOND SEMESTER, 2025/2026 ACADEMIC SESSION", title_style))
        story.append(Paragraph("LECTURE TIME-TABLE <font color='#FF0000' size='16'><b>(DRAFT)</b></font>", title_style))

    story.append(Spacer(1, 8))

    # ── Build grid ──────────────────────────────────────────────────────
    grid = {}
    for day in DAYS:
        grid[day] = {}
        for start, end, _ in TEACHING_SLOTS:
            grid[day][start] = []

    for c in courses:
        if c.day_of_the_week in grid and c.time_start in grid[c.day_of_the_week]:
            grid[c.day_of_the_week][c.time_start].append(c)

    # Sort within each cell by department then level
    for day in DAYS:
        for start in grid[day]:
            grid[day][start].sort(key=lambda c: (c.department, c.academic_level))

    # ── Table data ──────────────────────────────────────────────────────
    # Row 0: time slot labels (header row 1)
    # Row 1: "Course & Venue" sub-headers (header row 2)
    # Rows 2-6: MON through FRI

    header1 = ["DAY/\nTime"] + [
        Paragraph(s[2], header_time_style) for s in SLOT_HEADERS
    ]

    header2 = [""] + [
        Paragraph("Course &<br/>Venue", header_sub_italic_style) if s[2] == "12 – 1pm"
        else Paragraph("Course &<br/>Venue", header_sub_italic_style)
        for s in SLOT_HEADERS
    ]

    data = [header1, header2]

    for day in DAYS:
        row = [Paragraph(DAY_SHORT[day], day_style)]
        for start, end, label in SLOT_HEADERS:
            if label == "12 – 1pm":
                row.append(Paragraph("B<br/>R<br/>E<br/>A<br/>K", break_style))
            else:
                cell_courses = grid[day].get(start, [])
                if cell_courses:
                    lines = [_course_line(c, conflict_set) for c in cell_courses]
                    row.append(Paragraph("<br/>".join(lines), cell_style))
                else:
                    row.append("")  # empty cell = breathing space
        data.append(row)

    # ── Column widths ───────────────────────────────────────────────────
    day_col_w = 55
    num_cols = len(SLOT_HEADERS)
    slot_col_w = (usable_w - day_col_w) / num_cols
    col_widths = [day_col_w] + [slot_col_w] * num_cols

    # ── Build table ─────────────────────────────────────────────────────
    table = Table(data, colWidths=col_widths, repeatRows=2)

    style_cmds = [
        # ── Header rows (rows 0 and 1) ──────────────────────────────
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Times-BoldItalic"),
        ("FONTSIZE", (0, 0), (-1, 1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 1), 3),

        # ── Grid lines: pure black 1pt ──────────────────────────────
        ("GRID", (0, 0), (-1, -1), 1, BLACK),
        ("BOX", (0, 0), (-1, -1), 1.5, BLACK),

        # ── Day column ──────────────────────────────────────────────
        ("FONTNAME", (0, 2), (0, -1), "Times-Bold"),
        ("FONTSIZE", (0, 2), (0, -1), 10),
        ("ALIGN", (0, 2), (0, -1), "CENTER"),
        ("VALIGN", (0, 2), (0, -1), "MIDDLE"),

        # ── Body cells ──────────────────────────────────────────────
        ("VALIGN", (1, 2), (-1, -1), "TOP"),
        ("TOPPADDING", (1, 2), (-1, -1), 2),
        ("BOTTOMPADDING", (1, 2), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),

        # ── Line below header rows ──────────────────────────────────
        ("LINEBELOW", (0, 1), (-1, 1), 1.5, BLACK),
    ]

    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    # ── Footer ──────────────────────────────────────────────────────────
    story.append(Paragraph("Signed: TTE committee", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer