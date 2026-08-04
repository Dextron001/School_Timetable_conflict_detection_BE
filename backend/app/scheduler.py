"""Timetable scheduling via GRAPH COLOURING (DSATUR heuristic) + soft constraints.

Supports multi-unit courses:
  - 3-unit: session A (2hr block on one day) + session B (1hr on a DIFFERENT day)
  - 2-unit: 2-hour block on one day
  - 1-unit: 1-hour slot on one day
  - 6-unit: treated as 2hr block (project meeting)

Key design goals:
  - Evenly spread courses across all 5 days of the week
  - No cohort overloaded on a single day (max ~2 courses per cohort per day)
  - 3-unit session B MUST be on a different day from session A
  - Different departments can share time slots (different cohorts)
  - Avoid lunch hour (12-1pm) and late afternoon when possible
  - Avoid overcrowding any single venue/time slot
  - Reassign venues to eliminate venue conflicts
"""
from collections import Counter
from dataclasses import dataclass, field
from math import ceil
from typing import Sequence

from sqlalchemy.orm import Session

from .models import CourseItem
from .seed import DAYS, FACULTY_VENUES, TIME_SLOTS

# ── Colour palette: every (day, slot) combination is one colour ───────────
COLOURS: list[tuple[str, tuple[str, str]]] = [
    (day, slot) for day in DAYS for slot in TIME_SLOTS
]

# For 2-hour blocks: given colour index i, what is the next consecutive
# colour on the same day?
NEXT_CONSECUTIVE: dict[int, int] = {}
for i, (day, slot) in enumerate(COLOURS):
    start_hr = int(slot[0].split(":")[0])
    next_start = f"{start_hr + 1:02d}:00"
    next_end = f"{start_hr + 2:02d}:00"
    next_slot = (next_start, next_end)
    for j, (d2, s2) in enumerate(COLOURS):
        if d2 == day and s2 == next_slot:
            NEXT_CONSECUTIVE[i] = j
            break

# ── Soft constraint penalties ─────────────────────────────────────────────
LUNCH_SLOT = ("12:00", "13:00")

LUNCH_PENALTY = 5          # Don't schedule at 12-1pm
LATE_PENALTY = 2           # Prefer not scheduling at 4-5pm
DAY_OVERLOAD_PENALTY = 8   # Penalize days with too many courses
COHORT_DAY_LIMIT_PENALTY = 10  # Same cohort can't have too many courses/day
SESSION_DIFFERENT_DAY_PENALTY = 50  # session B MUST be on different day (hard)
OVERCROWD_THRESHOLD = 14     # Max courses per time slot = number of venues
OVERCROWD_PENALTY = 50       # Heavy penalty for exceeding venue capacity


def colour_cost(colour_index: int) -> int:
    """Base cost of a time slot (lunch & late penalties)."""
    _day, slot = COLOURS[colour_index]
    cost = 0
    if slot == LUNCH_SLOT:
        cost += LUNCH_PENALTY
    if slot[0] >= "16:00":
        cost += LATE_PENALTY
    return cost


def duration_hours(course: CourseItem) -> int:
    """How many hours this course session spans."""
    units = getattr(course, "units", 1)
    session = getattr(course, "session", "A")
    if units == 2 and session == "A":
        return 2
    if units == 3 and session == "A":
        return 2
    return 1


@dataclass
class Node:
    """A course as a graph node, with DSATUR bookkeeping."""
    course: CourseItem
    neighbours: set[int] = field(default_factory=set)
    colour: int | None = None
    colour2: int | None = None  # second colour for 2-hour blocks
    saturation: set[int] = field(default_factory=set)
    saturation2: set[int] = field(default_factory=set)

    @property
    def degree(self) -> int:
        return len(self.neighbours)

    @property
    def dur(self) -> int:
        return duration_hours(self.course)


# ── General course prefixes (taken by ALL students across faculties) ──────
# GST courses are department-specific (e.g. GST 212 = CSC/SEN/CYB only),
# so they are NOT treated as general — only HDS and GNS are.
GENERAL_PREFIXES = ("HDS ", "GNS ", "PCU-HDS ", "PCU-GNS ")


def _is_general(code: str) -> bool:
    """True if this course code is a general/shared course taken by all students."""
    return any(code.strip().startswith(p) for p in GENERAL_PREFIXES)


def courses_conflict(a: CourseItem, b: CourseItem) -> bool:
    """Two courses share an edge (HARD constraint) if they cannot occupy the
    same time slot. Same course_code entries (different sessions) do NOT conflict.
    Venue conflicts are NOT edges — they are resolved by venue reassignment.
    General courses (HDS, GNS) conflict with ALL NON-GENERAL courses at the
    same level since every student at that level takes them. Two general
    courses at the same level do NOT conflict — they're the same lecture."""
    if a.id == b.id:
        return False
    if a.course_code == b.course_code:
        return False
    # General vs non-general at the same level → conflict
    if a.academic_level == b.academic_level:
        a_gen = _is_general(a.course_code)
        b_gen = _is_general(b.course_code)
        if a_gen != b_gen:          # one general, one not
            return True
        # two general courses at the same level = same lecture → no edge
        if a_gen and b_gen:
            return False
    same_cohort = (a.department == b.department
                   and a.academic_level == b.academic_level)
    same_lecturer = a.lecturer_name == b.lecturer_name
    # Venue conflicts are handled by venue reassignment, not by the graph
    return same_cohort or same_lecturer


def build_graph(courses: list[CourseItem]) -> list[Node]:
    """Create nodes and connect conflicting pairs with edges.
    Only cohort and lecturer conflicts are edges — venue conflicts are
    resolved later by venue reassignment."""
    nodes = [Node(course=c) for c in courses]
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if courses_conflict(nodes[i].course, nodes[j].course):
                nodes[i].neighbours.add(j)
                nodes[j].neighbours.add(i)
    return nodes


def _pick_next(nodes: list[Node]) -> int | None:
    """Return the index of the next node to colour (highest saturation,
    tie-broken by highest degree)."""
    best_idx = None
    best_key = (-1, -1)
    for idx, node in enumerate(nodes):
        if node.colour is not None:
            continue
        key = (len(node.saturation), node.degree)
        if key > best_key:
            best_key = key
            best_idx = idx
    return best_idx


def _selection_cost(
    colour_index: int,
    node: Node,
    nodes: list[Node],
    colour_usage: list[int],
    day_usage: dict[str, int],
    cohort_day_usage: dict[tuple[str, str, str], int],
    cohort_sizes: dict[tuple[str, str], int],
) -> int:
    """Total cost of assigning colour_index to this node."""
    cost = colour_cost(colour_index)

    # For 2-hour blocks, add cost of the consecutive slot too
    if node.dur == 2 and colour_index in NEXT_CONSECUTIVE:
        cost += colour_cost(NEXT_CONSECUTIVE[colour_index])

    target_day = COLOURS[colour_index][0]
    dept = node.course.department
    level = node.course.academic_level
    cohort_key = (dept, level)

    # ── Day overload penalty ─────────────────────────────────────────
    total_courses = sum(day_usage.values())
    avg_per_day = max(1, total_courses / 5) if total_courses > 0 else 1
    day_count = day_usage.get(target_day, 0)
    if day_count >= avg_per_day:
        cost += DAY_OVERLOAD_PENALTY * (day_count - int(avg_per_day) + 1)

    if node.dur == 2 and colour_index in NEXT_CONSECUTIVE:
        if day_count + 1 >= avg_per_day:
            cost += DAY_OVERLOAD_PENALTY * max(0, (day_count + 1 - int(avg_per_day) + 1))

    # ── Cohort-day limit penalty ─────────────────────────────────────
    cohort_size = cohort_sizes.get(cohort_key, 0)
    max_per_day = max(2, ceil(cohort_size / 5))
    cohort_day_key = (dept, level, target_day)
    cohort_day_count = cohort_day_usage.get(cohort_day_key, 0)
    if cohort_day_count >= max_per_day:
        cost += COHORT_DAY_LIMIT_PENALTY * (cohort_day_count - max_per_day + 1)

    # ── Overcrowding penalty (same time slot) ────────────────────────
    usage = colour_usage[colour_index]
    if usage >= OVERCROWD_THRESHOLD:
        cost += OVERCROWD_PENALTY * (usage - OVERCROWD_THRESHOLD + 1)
    if node.dur == 2 and colour_index in NEXT_CONSECUTIVE:
        usage2 = colour_usage[NEXT_CONSECUTIVE[colour_index]]
        if usage2 >= OVERCROWD_THRESHOLD:
            cost += OVERCROWD_PENALTY * (usage2 - OVERCROWD_THRESHOLD + 1)

    # ── Session B MUST be on different day from session A ────────────
    course_code = node.course.course_code
    node_session = node.course.session

    if node_session == "B":
        for other in nodes:
            if other.course.course_code == course_code and other.course.session == "A":
                if other.colour is not None:
                    a_day = COLOURS[other.colour][0]
                    if target_day == a_day:
                        cost += SESSION_DIFFERENT_DAY_PENALTY

    if node_session == "A":
        for other in nodes:
            if other.course.course_code == course_code and other.course.session == "B":
                if other.colour is not None:
                    b_day = COLOURS[other.colour][0]
                    if target_day == b_day:
                        cost += SESSION_DIFFERENT_DAY_PENALTY

    return cost


def _is_forbidden(colour_index: int, node: Node, nodes: list[Node]) -> bool:
    """Check if a colour is forbidden for this node."""
    for n_idx in node.neighbours:
        neighbour = nodes[n_idx]
        if neighbour.colour == colour_index or neighbour.colour2 == colour_index:
            return True
        if neighbour.colour is not None and neighbour.dur == 2:
            if neighbour.colour in NEXT_CONSECUTIVE and NEXT_CONSECUTIVE[neighbour.colour] == colour_index:
                return True
    return False


def _conflict_count_for_colour(colour_index: int, node: Node, nodes: list[Node]) -> int:
    """Count how many of this node's neighbours already occupy this colour.
    Used for the fallback when all colours are forbidden.
    General course overlaps are weighted much more heavily."""
    count = 0
    for n_idx in node.neighbours:
        neighbour = nodes[n_idx]
        if neighbour.colour == colour_index or neighbour.colour2 == colour_index:
            # General course overlap at same level is catastrophic
            if (node.course.academic_level == neighbour.course.academic_level
                    and _is_general(node.course.course_code) != _is_general(neighbour.course.course_code)):
                count += 100  # general course overlap is very bad
            else:
                count += 1
        if neighbour.colour is not None and neighbour.dur == 2:
            if neighbour.colour in NEXT_CONSECUTIVE and NEXT_CONSECUTIVE[neighbour.colour] == colour_index:
                count += 1
    return count


def dsatur_colour(nodes: list[Node]) -> tuple[int, int]:
    """Colour the graph using DSATUR with multi-hour + day-spreading support.

    Supports pre-coloured nodes (e.g. general courses locked to fixed slots):
    nodes whose .colour is already set are skipped, and their colours are
    included in the initial state so that remaining nodes avoid them.

    Returns (distinct_colours_used, total_base_penalty).
    """
    num_colours = len(COLOURS)
    used = set()
    total_penalty = 0
    colour_usage = [0] * num_colours

    day_usage: dict[str, int] = {}
    cohort_day_usage: dict[tuple[str, str, str], int] = {}

    cohort_sizes: dict[tuple[str, str], int] = {}
    for node in nodes:
        key = (node.course.department, node.course.academic_level)
        cohort_sizes[key] = cohort_sizes.get(key, 0) + 1

    # ── Initialise state from pre-coloured nodes (locked general courses) ──
    for node in nodes:
        if node.colour is not None:
            used.add(node.colour)
            total_penalty += colour_cost(node.colour)
            colour_usage[node.colour] += 1
            day = COLOURS[node.colour][0]
            day_usage[day] = day_usage.get(day, 0) + 1
            cdk = (node.course.department, node.course.academic_level, day)
            cohort_day_usage[cdk] = cohort_day_usage.get(cdk, 0) + 1
            if node.colour2 is not None:
                used.add(node.colour2)
                total_penalty += colour_cost(node.colour2)
                colour_usage[node.colour2] += 1
            # Propagate saturation to neighbours
            for n_idx in node.neighbours:
                nodes[n_idx].saturation.add(node.colour)
                if node.colour2 is not None:
                    nodes[n_idx].saturation.add(node.colour2)

    while (idx := _pick_next(nodes)) is not None:
        node = nodes[idx]

        forbidden = set()
        for n_idx in node.neighbours:
            neighbour = nodes[n_idx]
            if neighbour.colour is not None:
                forbidden.add(neighbour.colour)
                if neighbour.dur == 2 and neighbour.colour in NEXT_CONSECUTIVE:
                    forbidden.add(NEXT_CONSECUTIVE[neighbour.colour])
            if neighbour.colour2 is not None:
                forbidden.add(neighbour.colour2)

        # For session B: also forbid the same day as session A (hard constraint)
        if node.course.session == "B":
            for other in nodes:
                if other.course.course_code == node.course.course_code and other.course.session == "A":
                    if other.colour is not None:
                        a_day = COLOURS[other.colour][0]
                        for c in range(num_colours):
                            if COLOURS[c][0] == a_day:
                                forbidden.add(c)

        if node.dur == 1:
            candidates = [c for c in range(num_colours) if c not in forbidden]
            if candidates:
                chosen = min(candidates,
                             key=lambda c: (
                                 _selection_cost(c, node, nodes, colour_usage,
                                                 day_usage, cohort_day_usage, cohort_sizes),
                                 colour_usage[c],
                             ))
            else:
                # All colours are forbidden — pick the one that creates the
                # fewest conflicts with neighbours (least-bad fallback)
                chosen = min(range(num_colours),
                             key=lambda c: (
                                 _conflict_count_for_colour(c, node, nodes),
                                 colour_usage[c],
                                 colour_cost(c),
                             ))

            node.colour = chosen
            used.add(chosen)
            total_penalty += colour_cost(chosen)
            colour_usage[chosen] += 1

            day = COLOURS[chosen][0]
            day_usage[day] = day_usage.get(day, 0) + 1
            cdk = (node.course.department, node.course.academic_level, day)
            cohort_day_usage[cdk] = cohort_day_usage.get(cdk, 0) + 1

            for n in node.neighbours:
                nodes[n].saturation.add(chosen)

        elif node.dur == 2:
            pairs = []
            for c in range(num_colours):
                if c in forbidden:
                    continue
                if c not in NEXT_CONSECUTIVE:
                    continue
                c2 = NEXT_CONSECUTIVE[c]
                if c2 in forbidden:
                    continue
                pairs.append((c, c2))

            if pairs:
                chosen_pair = min(pairs,
                                  key=lambda p: (
                                      _selection_cost(p[0], node, nodes, colour_usage,
                                                      day_usage, cohort_day_usage, cohort_sizes)
                                      + _selection_cost(p[1], node, nodes, colour_usage,
                                                        day_usage, cohort_day_usage, cohort_sizes),
                                      colour_usage[p[0]] + colour_usage[p[1]],
                                  ))
                chosen = chosen_pair[0]
                chosen2 = chosen_pair[1]
            else:
                # No valid pair — find the best single colour (least-bad fallback)
                candidates = [c for c in range(num_colours) if c not in forbidden]
                if candidates:
                    chosen = min(candidates,
                                 key=lambda c: (
                                     _conflict_count_for_colour(c, node, nodes),
                                     colour_usage[c],
                                     colour_cost(c),
                                 ))
                else:
                    chosen = min(range(num_colours),
                                 key=lambda c: (
                                     _conflict_count_for_colour(c, node, nodes),
                                     colour_usage[c],
                                     colour_cost(c),
                                 ))
                chosen2 = None

            node.colour = chosen
            node.colour2 = chosen2
            used.add(chosen)
            if chosen2 is not None:
                used.add(chosen2)
            total_penalty += colour_cost(chosen)
            if chosen2 is not None:
                total_penalty += colour_cost(chosen2)
            colour_usage[chosen] += 1
            if chosen2 is not None:
                colour_usage[chosen2] += 1

            day = COLOURS[chosen][0]
            day_usage[day] = day_usage.get(day, 0) + 1
            cdk = (node.course.department, node.course.academic_level, day)
            cohort_day_usage[cdk] = cohort_day_usage.get(cdk, 0) + 1

            for n in node.neighbours:
                nodes[n].saturation.add(chosen)
                if chosen2 is not None:
                    nodes[n].saturation.add(chosen2)

    return len(used), total_penalty


def apply_colours(nodes: list[Node]) -> None:
    """Write each node's chosen colour back as (day, time_start, time_end)."""
    for node in nodes:
        day, (start, end) = COLOURS[node.colour]
        node.course.day_of_the_week = day
        node.course.time_start = start
        if node.dur == 2 and node.colour2 is not None:
            _, (_, end2) = COLOURS[node.colour2]
            node.course.time_end = end2
        else:
            node.course.time_end = end


def _time_overlap(a: CourseItem, b: CourseItem) -> bool:
    """Check if two courses overlap in time."""
    if a.day_of_the_week != b.day_of_the_week:
        return False
    a_start = int(a.time_start.split(":")[0]) * 60 + int(a.time_start.split(":")[1])
    a_end = int(a.time_end.split(":")[0]) * 60 + int(a.time_end.split(":")[1])
    b_start = int(b.time_start.split(":")[0]) * 60 + int(b.time_start.split(":")[1])
    b_end = int(b.time_end.split(":")[0]) * 60 + int(b.time_end.split(":")[1])
    return a_start < b_end and a_end > b_start


def _venue_load(venue: str, venue_schedule: dict) -> int:
    """Count how many times a venue is used across the whole schedule."""
    count = 0
    for _slot, venues_used in venue_schedule.items():
        if venue in venues_used:
            count += 1
    return count


def reassign_venues(courses: list[CourseItem], faculty_code: str) -> None:
    """Reassign venues to eliminate venue conflicts and balance venue usage.

    Two-phase approach:
      1. Fix venue conflicts (same venue, same time) by reassigning the
         less-loaded course to a free venue.
      2. Balance venue usage — move courses from overloaded shared venues
         (Auditorium, NH LAB) to underused dedicated lecture halls.

    Dedicated halls are preferred over shared venues to match the school's
    original timetable distribution.
    """
    venues = FACULTY_VENUES.get(faculty_code, FACULTY_VENUES["FPAS"])

    # Shared venues (used by both faculties) — should be used sparingly
    shared_venues = {"Auditorium", "NH LAB", "NW HORIZON LB"}

    # Dedicated venues — preferred for the faculty
    dedicated_venues = [v for v in venues if v not in shared_venues]

    def _build_schedule():
        """Build a map of (day, 1hr_slot) → set of venues in use."""
        schedule: dict[tuple[str, str, str], set[str]] = {}
        for c in courses:
            start_hr = int(c.time_start.split(":")[0])
            end_hr = int(c.time_end.split(":")[0])
            for hr in range(start_hr, end_hr):
                slot_start = f"{hr:02d}:00"
                slot_end = f"{hr + 1:02d}:00"
                key = (c.day_of_the_week, slot_start, slot_end)
                if key not in schedule:
                    schedule[key] = set()
                if c.description:
                    schedule[key].add(c.description)
        return schedule

    def _is_free(venue: str, day: str, start_hr: int, end_hr: int,
                 schedule: dict) -> bool:
        """Check if a venue is free for a given time range."""
        for hr in range(start_hr, end_hr):
            slot_start = f"{hr:02d}:00"
            slot_end = f"{hr + 1:02d}:00"
            key = (day, slot_start, slot_end)
            used_at_slot = schedule.get(key, set())
            if venue in used_at_slot:
                return False
        return True

    def _pick_best_venue(course: CourseItem, schedule: dict,
                         exclude: str | None = None) -> str | None:
        """Pick the best free venue for a course, preferring dedicated halls
        and least-used venues overall."""
        start_hr = int(course.time_start.split(":")[0])
        end_hr = int(course.time_end.split(":")[0])
        day = course.day_of_the_week

        # Find all free venues
        free_venues = []
        for v in venues:
            if v == exclude:
                continue
            if _is_free(v, day, start_hr, end_hr, schedule):
                free_venues.append(v)

        if not free_venues:
            return None

        # Sort: dedicated halls first, then by least overall usage
        def venue_sort_key(v):
            is_shared = v in shared_venues  # 0 = dedicated (preferred), 1 = shared
            load = _venue_load(v, schedule)
            return (is_shared, load)

        free_venues.sort(key=venue_sort_key)
        return free_venues[0]

    def _update_schedule(schedule: dict, old_venue: str | None,
                         new_venue: str, course: CourseItem) -> None:
        """Update the schedule map when a course changes venue."""
        start_hr = int(course.time_start.split(":")[0])
        end_hr = int(course.time_end.split(":")[0])
        # Remove old venue
        if old_venue:
            for hr in range(start_hr, end_hr):
                slot_start = f"{hr:02d}:00"
                slot_end = f"{hr + 1:02d}:00"
                key = (course.day_of_the_week, slot_start, slot_end)
                if key in schedule and old_venue in schedule[key]:
                    schedule[key].discard(old_venue)
        # Add new venue
        for hr in range(start_hr, end_hr):
            slot_start = f"{hr:02d}:00"
            slot_end = f"{hr + 1:02d}:00"
            key = (course.day_of_the_week, slot_start, slot_end)
            if key not in schedule:
                schedule[key] = set()
            schedule[key].add(new_venue)

    # ── Phase 1: Fix venue conflicts ───────────────────────────────────
    for _iteration in range(5):
        venue_schedule = _build_schedule()
        any_fixed = False

        for i, c in enumerate(courses):
            for j in range(i + 1, len(courses)):
                c2 = courses[j]
                if c.course_code == c2.course_code:
                    continue
                if not _time_overlap(c, c2):
                    continue
                if (c.description or "") != (c2.description or "") or not c.description:
                    continue

                # Venue conflict — reassign c2 to best free venue
                new_venue = _pick_best_venue(c2, venue_schedule,
                                             exclude=c.description)
                if new_venue:
                    old_venue = c2.description
                    c2.description = new_venue
                    _update_schedule(venue_schedule, old_venue, new_venue, c2)
                    any_fixed = True

        if not any_fixed:
            break

    # ── Phase 2: Balance venue usage ──────────────────────────────────
    # Move courses from overloaded shared venues to underused dedicated halls
    for _iteration in range(3):
        venue_schedule = _build_schedule()

        # Compute target per venue (ideal balanced distribution)
        total_courses = len(courses)
        target_per_venue = total_courses / len(venues)

        # Find courses in shared venues that could move to dedicated halls
        moved = False
        for c in courses:
            if c.description not in shared_venues:
                continue

            # Check if this venue is overused
            current_load = _venue_load(c.description, venue_schedule)
            if current_load <= target_per_venue:
                continue  # This shared venue is not overused, leave it

            # Try to move to a dedicated hall
            start_hr = int(c.time_start.split(":")[0])
            end_hr = int(c.time_end.split(":")[0])
            day = c.day_of_the_week

            # Find the least-used dedicated hall that's free
            best_dedicated = None
            best_load = float('inf')
            for v in dedicated_venues:
                if not _is_free(v, day, start_hr, end_hr, venue_schedule):
                    continue
                load = _venue_load(v, venue_schedule)
                if load < best_load and load < target_per_venue:
                    best_load = load
                    best_dedicated = v

            if best_dedicated:
                old_venue = c.description
                c.description = best_dedicated
                _update_schedule(venue_schedule, old_venue, best_dedicated, c)
                moved = True

        if not moved:
            break


# ── Greedy comparison baseline ────────────────────────────────────────────
def greedy_colour_count(courses: list[CourseItem]) -> tuple[int, int]:
    """Colour the conflict graph greedily for benchmarking.
    Returns (distinct_colours_used, total_base_penalty) WITHOUT modifying courses."""
    nodes = build_graph(courses)
    num_colours = len(COLOURS)
    used = set()
    penalty = 0
    colour_usage = [0] * num_colours
    day_usage: dict[str, int] = {}
    cohort_day_usage: dict[tuple[str, str, str], int] = {}

    cohort_sizes: dict[tuple[str, str], int] = {}
    for node in nodes:
        key = (node.course.department, node.course.academic_level)
        cohort_sizes[key] = cohort_sizes.get(key, 0) + 1

    for node in nodes:
        forbidden = set()
        for n_idx in node.neighbours:
            neighbour = nodes[n_idx]
            if neighbour.colour is not None:
                forbidden.add(neighbour.colour)
                if neighbour.dur == 2 and neighbour.colour in NEXT_CONSECUTIVE:
                    forbidden.add(NEXT_CONSECUTIVE[neighbour.colour])
            if neighbour.colour2 is not None:
                forbidden.add(neighbour.colour2)

        if node.course.session == "B":
            for other in nodes:
                if other.course.course_code == node.course.course_code and other.course.session == "A":
                    if other.colour is not None:
                        a_day = COLOURS[other.colour][0]
                        for c in range(num_colours):
                            if COLOURS[c][0] == a_day:
                                forbidden.add(c)

        if node.dur == 1:
            candidates = [c for c in range(num_colours) if c not in forbidden]
            if candidates:
                chosen = min(candidates,
                             key=lambda c: (
                                 _selection_cost(c, node, nodes, colour_usage,
                                                 day_usage, cohort_day_usage, cohort_sizes),
                                 colour_usage[c],
                             ))
            else:
                chosen = min(range(num_colours),
                             key=lambda c: (
                                 _conflict_count_for_colour(c, node, nodes),
                                 colour_usage[c],
                                 colour_cost(c),
                             ))
            node.colour = chosen
            used.add(chosen)
            penalty += colour_cost(chosen)
            colour_usage[chosen] += 1
            day = COLOURS[chosen][0]
            day_usage[day] = day_usage.get(day, 0) + 1
            cdk = (node.course.department, node.course.academic_level, day)
            cohort_day_usage[cdk] = cohort_day_usage.get(cdk, 0) + 1

        elif node.dur == 2:
            pairs = []
            for c in range(num_colours):
                if c in forbidden:
                    continue
                if c not in NEXT_CONSECUTIVE:
                    continue
                c2 = NEXT_CONSECUTIVE[c]
                if c2 in forbidden:
                    continue
                pairs.append((c, c2))

            if pairs:
                chosen_pair = min(pairs,
                                  key=lambda p: (
                                      _selection_cost(p[0], node, nodes, colour_usage,
                                                      day_usage, cohort_day_usage, cohort_sizes)
                                      + _selection_cost(p[1], node, nodes, colour_usage,
                                                        day_usage, cohort_day_usage, cohort_sizes),
                                      colour_usage[p[0]] + colour_usage[p[1]],
                                  ))
                chosen = chosen_pair[0]
                chosen2 = chosen_pair[1]
            else:
                candidates = [c for c in range(num_colours) if c not in forbidden]
                if candidates:
                    chosen = min(candidates,
                                 key=lambda c: (
                                     _conflict_count_for_colour(c, node, nodes),
                                     colour_usage[c],
                                     colour_cost(c),
                                 ))
                else:
                    chosen = min(range(num_colours),
                                 key=lambda c: (
                                     _conflict_count_for_colour(c, node, nodes),
                                     colour_usage[c],
                                     colour_cost(c),
                                 ))
                chosen2 = None

            node.colour = chosen
            node.colour2 = chosen2
            used.add(chosen)
            if chosen2 is not None:
                used.add(chosen2)
            penalty += colour_cost(chosen)
            if chosen2 is not None:
                penalty += colour_cost(chosen2)
            colour_usage[chosen] += 1
            if chosen2 is not None:
                colour_usage[chosen2] += 1
            day = COLOURS[chosen][0]
            day_usage[day] = day_usage.get(day, 0) + 1
            cdk = (node.course.department, node.course.academic_level, day)
            cohort_day_usage[cdk] = cohort_day_usage.get(cdk, 0) + 1

    return len(used), penalty


def schedule_courses(db: Session, courses: list[CourseItem]) -> dict:
    """Run the full DSATUR pipeline, persist results, and benchmark vs greedy.

    Steps:
      1. DSATUR graph colouring to assign time slots (day + time)
      2. Venue reassignment to eliminate venue conflicts
      3. Commit to database
    """
    if not courses:
        return {"algorithm": "DSATUR graph colouring", "nodes": 0, "edges": 0,
                "colours_used": 0, "slots_available": len(COLOURS),
                "soft_penalty": 0,
                "comparison": {"dsatur_slots": 0, "greedy_slots": 0,
                               "dsatur_penalty": 0, "greedy_penalty": 0}}

    # Determine faculty code first (needed for venue-capacity threshold)
    dept = courses[0].department if courses else ""
    from .seed import DEPT_TO_FACULTY
    faculty_code = DEPT_TO_FACULTY.get(dept, "FPAS")

    # Set overcrowd threshold dynamically based on venue count
    venues = FACULTY_VENUES.get(faculty_code, FACULTY_VENUES["FPAS"])
    global OVERCROWD_THRESHOLD
    OVERCROWD_THRESHOLD = len(venues)

    greedy_slots, greedy_penalty = greedy_colour_count(courses)

    nodes = build_graph(courses)
    edges = sum(n.degree for n in nodes) // 2
    colours_used, soft_penalty = dsatur_colour(nodes)
    apply_colours(nodes)

    # Reassign venues to eliminate venue conflicts
    reassign_venues(courses, faculty_code)

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
