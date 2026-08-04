"""Core timetable logic: time helpers, conflict detection with cause details,
generation, resolution.

Generation produces a deliberately messy DRAFT. Resolution uses the DSATUR
graph-colouring scheduler to produce a clash-free timetable with even
day-spreading.

All times are 24-hour 'HH:MM' (1-hour slots matching institution pattern).
Multi-unit courses: 2-unit = 2hr block, 3-unit = 2hr session A + 1hr session B.
"""
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from .models import CourseItem
from .scheduler import (
    schedule_courses, _is_general,
    build_graph, dsatur_colour, apply_colours, reassign_venues,
    greedy_colour_count, COLOURS, NEXT_CONSECUTIVE,
)
from .seed import DAYS, DEPARTMENT_POOLS, FACULTIES, FACULTY_VENUES, TIME_SLOTS, DEPT_TO_FACULTY

# ── Fixed time slots for general courses (same for both faculties) ─────────
GENERAL_COURSE_SLOTS = {
    # 100-level — Monday morning
    ("HDS 101", "100"): ("Monday", "08:00", "09:00"),
    ("PCU-HDS 101", "100"): ("Monday", "08:00", "09:00"),
    ("HDS 102", "100"): ("Monday", "09:00", "10:00"),
    ("GNS 101", "100"): ("Monday", "10:00", "12:00"),
    ("GNS 103", "100"): ("Monday", "13:00", "15:00"),
    ("PCU-GNS 103", "100"): ("Monday", "13:00", "15:00"),
    ("GNS 111", "100"): ("Monday", "15:00", "17:00"),
    # 200-level — Tuesday morning
    ("HDS 201", "200"): ("Tuesday", "08:00", "09:00"),
    ("PCU-HDS 201", "200"): ("Tuesday", "08:00", "09:00"),
    ("HDS 202", "200"): ("Tuesday", "09:00", "10:00"),
    ("GNS 201", "200"): ("Tuesday", "10:00", "12:00"),
    ("GNS 203", "200"): ("Tuesday", "13:00", "15:00"),
    ("PCU-GNS 203", "200"): ("Tuesday", "13:00", "15:00"),
    # 300-level — Wednesday morning
    ("HDS 301", "300"): ("Wednesday", "08:00", "09:00"),
    ("PCU-HDS 301", "300"): ("Wednesday", "08:00", "09:00"),
}


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
    if a.course_code == b.course_code:
        return None
    if not _time_overlap(a, b):
        return None
    if a.academic_level == b.academic_level:
        a_gen = _is_general(a.course_code)
        b_gen = _is_general(b.course_code)
        if a_gen != b_gen:
            return "general"
        if a_gen and b_gen:
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


def find_conflict_details(courses: list[CourseItem]) -> list[dict]:
    """Return detailed list of every conflict with cause information."""
    details = []
    for i, a in enumerate(courses):
        for b in courses[i + 1:]:
            reason = conflict_reason(a, b)
            if reason:
                detail_text = ""
                if reason == "general":
                    detail_text = f"General course clash ({a.academic_level}-level)"
                elif reason == "cohort":
                    detail_text = f"{a.department} {a.academic_level}-level"
                elif reason == "lecturer":
                    detail_text = a.lecturer_name
                elif reason == "venue":
                    detail_text = a.description or b.description or "Unknown venue"

                overlap_start = max(a.time_start, b.time_start)
                overlap_end = min(a.time_end, b.time_end)

                details.append({
                    "course_id_1": a.id,
                    "course_code_1": a.course_code,
                    "course_id_2": b.id,
                    "course_code_2": b.course_code,
                    "cause": reason,
                    "detail": detail_text,
                    "day": a.day_of_the_week,
                    "time_start": overlap_start,
                    "time_end": overlap_end,
                })
    return details


def _assign_general_courses(courses: list[CourseItem]) -> None:
    """Assign fixed time slots to all general courses and set venue to Auditorium."""
    for c in courses:
        if not _is_general(c.course_code):
            continue
        key = (c.course_code, c.academic_level)
        if key in GENERAL_COURSE_SLOTS:
            day, start, end = GENERAL_COURSE_SLOTS[key]
            c.day_of_the_week = day
            c.time_start = start
            c.time_end = end
            c.description = "Auditorium"


def _precolour_general_nodes(nodes) -> None:
    """Pre-colour general-course nodes in the DSATUR graph with their fixed
    slot colours so the scheduler respects them as hard constraints."""
    for node in nodes:
        if not _is_general(node.course.course_code):
            continue
        if node.colour is not None:
            continue
        key = (node.course.course_code, node.course.academic_level)
        if key not in GENERAL_COURSE_SLOTS:
            continue
        day, start, end = GENERAL_COURSE_SLOTS[key]
        for c_idx, (c_day, (c_start, c_end)) in enumerate(COLOURS):
            if c_day == day and c_start == start:
                node.colour = c_idx
                if node.dur == 2 and c_idx in NEXT_CONSECUTIVE:
                    node.colour2 = NEXT_CONSECUTIVE[c_idx]
                break


def _count_conflicts_at(c: CourseItem, day: str, start_min: int, end_min: int,
                        courses: list[CourseItem], general_slots: dict) -> int:
    """Count how many hard conflicts course *c* would have if placed at
    (day, start_min–end_min).  Returns 0 if the slot is conflict-free."""
    level = c.academic_level
    if level in general_slots:
        for g_day, g_start, g_end in general_slots[level]:
            if day == g_day and start_min < g_end and end_min > g_start:
                return 999

    if c.units == 3 and c.session == "B":
        for other in courses:
            if (other.course_code == c.course_code
                    and other.session == "A"
                    and other.department == c.department):
                if other.day_of_the_week == day:
                    return 999
                break

    conflicts = 0
    for other in courses:
        if other.id == c.id or other.course_code == c.course_code:
            continue
        if other.day_of_the_week != day:
            continue
        o_start = time_to_min(other.time_start)
        o_end = time_to_min(other.time_end)
        if start_min >= o_end or end_min <= o_start:
            continue
        if (other.department == c.department
                and other.academic_level == c.academic_level):
            conflicts += 1
        elif other.lecturer_name == c.lecturer_name:
            conflicts += 1
    return conflicts


def _count_non_venue_conflicts(courses: list[CourseItem]) -> int:
    """Count total non-venue conflicts (cohort, lecturer, general)."""
    count = 0
    for i, a in enumerate(courses):
        for b in courses[i + 1:]:
            reason = conflict_reason(a, b)
            if reason and reason != "venue":
                count += 1
    return count


def _find_best_slots(c: CourseItem, courses: list[CourseItem],
                     general_slots: dict, top_n: int = 10
                     ) -> list[tuple[tuple[int, int], tuple[str, str, str]]]:
    """Find the top-N best time slots for a course (fewest conflicts)."""
    candidates = []
    for day in DAYS:
        for start, end in TIME_SLOTS:
            start_min = time_to_min(start)
            if c.units == 2 or (c.units == 3 and c.session == "A"):
                end_min = start_min + 120
                end_str = f"{end_min // 60:02d}:{end_min % 60:02d}"
            else:
                end_min = time_to_min(end)
                end_str = end

            cost = _count_conflicts_at(
                c, day, start_min, end_min, courses, general_slots
            )
            tiebreak = 0
            if start_min >= 960:
                tiebreak += 1
            if 720 <= start_min < 780:
                tiebreak += 1
            candidates.append(((cost, tiebreak), (day, start, end_str)))

    candidates.sort(key=lambda x: x[0])
    return candidates[:top_n]


def _fix_all_conflicts(courses: list[CourseItem], faculty_code: str) -> int:
    """Quick greedy repair: move each conflicting course to its best slot.

    Single-pass, fast. A few minor conflicts may remain in very dense
    cohorts, but the DSATUR scheduler handles the vast majority already.

    Returns total number of moves made.
    """
    general_slots: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for c in courses:
        if _is_general(c.course_code):
            general_slots[c.academic_level].append(
                (c.day_of_the_week, time_to_min(c.time_start), time_to_min(c.time_end))
            )

    total_moves = 0

    # ── Single-move repair ──────────────────────────────────────────────
    for _round in range(10):
        details = find_conflict_details(courses)
        non_venue = [d for d in details if d["cause"] != "venue"]
        if not non_venue:
            break

        bad_ids: set[int] = set()
        for d in non_venue:
            bad_ids.add(d["course_id_1"])
            bad_ids.add(d["course_id_2"])

        moved = False
        for c in courses:
            if c.id not in bad_ids or _is_general(c.course_code):
                continue

            candidates = _find_best_slots(c, courses, general_slots, top_n=10)

            for score, slot in candidates:
                if score[0] >= 999:
                    break
                old = (c.day_of_the_week, c.time_start, c.time_end)
                c.day_of_the_week, c.time_start, c.time_end = slot

                new_details = find_conflict_details(courses)
                new_non_venue = [d for d in new_details if d["cause"] != "venue"]
                if len(new_non_venue) < len(non_venue):
                    total_moves += 1
                    moved = True
                    break
                else:
                    c.day_of_the_week, c.time_start, c.time_end = old

            if moved:
                break

        if moved:
            reassign_venues(courses, faculty_code)
            continue

        break

    # ── Venue conflict fix ──────────────────────────────────────────────
    for _round in range(3):
        details = find_conflict_details(courses)
        venue_conflicts = [d for d in details if d["cause"] == "venue"]
        if not venue_conflicts:
            break

        venue_ids: set[int] = set()
        for d in venue_conflicts:
            venue_ids.add(d["course_id_1"])
            venue_ids.add(d["course_id_2"])

        moved = False
        for c in courses:
            if c.id not in venue_ids or _is_general(c.course_code):
                continue

            best_slot = None
            best_score = (999, 999, 999)

            for day in DAYS:
                for start, end in TIME_SLOTS:
                    start_min = time_to_min(start)
                    if c.units == 2 or (c.units == 3 and c.session == "A"):
                        end_min = start_min + 120
                        end_str = f"{end_min // 60:02d}:{end_min % 60:02d}"
                    else:
                        end_min = time_to_min(end)
                        end_str = end

                    cost = _count_conflicts_at(
                        c, day, start_min, end_min, courses, general_slots
                    )
                    if cost >= 999:
                        continue

                    crowd = sum(
                        1 for other in courses
                        if other.id != c.id and other.day_of_the_week == day
                        and time_to_min(other.time_start) < end_min
                        and time_to_min(other.time_end) > start_min
                    )

                    tiebreak = 0
                    if start_min >= 960:
                        tiebreak += 1
                    if 720 <= start_min < 780:
                        tiebreak += 1

                    score = (cost, crowd, tiebreak)
                    if score < best_score:
                        best_score = score
                        best_slot = (day, start, end_str)

            if best_slot:
                old_day, old_start, old_end = c.day_of_the_week, c.time_start, c.time_end
                c.day_of_the_week, c.time_start, c.time_end = best_slot

                reassign_venues(courses, faculty_code)
                new_details = find_conflict_details(courses)
                new_venue = len([d for d in new_details if d["cause"] == "venue"])

                if len(venue_conflicts) > new_venue:
                    total_moves += 1
                    moved = True
                    break
                elif len(new_details) == 0:
                    total_moves += 1
                    moved = True
                    break
                else:
                    c.day_of_the_week, c.time_start, c.time_end = old_day, old_start, old_end
                    reassign_venues(courses, faculty_code)

        if not moved:
            break

    reassign_venues(courses, faculty_code)
    return total_moves


def generate_for(db: Session, faculty: str) -> list[CourseItem]:
    """Create a fresh DRAFT timetable for a faculty (all departments, all levels)."""
    from .seed import REAL_COURSES
    fac = faculty.upper()
    if fac not in FACULTIES:
        return []

    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()

    if not courses:
        return []

    venues = FACULTY_VENUES.get(fac, FACULTY_VENUES["FPAS"])

    groups = defaultdict(list)
    for c in courses:
        key = (c.department, c.academic_level, c.course_code)
        groups[key].append(c)

    cohort_day_count: dict[tuple[str, str, str], int] = {}
    venue_usage: dict[str, int] = {v: 0 for v in venues}
    lec_idx = 0

    for c in courses:
        if _is_general(c.course_code):
            _assign_general_courses([c])

    for key, group_courses in groups.items():
        dept = key[0]
        level = key[1]
        code = key[2]
        pool = DEPARTMENT_POOLS[dept]
        is_real = dept in REAL_COURSES

        if _is_general(code):
            continue

        # Use lecturers excluding the first (dedicated general-course lecturer)
        # so non-general courses never share a lecturer with general courses.
        gen_lecturer = pool["lecturers"][0]
        normal_lecs = pool["lecturers"][1:]
        lecturer = normal_lecs[lec_idx % len(normal_lecs)]
        lec_idx += 1
        min_venue_usage = min(venue_usage.values())
        least_used_venues = [v for v, u in venue_usage.items() if u == min_venue_usage]
        venue = random.choice(least_used_venues)
        venue_usage[venue] = venue_usage.get(venue, 0) + len(group_courses)

        cohort_days = {d: cohort_day_count.get((dept, level, d), 0) for d in DAYS}
        min_count = min(cohort_days.values())
        least_used_days = [d for d, c in cohort_days.items() if c == min_count]
        day = random.choice(least_used_days)

        for gc in group_courses:
            if not is_real:
                gc.name = random.choice(pool["courses"])

            gc.lecturer_name = lecturer
            gc.day_of_the_week = day
            gc.description = venue

            if gc.units == 2 and gc.session == "A":
                start, _ = random.choice(TIME_SLOTS)
                start_hr = int(start.split(":")[0])
                if start_hr >= 16:
                    start = "15:00"
                end_hr = start_hr + 2
                gc.time_start = start
                gc.time_end = f"{end_hr:02d}:00"
            elif gc.units == 3 and gc.session == "A":
                start, _ = random.choice(TIME_SLOTS)
                start_hr = int(start.split(":")[0])
                if start_hr >= 16:
                    start = "15:00"
                end_hr = start_hr + 2
                gc.time_start = start
                gc.time_end = f"{end_hr:02d}:00"
            else:
                if gc.units == 3 and gc.session == "B":
                    other_days = [d for d in DAYS if d != gc.day_of_the_week]
                    if other_days:
                        b_cohort_days = {d: cohort_day_count.get((dept, level, d), 0) for d in other_days}
                        b_min = min(b_cohort_days.values())
                        b_least = [d for d, c in b_cohort_days.items() if c == b_min]
                        gc.day_of_the_week = random.choice(b_least)
                start, end = random.choice(TIME_SLOTS)
                gc.time_start = start
                gc.time_end = end

            cdk = (dept, level, gc.day_of_the_week)
            cohort_day_count[cdk] = cohort_day_count.get(cdk, 0) + 1

    db.commit()
    return courses


def resolve_for(db: Session, faculty: str) -> dict:
    """Produce a clash-free timetable using DSATUR graph colouring for a faculty.

    General courses (HDS, GNS) are pre-coloured with their fixed time slots
    so the scheduler respects them as hard constraints — non-general courses
    at the same level will be scheduled to avoid those slots.
    SIWES courses and 6-unit project courses are excluded from the timetable.
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
    all_courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()

    # ── Remove SIWES and 6-unit project courses from scheduling ─────────
    courses = [c for c in all_courses
               if not c.course_code.strip().startswith("SIWES")
               and getattr(c, "units", 1) != 6]

    # ── Merge general course copies: keep only one per (code, level) ────
    general_map = {}
    general_copies = {}
    to_schedule = []

    for c in courses:
        if _is_general(c.course_code):
            key = (c.course_code, c.academic_level)
            if key not in general_map:
                general_map[key] = c
                general_copies[key] = [c]
                to_schedule.append(c)
            else:
                general_copies[key].append(c)
        else:
            to_schedule.append(c)

    if not to_schedule:
        return {
            "algorithm": "DSATUR graph colouring", "nodes": 0, "edges": 0,
            "colours_used": 0, "slots_available": len(COLOURS), "soft_penalty": 0,
            "comparison": {"dsatur_slots": 0, "greedy_slots": 0,
                           "dsatur_penalty": 0, "greedy_penalty": 0},
        }

    _assign_general_courses(to_schedule)

    dept = to_schedule[0].department if to_schedule else ""
    faculty_code = DEPT_TO_FACULTY.get(dept, fac)

    venues = FACULTY_VENUES.get(faculty_code, FACULTY_VENUES["FPAS"])
    import app.scheduler as sch
    sch.OVERCROWD_THRESHOLD = len(venues)

    greedy_slots, greedy_penalty = greedy_colour_count(to_schedule)

    nodes = build_graph(to_schedule)
    edges = sum(n.degree for n in nodes) // 2

    _precolour_general_nodes(nodes)

    colours_used, soft_penalty = dsatur_colour(nodes)

    apply_colours(nodes)

    for key, copies in general_copies.items():
        template = general_map[key]
        for c in copies:
            c.day_of_the_week = template.day_of_the_week
            c.time_start = template.time_start
            c.time_end = template.time_end
            c.description = "Auditorium"

    # ── Venue reassignment (handles any venue conflicts) ────────────────
    reassign_venues(courses, faculty_code)

    # ── Fast conflict repair using lookup tables ────────────────────────
    # Build fast lookups so we can check conflicts in O(1) instead of O(n).
    # This makes the repair loop fast enough to resolve ALL conflicts.
    for _attempt in range(50):
        details = find_conflict_details(courses)
        if not details:
            break

        # Build lecturer busy map: lecturer → list of (day, start_min, end_min)
        lecturer_busy: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
        for c in courses:
            lecturer_busy[c.lecturer_name].append(
                (c.day_of_the_week, time_to_min(c.time_start), time_to_min(c.time_end))
            )

        # Build cohort busy map: (dept, level) → list of (day, start_min, end_min)
        cohort_busy: dict[tuple[str, str], list[tuple[str, int, int]]] = defaultdict(list)
        for c in courses:
            cohort_busy[(c.department, c.academic_level)].append(
                (c.day_of_the_week, time_to_min(c.time_start), time_to_min(c.time_end))
            )

        # General course slots
        general_slots_nv: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
        for c in courses:
            if _is_general(c.course_code):
                general_slots_nv[c.academic_level].append(
                    (c.day_of_the_week, time_to_min(c.time_start), time_to_min(c.time_end))
                )

        # Find conflicting courses
        bad_ids: set[int] = set()
        for d in details:
            bad_ids.add(d["course_id_1"])
            bad_ids.add(d["course_id_2"])

        moved_any = False
        for c in courses:
            if c.id not in bad_ids or _is_general(c.course_code):
                continue

            c_start = time_to_min(c.time_start)
            c_end = time_to_min(c.time_end)
            c_dur = c.units == 2 or (c.units == 3 and c.session == "A")

            best_slot = None
            for day in DAYS:
                for start, end in TIME_SLOTS:
                    start_min = time_to_min(start)
                    if c_dur:
                        end_min = start_min + 120
                    else:
                        end_min = time_to_min(end)

                    # Check general course overlap
                    level = c.academic_level
                    if level in general_slots_nv:
                        skip = False
                        for g_day, g_start, g_end in general_slots_nv[level]:
                            if day == g_day and start_min < g_end and end_min > g_start:
                                skip = True
                                break
                        if skip:
                            continue

                    # Check session B different day
                    if c.units == 3 and c.session == "B":
                        conflict_a = False
                        for other in courses:
                            if other.course_code == c.course_code and other.session == "A" and other.department == c.department:
                                if other.day_of_the_week == day:
                                    conflict_a = True
                                break
                        if conflict_a:
                            continue

                    # Check lecturer busy (fast lookup)
                    lecturer_ok = True
                    for l_day, l_start, l_end in lecturer_busy.get(c.lecturer_name, []):
                        if day == l_day and start_min < l_end and end_min > l_start:
                            if l_day == c.day_of_the_week and l_start == c_start and l_end == c_end:
                                continue
                            lecturer_ok = False
                            break
                    if not lecturer_ok:
                        continue

                    # Check cohort busy (fast lookup)
                    cohort_ok = True
                    for co_day, co_start, co_end in cohort_busy.get((c.department, c.academic_level), []):
                        if day == co_day and start_min < co_end and end_min > co_start:
                            if co_day == c.day_of_the_week and co_start == c_start and co_end == c_end:
                                continue
                            cohort_ok = False
                            break
                    if not cohort_ok:
                        continue

                    best_slot = (day, start, f"{end_min // 60:02d}:{end_min % 60:02d}")
                    break
                if best_slot:
                    break

            if best_slot and best_slot != (c.day_of_the_week, c.time_start, c.time_end):
                c.day_of_the_week, c.time_start, c.time_end = best_slot
                moved_any = True
                # Rebuild lookups after each move so the next course sees the update
                lecturer_busy = defaultdict(list)
                cohort_busy = defaultdict(list)
                for x in courses:
                    lecturer_busy[x.lecturer_name].append(
                        (x.day_of_the_week, time_to_min(x.time_start), time_to_min(x.time_end))
                    )
                    cohort_busy[(x.department, x.academic_level)].append(
                        (x.day_of_the_week, time_to_min(x.time_start), time_to_min(x.time_end))
                    )

        if moved_any:
            reassign_venues(courses, faculty_code)
        else:
            break

    db.commit()
    return {
        "algorithm": "DSATUR graph colouring",
        "nodes": len(nodes),
        "edges": edges,
        "colours_used": colours_used,
        "slots_available": len(COLOURS),
        "soft_penalty": soft_penalty,
        "comparison": {
            "dsatur_slots": colours_used,
            "greedy_slots": greedy_slots,
            "dsatur_penalty": soft_penalty,
            "greedy_penalty": greedy_penalty,
        },
    }