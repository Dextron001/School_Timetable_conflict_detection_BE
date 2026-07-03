"""Build a landscape PDF timetable with reportlab."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from .models import CourseItem
from .seed import DAYS


def build_timetable_pdf(courses: list[CourseItem], department: str, level: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Heading1"], fontSize=18, leading=22,
        textColor=colors.HexColor("#1e293b"), spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "DocMeta", parent=styles["Normal"], fontSize=10, leading=14,
        textColor=colors.HexColor("#475569"), spaceAfter=15,
    )

    story.append(Paragraph(
        f"OFFICIAL TIMETABLE — {department.upper()} ({level} Level)", title_style))
    story.append(Paragraph(
        "Academic Session 2025/2026 · First Semester", meta_style))
    story.append(Spacer(1, 10))

    for day in DAYS:
        day_courses = sorted(
            [c for c in courses if c.day_of_the_week == day],
            key=lambda c: c.time_start,
        )
        if not day_courses:
            continue

        day_head = ParagraphStyle(
            f"DayHead_{day}", parent=styles["Heading2"], fontSize=12,
            textColor=colors.HexColor("#0f172a"), spaceBefore=12, spaceAfter=6,
        )
        story.append(Paragraph(f"{day.upper()}", day_head))

        data = [["Time", "Course", "Venue", "Lecturer"]]
        for c in day_courses:
            data.append([
                f"{c.time_start} - {c.time_end}",
                f"{c.course_code}: {c.name}",
                c.description or "TBA",
                c.lecturer_name,
            ])

        table = Table(data, colWidths=[110, 250, 160, 180])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    if len(story) <= 3:
        story.append(Paragraph("No courses scheduled.", meta_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
