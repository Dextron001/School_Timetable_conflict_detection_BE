"""Timetable scheduling via GRAPH COLOURING (DSATUR heuristic) + soft constraints.

============================================================================
THE IDEA (this is what you explain in your defence)
============================================================================
Timetabling is modelled as a *graph colouring* problem:

  * NODE   = a course that must be placed in exactly one time slot.
  * EDGE   = a "conflict" between two courses that therefore must NOT share
             the same time slot. Two courses conflict if they:
                - belong to the same cohort (same dept + level), OR
                - are taught by the same lecturer, OR
                - use the same venue/room.
  * COLOUR = a concrete (day, time-slot) pair, e.g. (Monday, 08:00-09:00).

A *proper colouring* assigns a colour to every node so that no two adjacent
nodes (conflicting courses) share a colour. A proper colouring is, by
definition, a CLASH-FREE timetable.

We colour the graph with the DSATUR algorithm (Brélaz, 1979):

  1. Compute each node's DEGREE (number of conflicting courses).
  2. Repeat until all nodes are coloured:
       a. Pick the uncoloured node with the highest SATURATION DEGREE
          (= the number of DIFFERENT colours already used by its neighbours).
          Break ties by highest ordinary degree.
       b. Assign it the LOWEST-COST colour not used by any neighbour, where
          "cost" encodes SOFT CONSTRAINTS (see below). Among equally-costed
          candidates, prefer the LEAST-USED colour so courses spread evenly
          across all five days, and penalise same-day placement for same
          cohort to give students breathing space (free periods).
  3. Map each chosen colour index back to its (day, slot) and write it
     onto the course.

----------------------------------------------------------------------------
HARD vs SOFT CONSTRAINTS (a key defence talking point)
----------------------------------------------------------------------------
  * HARD constraints MUST be satisfied -> they are the graph EDGES. A valid
    timetable never breaks them (no lecturer/venue/cohort double-booking).
  * SOFT constraints are PREFERENCES we try to honour but may break if needed:
      (a) Lunch break slot (12-1pm) — penalised heavily
      (b) Late afternoon (4-5pm) — penalised mildly
      (c) Same-day for same cohort — penalised to give students free periods
          between lectures (breathing space), matching institution pattern
      (d) Overall even spread — least-used-first tie-breaking

============================================================================
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from .models import CourseItem
from .seed import DAYS, TIME_SLOTS

# The palette of colours: every (day, slot) combination is one colour.
COLOURS: list[tuple[str, tuple[str, str]]] = [
    (day, slot) for day in DAYS for slot in TIME_SLOTS
]

# --------------------------------------------------------------------------
# SOFT CONSTRAINTS
# --------------------------------------------------------------------------
LUNCH_SLOT = ("12:00", "13:00")
LATE_SLOTS = {("16:00", "17:00")}

LUNCH_PENALTY = 5
LATE_PENALTY = 2
COHORT_DAY_PENALTY = 4  # penalise same-day for same cohort (breathing space)


def colour_cost(colour_index: int) -> int:
    """Base soft-constraint cost (lunch + late)."""
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
    """Two courses share an edge (HARD constraint) if they cannot occupy the
    same time slot: same cohort, same lecturer, or same venue."""
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
    """Return the index of the next node to colour (highest saturation,
    tie-broken by highest degree). Returns None if all are coloured."""
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


def _selection_cost(colour_index: int, node: Node, nodes: list[Node]) -> int:
    """Total cost of assigning colour_index to this node.

    Includes:
      - Lunch / late penalty (base soft constraints)
      - Cohort-day penalty: how many same-cohort courses already on this day
        (gives students breathing space between lectures)
    """
    cost = colour_cost(colour_index)

    # Cohort-day penalty: penalise putting a course on a day where
    # its same-cohort (same dept + level) already has lectures.
    target_day = COLOURS[colour_index][0]
    dept = node.course.department
    level = node.course.academic_level

    for n_idx in node.neighbours:
        neighbour = nodes[n_idx]
        if neighbour.colour is not None:
            n_day = COLOURS[neighbour.colour][0]
            if (n_day == target_day
                    and neighbour.course.department == dept
                    and neighbour.course.academic_level == level):
                cost += COHORT_DAY_PENALTY

    return cost


def dsatur_colour(nodes: list[Node]) -> tuple[int, int]:
    """Colour the graph in place using DSATUR with all soft constraints.

    Selection key: (selection_cost, colour_usage) —
      1. Lowest total soft cost (lunch + late + cohort-day)
      2. Least-used colour (even spread across all 5 days)

    Returns (distinct_colours_used, total_base_penalty).
    """
    num_colours = len(COLOURS)
    used = set()
    total_penalty = 0
    colour_usage = [0] * num_colours

    while (idx := _pick_next(nodes)) is not None:
        node = nodes[idx]
        forbidden = {nodes[n].colour for n in node.neighbours
                     if nodes[n].colour is not None}
        candidates = [c for c in range(num_colours) if c not in forbidden]
        if candidates:
            chosen = min(candidates,
                         key=lambda c: (_selection_cost(c, node, nodes),
                                        colour_usage[c]))
        else:
            chosen = min(range(num_colours),
                         key=lambda c: (colour_usage[c], colour_cost(c)))
        node.colour = chosen
        used.add(chosen)
        total_penalty += colour_cost(chosen)
        colour_usage[chosen] += 1
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


# --------------------------------------------------------------------------
# Greedy comparison: a naive baseline to benchmark against DSATUR.
# --------------------------------------------------------------------------
def greedy_colour_count(courses: list[CourseItem]) -> tuple[int, int]:
    """Colour the conflict graph greedily in the courses' natural order.

    Uses same soft constraints + least-used tie-breaking for fair comparison.
    Returns (distinct_colours_used, total_base_penalty) WITHOUT modifying
    the courses.
    """
    nodes = build_graph(courses)
    num_colours = len(COLOURS)
    used = set()
    penalty = 0
    colour_usage = [0] * num_colours

    for node in nodes:
        forbidden = {nodes[n].colour for n in node.neighbours
                     if nodes[n].colour is not None}
        candidates = [c for c in range(num_colours) if c not in forbidden]
        if candidates:
            chosen = min(candidates,
                         key=lambda c: (_selection_cost(c, node, nodes),
                                        colour_usage[c]))
        else:
            chosen = min(range(num_colours),
                         key=lambda c: (colour_usage[c], colour_cost(c)))
        node.colour = chosen
        used.add(chosen)
        penalty += colour_cost(chosen)
        colour_usage[chosen] += 1

    return len(used), penalty


def schedule_courses(db: Session, courses: list[CourseItem]) -> dict:
    """Run the full DSATUR pipeline, persist results, and benchmark vs greedy.

    Returns a report for the UI / defence demo.
    """
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