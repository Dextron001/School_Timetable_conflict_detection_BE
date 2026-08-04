"""Build a landscape GRID PDF timetable matching the institution PDF EXACTLY.

Matches the Precious Cornerstone University (PCU) lecture timetable format:
  - PCU logo at top-left
  - Title: Arial-Black 14pt black (3 lines) + "LECTURE TIME-TABLE (DRAFT ...)"
  - Two-row header: time slots (Times Bold 10pt) + "Course & Venue" (BoldItalic)
  - Day labels: MON, TUE, WED, THUR, FRI (Times Bold 10pt)
  - Cell format: COURSE_CODE (Venue) — Bold code + BoldItalic venue
  - BREAK column: "B R E A K" vertically
  - Multi-hour courses MERGE across 2 adjacent columns (SPAN command)
  - 2hr course = one merged cell spanning 2 hour-columns
  - 1hr course = single normal cell
  - When 1hr and 2hr courses share a time block, they are split into
    separate rows within the same day — 2hr courses in a merged row,
    1hr courses in a separate row with individual columns.
  - Empty cells: white space (breathing room)
  - Footer: "Signed: TTE committee" (Times Bold 12pt)
  - All colors: pure black (#000000) — no colored backgrounds
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
RED = colors.HexColor("#FF0000")

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

DAY_SHORT = {"Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED",
             "Thursday": "THUR", "Friday": "FRI"}

# ── Locate logo ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
_LOGO_SEARCH = [
    _BACKEND / "pcu_logo.png",
    _HERE / "pcu_logo.png",
    _BACKEND / "static" / "pcu_logo.png",
    _BACKEND / "assets" / "pcu_logo.png",
]

LOGO_PATH = None
for candidate in _LOGO_SEARCH:
    if candidate.exists():
        LOGO_PATH = candidate
        print(f"[PDF] ✓ Logo found at: {candidate}")
        break

if LOGO_PATH is None:
    print(f"[PDF] ✗ Logo NOT found! Searching in: {_BACKEND}")
    print(f"[PDF]    Please save 'pcu_logo.png' in: {_BACKEND}")
    print(f"[PDF]    PDF will be generated WITHOUT the logo.")


def _course_line(course, conflict_set):
    """Compact cell text: COURSE_CODE (Venue) — Bold code + BoldItalic venue."""
    venue = course.description or "TBA"
    code = f'<font name="Times-Bold">{course.course_code}</font>'
    venue_part = f'<font name="Times-BoldItalic">({venue})</font>'
    if course.id in conflict_set:
        return f'<font color="#FF0000"><b>⚠ {course.course_code} ({venue})</b></font>'
    return f"{code} {venue_part}"


def _duration_hours(course):
    """How many hours this course session spans."""
    return int(course.time_end.split(":")[0]) - int(course.time_start.split(":")[0])


def build_timetable_pdf(
    courses: list[CourseItem],
    faculty_code: str,
    faculty_name: str,
    conflict_ids: list[int] | None = None,
) -> BytesIO:
    """Build a GRID-format PDF matching the institution timetable.

    2hr courses get a merged cell spanning 2 hour-columns.
    1hr courses get a single normal cell.
    When 1hr and 2hr courses share a time block, the day is split into
    two sub-rows: one for 2hr courses (with merged cells) and one for
    1hr courses (with individual cells).
    """
    buffer = BytesIO()
    conflict_set = set(conflict_ids or [])

    page_w, page_h = landscape(letter)
    margin_left = 12 * mm
    margin_right = 12 * mm
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

    # ── Styles ────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", fontSize=14, leading=17, textColor=BLACK,
        fontName="Helvetica-Bold", alignment=1, spaceAfter=2,
    )
    header_time_style = ParagraphStyle(
        "HeaderTime", fontSize=9, leading=11, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    header_sub_italic_style = ParagraphStyle(
        "HeaderSubItalic", fontSize=9, leading=11, textColor=BLACK,
        fontName="Times-BoldItalic", alignment=1,
    )
    day_style = ParagraphStyle(
        "DayLabel", fontSize=9, leading=11, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    break_style = ParagraphStyle(
        "Break", fontSize=9, leading=11, textColor=BLACK,
        fontName="Times-Bold", alignment=1,
    )
    cell_style = ParagraphStyle(
        "Cell", fontSize=8, leading=10, textColor=BLACK,
        fontName="Times-Roman",
    )
    footer_style = ParagraphStyle(
        "Footer", fontSize=12, leading=14, textColor=BLACK,
        fontName="Times-Bold", spaceBefore=12,
    )

    # ── Logo + Title block ────────────────────────────────────────────
    if LOGO_PATH is not None and LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=65, height=60)
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

    story.append(Spacer(1, 6))

    # ── Build grid: place each course into its START slot ──────────────
    grid = {}
    for day in DAYS:
        grid[day] = {}
        for start, end, label in SLOT_HEADERS:
            if label != "12 – 1pm":
                grid[day][start] = []

    seen = {}
    for c in courses:
        day_slots = grid.get(c.day_of_the_week)
        if day_slots and c.time_start in day_slots:
            key = (c.day_of_the_week, c.time_start, c.course_code)
            if key not in seen:
                day_slots[c.time_start].append(c)
                seen[key] = True

    for day in DAYS:
        for start in grid[day]:
            grid[day][start].sort(key=lambda c: (c.department, c.academic_level))

    # ── Determine which days need two sub-rows ─────────────────────────
    day_needs_split = {}
    for day in DAYS:
        needs_split = False
        for start in grid[day]:
            durs = set(_duration_hours(c) for c in grid[day][start])
            if len(durs) > 1:
                needs_split = True
                break
        day_needs_split[day] = needs_split

    # ── Table data ──────────────────────────────────────────────────────
    header1 = ["DAY/\nTime"] + [
        Paragraph(s[2], header_time_style) for s in SLOT_HEADERS
    ]
    header2 = [""] + [
        Paragraph("Course &<br/>Venue", header_sub_italic_style) for s in SLOT_HEADERS
    ]

    data = [header1, header2]
    span_cmds = []
    merge_cmds = []

    current_row = 2

    for day_idx, day in enumerate(DAYS):
        needs_split = day_needs_split[day]
        num_sub_rows = 2 if needs_split else 1

        if num_sub_rows == 2:
            merge_cmds.append(("SPAN", (0, current_row), (0, current_row + 1)))

        for sub_row in range(num_sub_rows):
            row = []

            if sub_row == 0:
                row.append(Paragraph(DAY_SHORT[day], day_style))
            else:
                row.append("")

            consumed_cols = set()

            for si, (start, end, label) in enumerate(SLOT_HEADERS):
                col_idx = si + 1

                if col_idx in consumed_cols:
                    row.append("")
                    continue

                if label == "12 – 1pm":
                    row.append(Paragraph("B<br/>R<br/>E<br/>A<br/>K", break_style))
                    continue

                all_courses = grid[day].get(start, [])

                if needs_split:
                    if sub_row == 0:
                        cell_courses = [c for c in all_courses if _duration_hours(c) >= 2]
                    else:
                        cell_courses = [c for c in all_courses if _duration_hours(c) == 1]
                else:
                    cell_courses = all_courses

                has_2hr = any(_duration_hours(c) >= 2 for c in cell_courses)

                if has_2hr and si + 1 < len(SLOT_HEADERS):
                    next_si = si + 1
                    while next_si < len(SLOT_HEADERS) and SLOT_HEADERS[next_si][2] == "12 – 1pm":
                        next_si += 1

                    if next_si < len(SLOT_HEADERS):
                        next_col_idx = next_si + 1
                        span_cmds.append(("SPAN", (col_idx, current_row), (next_col_idx, current_row)))
                        consumed_cols.add(next_col_idx)

                if cell_courses:
                    lines = [_course_line(c, conflict_set) for c in cell_courses]
                    row.append(Paragraph("<br/>".join(lines), cell_style))
                else:
                    row.append("")

            data.append(row)
            current_row += 1

    # ── Column widths ───────────────────────────────────────────────────
    day_col_w = 42
    break_col_w = 42
    num_teaching = len([s for s in SLOT_HEADERS if s[2] != "12 – 1pm"])
    remaining_w = usable_w - day_col_w
    slot_col_w = (remaining_w - break_col_w) / num_teaching

    col_widths = [day_col_w]
    for s in SLOT_HEADERS:
        if s[2] == "12 – 1pm":
            col_widths.append(break_col_w)
        else:
            col_widths.append(slot_col_w)

    # ── Build table ─────────────────────────────────────────────────────
    table = Table(data, colWidths=col_widths, repeatRows=2)

    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Times-BoldItalic"),
        ("FONTSIZE", (0, 0), (-1, 1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), BLACK),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 1), 3),

        ("GRID", (0, 0), (-1, -1), 1, BLACK),
        ("BOX", (0, 0), (-1, -1), 1.5, BLACK),

        ("FONTNAME", (0, 2), (0, -1), "Times-Bold"),
        ("FONTSIZE", (0, 2), (0, -1), 9),
        ("ALIGN", (0, 2), (0, -1), "CENTER"),
        ("VALIGN", (0, 2), (0, -1), "MIDDLE"),

        ("VALIGN", (1, 2), (-1, -1), "TOP"),
        ("TOPPADDING", (1, 2), (-1, -1), 2),
        ("BOTTOMPADDING", (1, 2), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),

        ("LINEBELOW", (0, 1), (-1, 1), 1.5, BLACK),
    ]

    style_cmds.extend(span_cmds)
    style_cmds.extend(merge_cmds)

    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    # ── Footer ──────────────────────────────────────────────────────────
    story.append(Paragraph("Signed: TTE committee", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer