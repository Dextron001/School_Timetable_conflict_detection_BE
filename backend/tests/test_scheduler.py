"""Tests proving the DSATUR scheduler produces clash-free timetables.

Run from the backend folder with:   pytest -v
"""
import itertools
import random
from types import SimpleNamespace

from app import scheduler as sch


class FakeDB:
    """Stand-in for a SQLAlchemy session; the scheduler only calls .commit()."""
    def commit(self):
        pass


def make_course(i, lecturer, venue, dept="CSC", level="200", units=1, session="A"):
    return SimpleNamespace(
        id=i, department=dept, academic_level=level,
        name=f"Course {i}", description=venue, course_code=f"CSC{i}",
        lecturer_name=lecturer,
        day_of_the_week="Monday", time_start="08:30", time_end="10:00",
        units=units, session=session,
    )


def find_residual_clashes(courses):
    """Two scheduled courses clash if they share a (day, start) AND a
    cohort, lecturer, or venue. Same course_code entries (different sessions)
    do NOT clash."""
    bad = []
    for a, b in itertools.combinations(courses, 2):
        # Same course, different session — no conflict
        if a.course_code == b.course_code:
            continue
        same_slot = (a.day_of_the_week == b.day_of_the_week
                     and a.time_start == b.time_start)
        if not same_slot:
            continue
        same_cohort = (a.department == b.department
                       and a.academic_level == b.academic_level)
        same_lect = a.lecturer_name == b.lecturer_name
        same_venue = bool(a.description) and a.description == b.description
        if same_cohort or same_lect or same_venue:
            bad.append((a.id, b.id))
    return bad


def test_same_cohort_all_get_different_slots():
    """All courses in one cohort must end up in different (day, slot) pairs."""
    courses = [make_course(i, f"L{i}", f"V{i}") for i in range(6)]
    sch.schedule_courses(FakeDB(), courses)
    slots = {(c.day_of_the_week, c.time_start) for c in courses}
    assert len(slots) == len(courses)
    assert find_residual_clashes(courses) == []


def test_shared_lecturer_never_double_booked():
    """Two courses with the same lecturer must not share a slot."""
    courses = [
        make_course(1, "Dr Smith", "Room A", level="100"),
        make_course(2, "Dr Smith", "Room B", level="200"),  # diff cohort, same lecturer
    ]
    sch.schedule_courses(FakeDB(), courses)
    assert (courses[0].day_of_the_week, courses[0].time_start) != \
           (courses[1].day_of_the_week, courses[1].time_start)


def test_shared_venue_never_double_booked():
    courses = [
        make_course(1, "Dr A", "Hall 1", level="100"),
        make_course(2, "Dr B", "Hall 1", level="200"),  # diff cohort, same venue
    ]
    sch.schedule_courses(FakeDB(), courses)
    assert (courses[0].day_of_the_week, courses[0].time_start) != \
           (courses[1].day_of_the_week, courses[1].time_start)


def test_no_residual_conflicts_random_stress():
    """Across many random inputs that fit in the available slots, the result
    must always be conflict-free."""
    random.seed(123)
    max_slots = len(sch.COLOURS)
    for _ in range(200):
        n = random.randint(2, max_slots)
        courses = [
            make_course(i, f"L{random.randint(0, 3)}", f"V{random.randint(0, 3)}")
            for i in range(n)
        ]
        sch.schedule_courses(FakeDB(), courses)
        assert find_residual_clashes(courses) == []


def test_report_shape():
    courses = [make_course(i, f"L{i}", f"V{i}") for i in range(4)]
    report = sch.schedule_courses(FakeDB(), courses)
    assert report["algorithm"] == "DSATUR graph colouring"
    assert report["nodes"] == 4
    assert report["colours_used"] >= 1
    assert report["slots_available"] == len(sch.COLOURS)


# ---------- Soft constraints (#1) ----------
def test_soft_constraints_avoid_lunch_and_late_when_room():
    """A small cohort should avoid the lunch slot while free morning
    slots still exist."""
    courses = [make_course(i, f"L{i}", f"V{i}") for i in range(5)]
    sch.schedule_courses(FakeDB(), courses)
    used = {(c.time_start, c.time_end) for c in courses}
    assert sch.LUNCH_SLOT not in used


def test_soft_penalty_reported():
    courses = [make_course(i, f"L{i}", f"V{i}") for i in range(4)]
    report = sch.schedule_courses(FakeDB(), courses)
    assert "soft_penalty" in report
    assert report["soft_penalty"] >= 0


# ---------- Algorithm comparison (#4) ----------
def test_comparison_block_present_and_dsatur_not_worse():
    """DSATUR should never need MORE slots than naive greedy, and should not
    have a worse soft penalty."""
    random.seed(99)
    for _ in range(50):
        n = random.randint(2, len(sch.COLOURS))
        courses = [make_course(i, f"L{random.randint(0,3)}", f"V{random.randint(0,3)}")
                   for i in range(n)]
        report = sch.schedule_courses(FakeDB(), courses)
        comp = report["comparison"]
        assert comp["dsatur_slots"] <= comp["greedy_slots"]
        assert comp["dsatur_penalty"] <= comp["greedy_penalty"]