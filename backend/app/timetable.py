"""Core timetable logic: time helpers, conflict detection, generation, resolution.

Generation produces a deliberately messy DRAFT. Resolution uses the DSATUR
graph-colouring scheduler to produce a clash-free timetable.

All times are 24-hour 'HH:MM' (1-hour slots matching institution pattern).

Scope is FACULTY-level: generate/resolve operate on ALL departments within
a faculty and ALL levels (100–400) combined.
"""
import random

from sqlalchemy.orm import Session

from .models import CourseItem
from .scheduler import schedule_courses
from .seed import DAYS, DEPARTMENT_POOLS, FACULTIES, FACULTY_VENUES, TIME_SLOTS


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
    """Return why a and b clash, or None if they don't."""
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


def generate_for(db: Session, faculty: str) -> list[CourseItem]:
    """Create a fresh DRAFT timetable for a faculty (all departments, all levels).

    Randomly assigns time slots, venues, names, and lecturers to all courses
    belonging to departments within the given faculty.
    """
    fac = faculty.upper()
    if fac not in FACULTIES:
        return []

    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()

    if not courses:
        return []

    # Use faculty-specific venues for realism
    venues = FACULTY_VENUES.get(fac, FACULTY_VENUES["FPAS"])
    used_codes = {c.course_code for c in db.query(CourseItem.course_code).all()}

    for c in courses:
        dept = c.department
        pool = DEPARTMENT_POOLS[dept]
        for _ in range(50):
            num = int(c.academic_level) + random.randint(1, 98)
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
        c.description = random.choice(venues)

    db.commit()
    return courses


def resolve_for(db: Session, faculty: str) -> dict:
    """Produce a clash-free timetable using DSATUR graph colouring for a faculty.

    Operates on ALL departments in the faculty and ALL levels combined.
    """
    fac = faculty.upper()
    if fac not in FACULTIES:
        return {
            "algorithm": "DSATUR graph colouring", "nodes": 0, "edges": 0,
            "colours_used": 0, "slots_available": 40, "soft_penalty": 0,
            "comparison": {"dsatur_slots": 0, "greedy_slots": 0,
                           "dsatur_penalty": 0, "greedy_penalty": 0},
        }

    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()

    report = schedule_courses(db, courses)
    return report