"""Timetable scheduling via GRAPH COLOURING (DSATUR heuristic) + soft constraints."""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .models import CourseItem
from .seed import DAYS, TIME_SLOTS

# Every (day, slot) combination is one "colour".
COLOURS: list[tuple[str, tuple[str, str]]] = [
    (day, slot) for day in DAYS for slot in TIME_SLOTS
]

# ---- SOFT CONSTRAINTS: preferences expressed as a per-colour "cost". ----
LUNCH_SLOT = ("11:30", "13:00")     # the slot that straddles lunch
LATE_SLOTS = {("14:30", "16:00")}   # discouraged late-afternoon slot(s)
LUNCH_PENALTY = 5
LATE_PENALTY = 2


def colour_cost(colour_index: int) -> int:
    """Soft-constraint cost of using a given (day, slot) colour."""
    _day, slot = COLOURS[colour_index]
    cost = 0
    if slot == LUNCH_SLOT:
        cost += LUNCH_PENALTY
    if slot in LATE_SLOTS:
        cost += LATE_PENALTY
    return cost


@dataclass
class Node:
    """A course as a graph node, with the bookkeeping DSATUR needs."""
    course: CourseItem
    neighbours: set[int] = field(default_factory=set)
    colour: int | None = None
    saturation: set[int] = field(default_factory=set)

    @property
    def degree(self) -> int:
        return len(self.neighbours)


def courses_conflict(a: CourseItem, b: CourseItem) -> bool:
    """HARD constraint: two courses cannot share a slot if same cohort,
    same lecturer, or same venue."""
    if a.id == b.id:
        return False
    same_cohort = (a.department == b.department
                   and a.academic_level == b.academic_level)
    same_lecturer = a.lecturer_name == b.lecturer_name
    same_venue = (a.description or "") == (b.description or "") and bool(a.description)
    return same_cohort or same_lecturer or same_venue


def build_graph(courses: list[CourseItem]) -> list[Node]:
    """Create nodes and connect conflicting pairs with edges."""
    nodes = [Node(course=c) for c in courses]
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if courses_conflict(nodes[i].course, nodes[j].course):
                nodes[i].neighbours.add(j)
                nodes[j].neighbours.add(i)
    return nodes


def _pick_next(nodes: list[Node]) -> int | None:
    """Pick the uncoloured node with highest saturation (tie-break: degree)."""
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


def dsatur_colour(nodes: list[Node]) -> tuple[int, int]:
    """Colour the graph with DSATUR + soft costs.

    Returns (distinct_colours_used, total_soft_penalty).
    """
    num_colours = len(COLOURS)
    used = set()
    total_penalty = 0

    while (idx := _pick_next(nodes)) is not None:
        node = nodes[idx]
        forbidden = {nodes[n].colour for n in node.neighbours
                     if nodes[n].colour is not None}
        candidates = [c for c in range(num_colours) if c not in forbidden]
        if candidates:
            chosen = min(candidates, key=lambda c: (colour_cost(c), c))
        else:
            chosen = min(range(num_colours),
                         key=lambda c: sum(1 for x in nodes if x.colour == c))
        node.colour = chosen
        used.add(chosen)
        total_penalty += colour_cost(chosen)
        for n in node.neighbours:
            nodes[n].saturation.add(chosen)

    return len(used), total_penalty


def apply_colours(nodes: list[Node]) -> None:
    """Write each node's chosen colour back as (day, time_start, time_end)."""
    for node in nodes:
        day, (start, end) = COLOURS[node.colour]
        node.course.day_of_the_week = day
        node.course.time_start = start
        node.course.time_end = end


def greedy_colour_count(courses: list[CourseItem]) -> tuple[int, int]:
    """Naive greedy baseline (does NOT modify courses) for benchmarking."""
    nodes = build_graph(courses)
    num_colours = len(COLOURS)
    used = set()
    penalty = 0
    for node in nodes:
        forbidden = {nodes[n].colour for n in node.neighbours
                     if nodes[n].colour is not None}
        candidates = [c for c in range(num_colours) if c not in forbidden]
        chosen = candidates[0] if candidates else 0
        node.colour = chosen
        used.add(chosen)
        penalty += colour_cost(chosen)
    return len(used), penalty


def schedule_courses(db: Session, courses: list[CourseItem]) -> dict:
    """Run DSATUR, persist results, and benchmark vs greedy. Returns a report."""
    if not courses:
        return {"algorithm": "DSATUR graph colouring", "nodes": 0, "edges": 0,
                "colours_used": 0, "slots_available": len(COLOURS),
                "soft_penalty": 0,
                "comparison": {"dsatur_slots": 0, "greedy_slots": 0,
                               "dsatur_penalty": 0, "greedy_penalty": 0}}

    greedy_slots, greedy_penalty = greedy_colour_count(courses)

    nodes = build_graph(courses)
    edges = sum(n.degree for n in nodes) // 2
    colours_used, soft_penalty = dsatur_colour(nodes)
    apply_colours(nodes)
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