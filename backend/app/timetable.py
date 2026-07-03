"""Core timetable logic: time helpers, conflict detection, generation, resolution.

Generation produces a deliberately messy DRAFT (so there's something to fix in
the demo). Resolution uses the DSATUR graph-colouring scheduler in scheduler.py
to produce a clash-free timetable.

All times are 24-hour 'HH:MM'.
"""
import random

from sqlalchemy.orm import Session

from .models import CourseItem
from .scheduler import schedule_courses
from .seed import DAYS, DEPARTMENT_POOLS, TIME_SLOTS, VENUES


def time_to_min(time_str: str) -> int:
    hr, mn = time_str.split(":")
    return int(hr) * 60 + int(mn)


def _time_overlap(a: CourseItem, b: CourseItem) -> bool:
    """True if two courses occupy the same day and overlapping time range."""
    if a.day_of_the_week != b.day_of_the_week:
        return False
    return (
        time_to_min(a.time_start) < time_to_min(b.time_end)
        and time_to_min(a.time_end) > time_to_min(b.time_start)
    )


def conflict_reason(a: CourseItem, b: CourseItem) -> str | None:
    """Return why a and b clash, or None if they don't.

    A clash only matters when the two courses are scheduled at the same time.
    Given that, they conflict if they are the same cohort (a student can't be in
    two places), share a lecturer, or share a venue.
    """
    if a.id == b.id:
        return None
    if not _time_overlap(a, b):
        return None
    if a.department == b.department and a.academic_level == b.academic_level:
        return "cohort"
    if a.lecturer_name == b.lecturer_name:
        return "lecturer"
    if (a.description or "") == (b.description or "") and a.description:
        return "venue"
    return None


def find_conflicts(courses: list[CourseItem]) -> set[int]:
    """Return the set of course ids involved in at least one clash."""
    conflicting: set[int] = set()
    for i, a in enumerate(courses):
        for b in courses[i + 1:]:
            if conflict_reason(a, b):
                conflicting.add(a.id)
                conflicting.add(b.id)
    return conflicting


def generate_for(db: Session, department: str, level: str) -> list[CourseItem]:
    """Create a fresh, intentionally messy DRAFT timetable for a dept/level.

    Random placement here is fine: it just produces the input that the DSATUR
    scheduler then solves. (Generation = the problem; Resolve = the algorithm.)
    """
    dept = department.upper()
    if dept not in DEPARTMENT_POOLS:
        return []

    pool = DEPARTMENT_POOLS[dept]
    courses = (
        db.query(CourseItem)
        .filter(CourseItem.department == dept, CourseItem.academic_level == level)
        .all()
    )

    used_codes = {c.course_code for c in db.query(CourseItem.course_code).all()}

    for c in courses:
        for _ in range(50):
            num = int(level) + random.randint(1, 98)
            code = f"{dept}{num}"
            if code not in used_codes or code == c.course_code:
                break
        used_codes.discard(c.course_code)
        used_codes.add(code)

        start, end = random.choice(TIME_SLOTS)
        c.course_code = code
        c.name = random.choice(pool["courses"])
        c.lecturer_name = random.choice(pool["lecturers"])
        c.day_of_the_week = random.choice(DAYS)
        c.time_start = start
        c.time_end = end
        c.description = random.choice(VENUES)

    db.commit()
    return courses


def resolve_for(db: Session, department: str, level: str) -> dict:
    """Produce a clash-free timetable using DSATUR graph colouring.

    Returns a report dict from the scheduler (algorithm name, node/edge counts,
    colours used) so the UI can show what happened.
    """
    dept = department.upper()
    courses = (
        db.query(CourseItem)
        .filter(CourseItem.department == dept, CourseItem.academic_level == level)
        .all()
    )
    report = schedule_courses(db, courses)
    return report