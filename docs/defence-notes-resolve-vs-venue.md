# Defence Note — "Why does clicking *Resolve* also reassign venues, if venue uses a different algorithm?"

## 30-second answer

The **Resolve** button triggers **one endpoint** (`PUT /resolve`) which runs a **two-stage
pipeline**, not a single algorithm:

1. **DSATUR graph colouring** decides **WHEN** each class holds (day + time slot).
2. A separate **greedy best-fit allocator** (`reassign_venues`) decides **WHERE** it holds (venue).

Venue was deliberately excluded from the conflict graph, because a room clash does not
require a different *time* — only a different *room*. The venue stage must run **after**
the colouring, because moving a class in time invalidates its room assignment — but never
the other way round.

---

## 1. The exact click path

```
AdminDashboard.jsx:70  handleResolve()
   └── api.resolve(faculty)                 frontend/src/api.js:78
        └── PUT /resolve                    backend/app/main.py:141
             └── timetable.resolve_for()    backend/app/timetable.py:482
```

One button → one request → one orchestrating function. The two algorithms live *inside*
that function.

## 2. What `resolve_for()` actually does (timetable.py:482)

| # | Line | Operation | Algorithm |
|---|------|-----------|-----------|
| 1 | `:534` | `_assign_general_courses()` — HDS/GNS pinned to fixed slots | hard pre-colouring |
| 2 | `:543` | `greedy_colour_count()` — baseline for comparison metrics | greedy (benchmark only) |
| 3 | `:545` | `build_graph()` — nodes = courses, edges = hard clashes | graph construction |
| 4 | `:548` | `_precolour_general_nodes()` | constraint propagation |
| 5 | `:550` | `dsatur_colour()` — **decides DAY + TIME** | **DSATUR colouring** |
| 6 | `:552` | `apply_colours()` — write day/time back to the ORM objects | — |
| 7 | `:563` | `reassign_venues()` — **decides VENUE** | **greedy best-fit allocation** |
| 8 | `:568–685` | repair loop — re-detect conflicts, relocate stragglers, and **re-run `reassign_venues()` at `:683` after every time change** | local search / repair |
| 9 | `:687` | `db.commit()` | — |

## 3. Why venue conflicts are NOT edges in the graph

Documented in the code itself — `scheduler.py:110–134`:

```python
def courses_conflict(a, b) -> bool:
    """... Venue conflicts are NOT edges — they are resolved by venue reassignment."""
    ...
    # Venue conflicts are handled by venue reassignment, not by the graph
    return same_cohort or same_lecturer
```

An **edge** in graph colouring asserts: *"these two courses can never share a time slot."*

* **Cohort clash** — the same students would need to be in two places → genuinely
  unsolvable at the same time → **edge**.
* **Lecturer clash** — one lecturer, two rooms → unsolvable at the same time → **edge**.
* **Venue clash** — two classes in NH LAB at 10:00 → **solvable at the same time** by
  moving one class to another hall → **NOT an edge**.

**Consequence if we had modelled venues as edges:** DSATUR would be forced to push those
courses into *different time slots*, increasing the chromatic number (slots used) and
stretching the timetable across more days than necessary — a strictly worse solution to a
problem that did not exist. Separating the two keeps the colour count minimal.

## 4. The two algorithms side by side

| | Time assignment | Venue assignment |
|---|---|---|
| Function | `dsatur_colour()` — `scheduler.py` | `reassign_venues()` — `scheduler.py:466` |
| Paradigm | Graph colouring (DSATUR heuristic) | Greedy best-fit resource allocation |
| Decision variable | colour = (day, time slot) | room string (`course.description`) |
| Objective | minimise colours used + soft penalties | zero room collisions + balanced room load |
| Fields written | `day_of_the_week`, `time_start`, `time_end` | `description` **only** |
| Guarantee | eliminates all cohort/lecturer clashes | best-effort (bounded by physical rooms) |

`reassign_venues()` itself has two phases:

* **Phase 1 — conflict repair** (`:564–586`): for every overlapping pair sharing a room,
  move the second course to the best free venue via `_pick_best_venue()`.
* **Phase 2 — load balancing** (`:592–633`): pull classes off overloaded *shared* venues
  (Auditorium, NH LAB, NW HORIZON LB) into underused *dedicated* faculty halls, so the
  distribution matches the school's real timetable.

## 5. THE CONNECTION — a one-way dependency

> **Changing a course's TIME invalidates its VENUE assignment.
> Changing a course's VENUE can never invalidate its TIME assignment.**

Proof by inspection: every mutation inside `reassign_venues()` is
`c2.description = new_venue` / `c.description = best_dedicated`. It never writes
`day_of_the_week`, `time_start` or `time_end`.

Because the dependency is strictly one-directional, the two algorithms **compose
sequentially and safely**:

```
DSATUR (time)  ──►  rooms now possibly double-booked  ──►  reassign_venues (space)
      ▲                                                            │
      └──── cannot be broken by a venue change (one-way) ◄─────────┘
```

That is exactly why the repair loop reads (`timetable.py:682`):

```python
if moved_any:
    reassign_venues(courses, faculty_code)   # a time changed → rooms are stale
else:
    break                                    # nothing moved → nothing stale → done
```

**Venue reassignment is a repair operator invoked after every time mutation** — that is
the whole of the coupling. It is not part of the colouring, and the colouring is not part
of it.

## 6. Anticipated follow-up questions

**Q: Why not design a single algorithm that assigns time and venue together?**
Joint time-and-room assignment is a multi-dimensional NP-hard problem. Decomposition
("schedule, then allocate") is the standard approach in the timetabling literature, and
mirrors compilers (instruction scheduling → register allocation). It is provably safe here
because of the one-way dependency in §5, and it preserves DSATUR's minimal colour count.

**Q: Does venue reassignment always succeed?**
No — and the system is honest about it. `_pick_best_venue()` returns `None` when no room is
free (`scheduler.py:530`); the course keeps its current venue and stays flagged as a venue
overlap. This is why the UI reports *"Resolved with N minor venue overlap(s) remaining"*
(`AdminDashboard.jsx:78`). Time conflicts are eliminated as hard constraints; venue
conflicts are best-effort because they are bounded by **physical room capacity**, not by
algorithmic weakness. Adding a room fixes them; no algorithm can.

**Q: Can the pipeline loop forever?**
No. The repair loop is bounded at 50 iterations (`timetable.py:568`), Phase 1 at 5
(`scheduler.py:565`), Phase 2 at 3 (`scheduler.py:592`), and each exits early via
`if not moved_any: break` when a fixed point is reached.

**Q: Complexity?**
DSATUR ≈ O(V²) over the conflict graph; venue Phase 1 ≈ O(5·n²) pairwise scan;
Phase 2 ≈ O(3·n·|venues|); repair loop bounded — overall polynomial and bounded.

**Q: How is conflict detection kept consistent between the two?**
A single source of truth: `conflict_reason()` (`timetable.py:62`) classifies every clash as
`general` / `cohort` / `lecturer` / `venue`, and `find_conflict_details()` (`:97`) is used
both by the repair loop and by the `/conflicts` reporting endpoint (`main.py:214`). The
dashboard and the resolver therefore agree by construction.

## 7. One-sentence exam answer

*"The button triggers one endpoint, `/resolve`, which runs a two-stage pipeline: DSATUR
colours the conflict graph to decide **when** each class holds, then a separate greedy
allocator decides **where**. Venue was excluded from the graph on purpose, because a room
clash doesn't require a different time slot — only a different room — and the venue stage
must re-run after the colouring because moving a class in time invalidates its room, never
the other way round."*
