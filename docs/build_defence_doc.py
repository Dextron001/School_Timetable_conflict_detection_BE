"""Build the project defence Q&A document (.docx) from structured content.

Run:  python3 docs/build_defence_doc.py
Output: docs/Project_Defence_QA.docx
"""
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BRAND = RGBColor(0x1F, 0x3A, 0x5F)
ACCENT = RGBColor(0x0B, 0x6B, 0x53)
CODE_BG = "F2F3F5"
MONO = "Consolas"

doc = Document()

# ── Page + base styles ────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin = Inches(0.85)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12

for name, size, colour in (("Heading 1", 16, BRAND), ("Heading 2", 13, BRAND),
                           ("Heading 3", 11.5, ACCENT)):
    st = doc.styles[name]
    st.font.name = "Calibri"
    st.font.size = Pt(size)
    st.font.color.rgb = colour
    st.font.bold = True


def shade(paragraph, fill):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def border(paragraph, colour="1F3A5F", size=18, edge="left"):
    pPr = paragraph._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    e = OxmlElement(f"w:{edge}")
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), str(size))
    e.set(qn("w:space"), "8")
    e.set(qn("w:color"), colour)
    bdr.append(e)
    pPr.append(bdr)


def para(text="", bold=False, italic=False, size=11, colour=None,
         align=None, space_after=6, style=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    r.font.size = Pt(size)
    if colour:
        r.font.color.rgb = colour
    if align:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p


def rich(parts, style=None, space_after=6, size=11):
    """parts = list of (text, {bold/italic/mono/colour})."""
    p = doc.add_paragraph(style=style)
    for text, fmt in parts:
        r = p.add_run(text)
        r.bold = fmt.get("bold", False)
        r.italic = fmt.get("italic", False)
        r.font.size = Pt(fmt.get("size", size))
        if fmt.get("mono"):
            r.font.name = MONO
            r.font.size = Pt(fmt.get("size", size) - 1)
        if fmt.get("colour"):
            r.font.color.rgb = fmt["colour"]
    p.paragraph_format.space_after = Pt(space_after)
    return p


def code(lines):
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        r = p.add_run(line if line else " ")
        r.font.name = MONO
        r.font.size = Pt(9)
        pf = p.paragraph_format
        pf.left_indent = Inches(0.22)
        pf.space_after = Pt(1 if i < len(lines) - 1 else 8)
        pf.space_before = Pt(6 if i == 0 else 1)
        shade(p, CODE_BG)


def bullets(items, level=0):
    for it in items:
        style = "List Bullet" if level == 0 else "List Bullet 2"
        if isinstance(it, list):
            rich(it, style=style, space_after=3)
        else:
            p = doc.add_paragraph(it, style=style)
            p.paragraph_format.space_after = Pt(3)


def numbers(items):
    for it in items:
        if isinstance(it, list):
            rich(it, style="List Number", space_after=3)
        else:
            p = doc.add_paragraph(it, style="List Number")
            p.paragraph_format.space_after = Pt(3)


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            mono = val.startswith("`") and val.endswith("`")
            r = p.add_run(val.strip("`"))
            r.font.size = Pt(9)
            if mono:
                r.font.name = MONO
                r.font.size = Pt(8.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def question(num, text):
    p = doc.add_paragraph()
    r = p.add_run(f"Q{num}.  {text}")
    r.bold = True
    r.font.size = Pt(11.5)
    r.font.color.rgb = BRAND
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    border(p, "1F3A5F", 18, "left")
    p.paragraph_format.left_indent = Inches(0.08)
    return p


def answer_label():
    p = doc.add_paragraph()
    r = p.add_run("ANSWER")
    r.bold = True
    r.font.size = Pt(8)
    r.font.color.rgb = ACCENT
    p.paragraph_format.space_after = Pt(2)
    return p


def oneliner(text):
    p = doc.add_paragraph()
    r = p.add_run("⚡ Say this: ")
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = ACCENT
    r2 = p.add_run(text)
    r2.italic = True
    r2.font.size = Pt(10)
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)
    shade(p, "EAF3F0")
    border(p, "0B6B53", 12, "left")
    return p


# ══════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════
for _ in range(4):
    doc.add_paragraph()

para("PROJECT DEFENCE", bold=True, size=13, colour=ACCENT,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("Questions & Model Answers", bold=True, size=26, colour=BRAND,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
para("School Timetable Conflict Detection & Resolution System",
     size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=22)

para("Focus: how the Resolve button, the DSATUR graph-colouring scheduler and "
     "the venue reassignment algorithm relate to one another — plus the full set "
     "of anticipated examiner questions on architecture, algorithms, security and "
     "limitations.",
     italic=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=26)

t = doc.add_table(rows=0, cols=2)
t.style = "Light List Accent 1"
t.alignment = WD_TABLE_ALIGNMENT.CENTER
for k, v in (
    ("System", "Timetable Conflict Detection & Resolution"),
    ("Backend", "Python · FastAPI · SQLAlchemy · SQLite/PostgreSQL"),
    ("Frontend", "React 18 · Vite · Tailwind CSS"),
    ("Core algorithm", "DSATUR graph colouring (time) + greedy best-fit (venue)"),
    ("Auth", "JWT (HS256) + bcrypt, server-side role guards"),
    ("Document", "Defence Q&A — all questions answered"),
):
    cells = t.add_row().cells
    r = cells[0].paragraphs[0].add_run(k)
    r.bold = True
    r.font.size = Pt(9.5)
    r2 = cells[1].paragraphs[0].add_run(v)
    r2.font.size = Pt(9.5)
    cells[0].width = Inches(1.6)
    cells[1].width = Inches(4.4)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# HOW TO USE + CONTENTS
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("How to use this document", level=1)
para("Every question below has a full answer plus a bolded one-line version "
     "(marked ⚡) you can deliver verbatim if the panel is rushing you. File and "
     "line references are included so you can open the code and point at the "
     "exact lines while you speak. Line numbers refer to the current state of "
     "the repository.", space_after=10)

doc.add_heading("Contents", level=2)
toc = [
    ("Section A", "The Resolve button, DSATUR and venue reassignment (Q1–Q10)"),
    ("Section B", "Algorithm design & justification (Q11–Q18)"),
    ("Section C", "Conflict detection logic (Q19–Q23)"),
    ("Section D", "System architecture & technology choices (Q24–Q29)"),
    ("Section E", "Security & access control (Q30–Q33)"),
    ("Section F", "Limitations, testing & future work (Q34–Q38)"),
    ("Appendix", "Quick reference — files, endpoints, constants"),
]
for a, b in toc:
    rich([(f"{a}   ", {"bold": True, "colour": ACCENT, "size": 10}),
          (b, {"size": 10})], space_after=3)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION A
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section A — The Resolve button, DSATUR and venue reassignment",
                level=1)
para("This section answers the central question: if venue reassignment is a "
     "different algorithm from conflict resolution, why does one click run both?",
     italic=True, size=10, space_after=10)

# Q1
question(1, "When I click “Resolve”, what exactly happens from the browser to the database?")
answer_label()
para("One button triggers one HTTP request to one endpoint, which runs a two-stage "
     "pipeline internally. The call chain is:")
code([
    "AdminDashboard.jsx:70   handleResolve()",
    "  └── api.resolve(faculty)              frontend/src/api.js:78",
    "       └── PUT /resolve?faculty=FPAS    backend/app/main.py:141",
    "            └── timetable.resolve_for(db, fac)   backend/app/timetable.py:482",
])
para("resolve_for() is an orchestrator, not a single algorithm. It executes the "
     "following ordered steps:")
table(
    ["#", "Line (timetable.py)", "Operation", "Algorithm"],
    [
        ["1", "534", "_assign_general_courses() — pin HDS/GNS to fixed slots", "Hard pre-assignment"],
        ["2", "543", "greedy_colour_count() — baseline for comparison metrics", "Greedy (benchmark only)"],
        ["3", "545", "build_graph() — nodes = courses, edges = hard clashes", "Graph construction"],
        ["4", "548", "_precolour_general_nodes() — lock general courses", "Constraint propagation"],
        ["5", "550", "dsatur_colour() — decides DAY + TIME", "DSATUR colouring"],
        ["6", "552", "apply_colours() — write day/time back to objects", "—"],
        ["7", "563", "reassign_venues() — decides VENUE", "Greedy best-fit"],
        ["8", "568–685", "Repair loop — re-detect, relocate, re-run venues (line 683)", "Local search / repair"],
        ["9", "687", "db.commit() — persist", "—"],
    ],
    widths=[0.35, 1.05, 3.3, 1.4],
)
para("The endpoint then re-queries the courses and returns both the algorithm "
     "report and the updated timetable (main.py:157–165), which is why the table "
     "on screen refreshes with new times AND new venues at once.")
oneliner("One click, one endpoint, but a two-stage pipeline inside: DSATUR "
         "assigns time, then a separate greedy allocator assigns venue.")

# Q2
question(2, "You said venue reassignment is a different algorithm. So why does Resolve run it too?")
answer_label()
para("Because resolving a timetable is not complete until every class has both a "
     "valid time and a valid room. The two algorithms answer two different "
     "questions:")
bullets([
    [("DSATUR graph colouring", {"bold": True}),
     (" answers ", {}), ("WHEN", {"bold": True}),
     (" — which day and time slot each class occupies.", {})],
    [("Greedy best-fit allocation", {"bold": True}),
     (" answers ", {}), ("WHERE", {"bold": True}),
     (" — which lecture hall or lab it occupies.", {})],
])
para("They are separate because they solve structurally different problems, but "
     "they are invoked together because the user's intent — “give me a working "
     "timetable” — requires both. Running only DSATUR would leave classes "
     "correctly timed but possibly double-booked in the same hall; running only "
     "the venue pass would shuffle rooms without fixing student or lecturer "
     "clashes.")
oneliner("They are different algorithms solving different sub-problems — time "
         "and space — but a usable timetable needs both, so one click runs both.")

# Q3
question(3, "What exactly is the connection between them? (the key question)")
answer_label()
rich([("The connection is a strict ", {}),
      ("one-way dependency", {"bold": True}), (":", {})])
p = doc.add_paragraph()
r = p.add_run("Changing a course's TIME invalidates its VENUE assignment.\n"
              "Changing a course's VENUE can never invalidate its TIME assignment.")
r.bold = True
r.font.size = Pt(11)
r.font.color.rgb = BRAND
p.paragraph_format.left_indent = Inches(0.2)
p.paragraph_format.space_before = Pt(6)
p.paragraph_format.space_after = Pt(8)
shade(p, "EDF1F7")
border(p, "1F3A5F", 14, "left")

para("This is provable by inspection. Every mutation inside reassign_venues() "
     "writes only the venue field:")
code([
    "c2.description = new_venue        # scheduler.py:584",
    "c.description  = best_dedicated   # scheduler.py:629",
])
para("It never touches day_of_the_week, time_start or time_end. Because the "
     "dependency runs in only one direction, the two algorithms compose safely in "
     "sequence: DSATUR moves classes in time, which may leave rooms double-booked, "
     "so the venue pass runs afterwards to repair them — and the venue pass cannot "
     "break DSATUR's guarantee, because moving a class to a different room does "
     "not change who is free at that hour.")
para("That is why the repair loop reads (timetable.py:682):")
code([
    "if moved_any:",
    "    reassign_venues(courses, faculty_code)   # a time changed → rooms stale",
    "else:",
    "    break                                    # nothing moved → nothing stale",
])
rich([("Venue reassignment is therefore best described as a ", {}),
      ("repair operator invoked after every time mutation", {"bold": True}),
      (" — that is the whole of the coupling. It is not part of the colouring, "
       "and the colouring is not part of it.", {})])
oneliner("Time changes invalidate rooms, but room changes never invalidate time — "
         "a one-way dependency, so venue reassignment runs as a repair step after "
         "every time change.")

# Q4
question(4, "Why did you deliberately exclude venue conflicts from the conflict graph?")
answer_label()
para("Because an edge in graph colouring makes a very specific claim: “these two "
     "courses can never share a time slot.” That claim is true for two of the three "
     "conflict types and false for the third.")
table(
    ["Conflict type", "Why it happens", "Solvable at the same time?", "Edge in graph?"],
    [
        ["Cohort", "Same students would be in two places", "No — physically impossible", "YES"],
        ["Lecturer", "One lecturer in two rooms", "No — physically impossible", "YES"],
        ["Venue", "Two classes assigned the same hall", "Yes — move one to another hall", "NO"],
    ],
    widths=[1.0, 2.0, 1.85, 0.85],
)
para("This decision is documented in the source itself (scheduler.py:110–134):")
code([
    "def courses_conflict(a, b) -> bool:",
    '    """... Venue conflicts are NOT edges — they are resolved by',
    '    venue reassignment. ..."""',
    "    ...",
    "    # Venue conflicts are handled by venue reassignment, not by the graph",
    "    return same_cohort or same_lecturer",
])
rich([("The consequence of getting this wrong: ", {"bold": True}),
      ("had venues been modelled as edges, DSATUR would have been forced to push "
       "those courses into different time slots. That inflates the chromatic "
       "number — more slots used, the timetable stretched over more days, more "
       "idle gaps for students — all to solve a problem that could be fixed by "
       "simply opening the door of the hall next door. Separating the two keeps "
       "the colour count minimal.", {})])
oneliner("A room clash doesn't need a different time, only a different room — "
         "making it an edge would waste time slots solving a problem that isn't "
         "a time problem.")

# Q5
question(5, "Walk me through the venue algorithm itself. How does it work?")
answer_label()
para("reassign_venues() (scheduler.py:466) is a greedy best-fit allocator with two "
     "phases. It first builds an occupancy map of (day, hour) → set of rooms in use "
     "via _build_schedule() (scheduler.py:486), so checking whether a room is free "
     "is a set lookup rather than a scan.")
para("Phase 1 — Conflict repair (scheduler.py:564–586)", bold=True)
numbers([
    "Scan every pair of courses; skip pairs that are the same course code or that "
    "do not overlap in time.",
    "If the pair shares a non-empty venue, that is a room collision.",
    "Call _pick_best_venue() for the second course, excluding the contested room.",
    "Update the occupancy map immediately so later pairs see the change.",
    "Repeat up to 5 iterations, exiting early when a pass fixes nothing.",
])
para("Phase 2 — Load balancing (scheduler.py:591–635)", bold=True)
numbers([
    "Compute a target load per venue = total courses ÷ number of venues.",
    "Find courses sitting in SHARED venues (Auditorium, NH LAB, NW HORIZON LB) "
    "whose load exceeds that target.",
    "Move them into the least-used DEDICATED faculty hall that is free at that hour.",
    "Repeat up to 3 iterations, exiting early when nothing moves.",
])
para("The selection rule inside _pick_best_venue() (scheduler.py:534) sorts free "
     "rooms by a two-part key — dedicated halls before shared halls, then by "
     "current load ascending — so it always picks the least-loaded appropriate "
     "room. Phase 2 exists so the output resembles the school's real distribution, "
     "where the Auditorium is used sparingly rather than becoming a dumping ground.")
oneliner("It's a two-phase greedy best-fit: first fix same-room-same-time "
         "collisions, then balance load off shared halls into underused dedicated ones.")

# Q6
question(6, "Why does reassign_venues() get called more than once in a single Resolve?")
answer_label()
para("Because each call is only valid for the timetable as it stood at that moment. "
     "It is called at three points:")
table(
    ["Call site", "Trigger", "Reason"],
    [
        ["timetable.py:563", "Immediately after apply_colours()", "DSATUR has just rewritten every day/time — the entire room map is stale"],
        ["timetable.py:683", "Inside the repair loop, when moved_any is true", "One or more courses just changed slot — their rooms must be re-checked"],
        ["timetable.py:379", "End of the generate/repair helper", "Final sweep before persisting"],
    ],
    widths=[1.25, 1.85, 2.6],
)
para("The pattern is consistent: any code path that mutates a time is immediately "
     "followed by a venue recomputation. If it were called only once, at the "
     "beginning, courses moved later in the repair loop would carry rooms that were "
     "correct for their OLD slot and possibly double-booked in their new one.")
oneliner("Every time mutation makes the room map stale, so the venue pass re-runs "
         "after each one — it's idempotent, so extra calls are safe.")

# Q7
question(7, "Could you run venue reassignment BEFORE the colouring instead?")
answer_label()
para("No — and the one-way dependency explains precisely why. Before DSATUR runs, "
     "the courses still hold their draft times from generate_for(). Rooms allocated "
     "against those draft times would be discarded the instant apply_colours() "
     "rewrote every day and time. The allocation would be computed against a "
     "timetable that no longer exists.")
para("The reverse ordering is safe for the same reason it is required: because the "
     "venue stage reads times but never writes them, it can always be run last "
     "against a finished schedule, and it will never invalidate the stage before it.")
oneliner("No — room allocation depends on final times, so it must run after the "
         "colouring, never before.")

# Q8
question(8, "Does the venue stage ever fail? What happens then?")
answer_label()
para("Yes, and the system reports it honestly rather than hiding it. "
     "_pick_best_venue() returns None when no room is free for that day and hour "
     "(scheduler.py:530). The calling code checks the return value:")
code([
    "new_venue = _pick_best_venue(c2, venue_schedule, exclude=c.description)",
    "if new_venue:                 # only reassign when a room was actually found",
    "    c2.description = new_venue",
])
para("If nothing is free, the course keeps its current room and remains flagged as "
     "a venue overlap by find_conflict_details(). This surfaces to the admin in the "
     "toast message (AdminDashboard.jsx:79):")
code(['"Resolved with N minor venue overlap(s) remaining."'])
rich([("The distinction to stress: ", {"bold": True}),
      ("time conflicts are eliminated as hard logical constraints, while venue "
       "conflicts are best-effort because they are bounded by ", {}),
      ("physical room capacity", {"bold": True}),
      (", not by algorithmic weakness. If more classes overlap at 10 a.m. than the "
       "faculty has halls, no algorithm on earth can place them — the fix is "
       "another building, and the system correctly tells the admin instead of "
       "pretending.", {})])
oneliner("Yes — when no room is free the overlap is reported, not hidden, because "
         "that's a capacity limit, not an algorithm failure.")

# Q9
question(9, "Prove that venue reassignment cannot re-introduce a time conflict.")
answer_label()
para("Three-step argument:")
numbers([
    "conflict_reason() (timetable.py:62) classifies a clash as cohort, lecturer, "
    "general or venue. The first three depend only on department, academic_level, "
    "lecturer_name, day and time — never on the venue field.",
    "reassign_venues() writes only course.description (the venue). Verified by "
    "inspection: the only assignments in the whole function are "
    "c2.description = new_venue and c.description = best_dedicated.",
    "Therefore no cohort, lecturer or general conflict test can change value as a "
    "result of the venue pass. Only the venue test can change — and it can only "
    "improve, because a reassignment is performed only when the target room is "
    "verified free by _is_free().",
])
para("So the venue stage is monotone with respect to correctness: it strictly "
     "reduces or preserves the total conflict count, and it can never undo "
     "DSATUR's guarantee.")
oneliner("It writes only the venue field, and the cohort, lecturer and general "
         "conflict tests never read that field — so it's provably safe.")

# Q10
question(10, "Draw the relationship between the two algorithms.")
answer_label()
para("The pipeline and its one-way dependency:")
code([
    "            ┌──────────────────────────────────────────────┐",
    "  CLICK ───►│  PUT /resolve   →   resolve_for()            │",
    "            └──────────────────────────────────────────────┘",
    "                              │",
    "                              ▼",
    "        ┌───────────────────────────────────────────┐",
    "        │  STAGE 1 — TIME                           │",
    "        │  DSATUR graph colouring                   │",
    "        │  writes: day_of_the_week, time_start/end  │",
    "        └───────────────────────────────────────────┘",
    "                              │",
    "            rooms are now stale (times changed)",
    "                              ▼",
    "        ┌───────────────────────────────────────────┐",
    "        │  STAGE 2 — SPACE                          │",
    "        │  reassign_venues()  (greedy best-fit)     │",
    "        │  writes: description (venue) ONLY         │",
    "        └───────────────────────────────────────────┘",
    "                              │",
    "                              ▼",
    "        ┌───────────────────────────────────────────┐",
    "        │  REPAIR LOOP (≤50 passes)                 │",
    "        │  conflicts left? → move course → back to  │",
    "        │  STAGE 2 for that course's new slot       │",
    "        └───────────────────────────────────────────┘",
    "                              │",
    "                        db.commit()",
    "",
    "  Dependency direction:  TIME ──influences──► SPACE",
    "                         SPACE ──✗ never──►  TIME",
])
oneliner("Time flows into space, never the reverse — that arrow is the entire "
         "relationship between the two algorithms.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION B
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section B — Algorithm design & justification", level=1)

question(11, "Why graph colouring for timetabling? Why not just brute force or random assignment?")
answer_label()
para("Timetabling is a textbook instance of the graph colouring problem, which is "
     "NP-hard. Model each course as a vertex, each hard clash as an edge, and each "
     "(day, time slot) pair as a colour. A valid timetable is exactly a proper "
     "colouring: no two adjacent vertices share a colour.")
para("With 5 days × 8 slots = 40 colours (scheduler.py:29) and hundreds of courses, "
     "brute force is 40^n — computationally impossible. Random assignment gives no "
     "guarantee and, as the original prototype showed, leaves clashes behind. "
     "Graph colouring gives a principled model with a large body of proven "
     "heuristics, of which DSATUR is among the strongest for its cost.")
oneliner("Timetabling IS graph colouring — courses are vertices, clashes are edges, "
         "time slots are colours — so I used a proven colouring heuristic instead "
         "of guessing.")

question(12, "Why DSATUR specifically, and not simple greedy colouring?")
answer_label()
para("Greedy colouring processes vertices in arbitrary order and is highly "
     "order-sensitive — a poor order uses far more colours than necessary. DSATUR "
     "(Degree of Saturation, Brélaz 1979) instead picks, at each step, the vertex "
     "with the highest saturation — the most distinct colours already used by its "
     "neighbours — breaking ties by highest degree (_pick_next, scheduler.py:150).")
para("Intuitively it always colours the most constrained course next, while it "
     "still has options, rather than painting itself into a corner. DSATUR is "
     "exact for bipartite graphs and consistently near-optimal in practice.")
rich([("Crucially, this project does not merely assert that — it ", {}),
      ("measures", {"bold": True}),
      (" it. greedy_colour_count() (scheduler.py:637) runs a greedy baseline over "
       "the same graph without mutating the courses, and the /resolve response "
       "returns a comparison block:", {})])
code([
    '"comparison": {',
    '    "dsatur_slots":   colours_used,    "greedy_slots":   greedy_slots,',
    '    "dsatur_penalty": soft_penalty,    "greedy_penalty": greedy_penalty,',
    "}",
])
para("That is empirical justification you can show live on the dashboard.")
oneliner("DSATUR colours the most constrained course first instead of an arbitrary "
         "order — and I benchmark it against greedy on every run to prove it.")

question(13, "How do you handle soft constraints — lunch hour, spreading across days?")
answer_label()
para("Hard constraints are enforced structurally, by edges. Soft constraints are "
     "handled by a weighted cost function, _selection_cost() (scheduler.py:163), "
     "which scores every candidate colour; the lowest-cost feasible colour wins.")
table(
    ["Penalty constant", "Value", "Purpose"],
    [
        ["LUNCH_PENALTY", "5", "Avoid the 12:00–13:00 break slot"],
        ["LATE_PENALTY", "2", "Discourage 16:00–17:00 classes"],
        ["DAY_OVERLOAD_PENALTY", "8", "Spread courses evenly across the 5 days"],
        ["COHORT_DAY_LIMIT_PENALTY", "10", "Stop one cohort being stacked on one day"],
        ["SESSION_DIFFERENT_DAY_PENALTY", "50", "3-unit session B must differ from session A"],
        ["OVERCROWD_PENALTY", "50", "Penalise exceeding available venue capacity"],
    ],
    widths=[2.2, 0.7, 3.0],
)
para("The magnitudes encode priority: a near-hard rule such as session separation "
     "scores 50, ten times the cost of a lunch-hour class, so the optimiser will "
     "always sacrifice the lunch preference before it violates session separation.")
oneliner("Hard constraints are graph edges; soft constraints are weighted penalties "
         "in a cost function, so the scheduler trades off preferences by priority.")

question(14, "OVERCROWD_PENALTY mentions venues — doesn't that contradict your claim that the graph ignores venues?")
answer_label()
para("A sharp question, and the distinction matters. The graph ignores venue "
     "IDENTITY — which specific room a class is in. The cost function is aware of "
     "venue CAPACITY — how many rooms exist in total.")
para("At timetable.py:541 the threshold is set dynamically:")
code([
    "venues = FACULTY_VENUES.get(faculty_code, FACULTY_VENUES['FPAS'])",
    "sch.OVERCROWD_THRESHOLD = len(venues)   # FPAS = 18 rooms, FSMS = 11",
])
para("If 19 FPAS classes were colour-scheduled into the same hour, no allocation "
     "could ever succeed — 19 classes cannot fit in 18 rooms. Rather than let the "
     "colouring create an impossible situation and then fail downstream, the cost "
     "function applies a heavy penalty (50 per excess class) to any slot already at "
     "capacity, steering DSATUR to spread the load.")
rich([("So the two stages cooperate through a single scalar — ", {}),
      ("a count, not an assignment", {"bold": True}),
      (". The colouring never decides which room; it only avoids creating slots "
       "the allocator provably cannot serve. This is a soft feasibility hint, not "
       "a hard edge.", {})])
oneliner("The graph ignores which room; the cost function only knows how many "
         "rooms exist, so it avoids over-filling an hour beyond total capacity.")

question(15, "How do you handle multi-unit courses — 2-hour blocks and split sessions?")
answer_label()
para("The Node dataclass carries two colours: colour and colour2 (scheduler.py:80). "
     "duration_hours() (scheduler.py:68) derives the span from credit units:")
bullets([
    "1-unit → one 1-hour slot (one colour).",
    "2-unit → one 2-hour block on a single day (colour + colour2, consecutive).",
    "3-unit → session A as a 2-hour block, plus session B as a separate 1-hour "
    "class on a DIFFERENT day.",
    "6-unit project courses and SIWES are excluded from scheduling entirely "
    "(timetable.py:504).",
])
para("Consecutive pairing uses the precomputed NEXT_CONSECUTIVE map "
     "(scheduler.py:34), which links each colour to the colour one hour later on "
     "the same day, so a 2-hour block can never straddle two different days or "
     "wrap around the lunch break. When a neighbour occupies a 2-hour block, BOTH "
     "its colours are added to the forbidden set, so no other class can slip into "
     "its second hour.")
para("Session B being on a different day from session A is enforced in two places: "
     "as a heavy penalty during colouring, and as an explicit check in the repair "
     "loop (timetable.py:626).")
oneliner("Credit units map to colour spans — 2-hour blocks take two consecutive "
         "colours via a precomputed adjacency map, and 3-unit session B is forced "
         "onto a different day.")

question(16, "What are general courses and why are they pre-coloured?")
answer_label()
para("General courses — the HDS and GNS series — are taken by every student at a "
     "given level, across all departments. The university fixes their slots "
     "centrally, so they are inputs to the problem, not decisions the scheduler is "
     "free to make. GENERAL_COURSE_SLOTS (timetable.py:25) hardcodes them, e.g. "
     "100-level general courses occupy Monday, 200-level Tuesday.")
para("_precolour_general_nodes() (timetable.py:145) assigns those nodes their "
     "colour BEFORE DSATUR starts. dsatur_colour() then treats pre-coloured nodes "
     "as fixed: it skips them, seeds them into the usage statistics, and propagates "
     "their colours into every neighbour's saturation set (scheduler.py:291–309). "
     "Every other course is therefore scheduled around them automatically.")
para("The edge rule reflects the semantics precisely (scheduler.py:120–128): a "
     "general course conflicts with every NON-general course at the same level, "
     "because all those students attend it — but two general courses at the same "
     "level do NOT conflict with one another, because they are the same lecture "
     "delivered to the same hall. Duplicate copies per department are merged before "
     "scheduling and re-synchronised afterwards (timetable.py:555–561).")
oneliner("They're university-fixed and taken by everyone at a level, so they're "
         "pre-coloured as hard constraints and every other course is scheduled "
         "around them.")

question(17, "What is the time complexity, and can the algorithm loop forever?")
answer_label()
table(
    ["Stage", "Complexity", "Bound"],
    [
        ["build_graph()", "O(V²) pairwise comparison", "—"],
        ["dsatur_colour()", "≈ O(V² + V·C), C = 40 colours", "One pass"],
        ["reassign_venues() Phase 1", "O(n²) per iteration", "5 iterations max (scheduler.py:565)"],
        ["reassign_venues() Phase 2", "O(n · |venues|) per iteration", "3 iterations max (scheduler.py:593)"],
        ["Repair loop", "O(n²) per attempt", "50 attempts max (timetable.py:568)"],
    ],
    widths=[1.6, 2.2, 2.1],
)
para("Termination is guaranteed twice over: every loop has a hard iteration cap, "
     "AND every loop exits early at a fixed point via a moved / any_fixed flag "
     "(if not moved: break). So the worst case is bounded polynomial time and the "
     "typical case terminates in far fewer passes. In practice a full faculty "
     "resolves in well under a second.")
oneliner("Polynomial overall, and every loop has both a hard iteration cap and an "
         "early fixed-point exit, so it cannot hang.")

question(18, "Is your solution optimal? Can you guarantee the best possible timetable?")
answer_label()
para("No, and claiming otherwise would be wrong. Graph colouring is NP-hard, so no "
     "polynomial algorithm guarantees the chromatic minimum unless P = NP. DSATUR "
     "is a heuristic: it is exact for certain graph classes such as bipartite "
     "graphs, and near-optimal in practice, but it carries no general optimality "
     "guarantee.")
para("What the system does guarantee is stronger and more useful for the user:")
bullets([
    "Feasibility — all cohort, lecturer and general-course conflicts are eliminated "
    "or explicitly reported.",
    "Measurable quality — the soft penalty and colour count are compared against a "
    "greedy baseline on every run.",
    "Transparency — anything it cannot fix is surfaced to the admin rather than "
    "silently ignored.",
])
oneliner("No — the problem is NP-hard, so I use a near-optimal heuristic and prove "
         "its quality by benchmarking it against greedy on every run.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION C
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section C — Conflict detection logic", level=1)

question(19, "How do you detect that two courses conflict?")
answer_label()
para("A single source of truth: conflict_reason() (timetable.py:62). It returns the "
     "cause of a clash or None. The order of tests matters — cheap exclusions first, "
     "then the overlap test, then cause classification.")
code([
    "if a.id == b.id:                    return None   # same row",
    "if a.course_code == b.course_code:  return None   # sessions of one course",
    "if not _time_overlap(a, b):         return None   # no temporal overlap",
    "# ... then classify: general → cohort → lecturer → venue",
])
para("The overlap test itself is the standard interval-intersection predicate "
     "(timetable.py:52): two courses overlap when they share a day AND")
code(["start_A < end_B  AND  end_A > start_B"])
para("Times are compared as minutes-since-midnight via time_to_min(), not as "
     "strings, so 09:00–11:00 and 10:00–12:00 are correctly detected as "
     "overlapping even though neither starts at the same time.")
oneliner("Same day plus the interval-intersection test start_A < end_B and "
         "end_A > start_B, evaluated in minutes since midnight.")

question(20, "What are the four conflict types your system reports?")
answer_label()
table(
    ["Cause", "Meaning", "Severity", "Resolution strategy"],
    [
        ["cohort", "Same department + level, overlapping times", "Hard", "Move to another time slot (graph edge)"],
        ["lecturer", "Same lecturer in two places", "Hard", "Move to another time slot (graph edge)"],
        ["general", "A general course clashes with a normal course at that level", "Hard", "The normal course moves; general is fixed"],
        ["venue", "Same room, overlapping times", "Soft", "Reassign the room, keep the time"],
    ],
    widths=[0.85, 2.35, 0.7, 2.1],
)
para("find_conflict_details() (timetable.py:97) returns, for every clashing pair, "
     "both course IDs and codes, the cause, a human-readable detail string, the day "
     "and the exact overlap window — so the dashboard can tell the admin not just "
     "THAT something clashes but WHY and WHEN.")
oneliner("Cohort, lecturer and general are hard time conflicts; venue is a soft "
         "space conflict — and each is reported with its cause and overlap window.")

question(21, "How do the dashboard's red rows and the resolver stay in agreement?")
answer_label()
para("They share one implementation. The GET /conflicts endpoint (main.py:198) "
     "calls find_conflicts() and find_conflict_details() — the exact same functions "
     "the repair loop calls at timetable.py:569. There is no second, duplicated "
     "definition of what a conflict is.")
para("This matters: if detection and resolution used separate logic they could "
     "drift, and the UI would paint rows red that the resolver believed were fine. "
     "Sharing the predicate makes agreement structural rather than coincidental.")
oneliner("Both the UI and the resolver call the same conflict_reason() function, so "
         "they agree by construction, not by luck.")

question(22, "Why don't two sessions of the same course conflict with each other?")
answer_label()
para("A 3-unit course is stored as two rows sharing one course_code — session A "
     "(a 2-hour block) and session B (a 1-hour class on another day). They are the "
     "same class meeting twice, not two competing classes, so a naive pairwise "
     "check would flag a false conflict.")
para("Both conflict_reason() (timetable.py:67) and courses_conflict() "
     "(scheduler.py:118) therefore short-circuit on equal course codes. Their "
     "genuine requirement — that session B falls on a different day from session A "
     "— is enforced separately, by SESSION_DIFFERENT_DAY_PENALTY during colouring "
     "and by an explicit day check in the repair loop (timetable.py:630).")
oneliner("They're the same class meeting twice, so equal course codes are excluded "
         "from the conflict test and handled by a separate different-day rule.")

question(23, "The README mentions a time-format bug. What was it?")
answer_label()
para("The original prototype stored afternoon times in 12-hour form — 1:00 for "
     "1 p.m. String or naive integer parsing read that as 01:00, one o'clock in the "
     "morning. A 1 p.m. class therefore appeared to be four hours BEFORE a 9 a.m. "
     "class, so overlap detection silently missed real clashes.")
para("The fix was to standardise on 24-hour HH:MM strings throughout, documented on "
     "the model itself (models.py: “time_start / time_end are stored as 24-hour "
     "'HH:MM' strings”), and to convert to minutes before any comparison via "
     "time_to_min(). It is worth raising proactively: it demonstrates that you "
     "tested your detection logic rather than assuming it worked.")
oneliner("Afternoon times were stored as 1:00 instead of 13:00 and parsed as 1 a.m., "
         "silently breaking overlap detection — fixed by standardising on 24-hour "
         "HH:MM and comparing in minutes.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION D
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section D — System architecture & technology choices", level=1)

question(24, "Describe the overall architecture.")
answer_label()
para("A three-tier client–server application with a clean separation of concerns:")
code([
    "┌──────────────────────────────────────────────────────┐",
    "│  PRESENTATION — React 18 + Vite + Tailwind           │",
    "│  pages/ (Admin, Client, Login, Users)                │",
    "│  components/ (TimetableTable, modals, Complaints)    │",
    "│  api.js — single fetch wrapper, attaches JWT          │",
    "└──────────────────────────────────────────────────────┘",
    "                    │ HTTPS / JSON",
    "┌──────────────────────────────────────────────────────┐",
    "│  APPLICATION — Python + FastAPI                      │",
    "│  main.py       — routes + role guards                │",
    "│  auth.py       — JWT + bcrypt                        │",
    "│  timetable.py  — detection, generate, resolve         │",
    "│  scheduler.py  — DSATUR + venue allocation           │",
    "│  pdf_export.py — ReportLab export                    │",
    "└──────────────────────────────────────────────────────┘",
    "                    │ SQLAlchemy ORM",
    "┌──────────────────────────────────────────────────────┐",
    "│  DATA — SQLite (dev) / PostgreSQL (production)       │",
    "│  users · course_items · complaints · messages        │",
    "└──────────────────────────────────────────────────────┘",
])
para("The algorithmic core (scheduler.py) is deliberately free of database and web "
     "concerns — it operates on plain objects with the right attributes, which is "
     "why the unit tests can drive it with SimpleNamespace stand-ins and a FakeDB "
     "(tests/test_scheduler.py). That is a real design benefit, not an accident.")
oneliner("Three tiers — React front end, FastAPI application layer, SQLAlchemy data "
         "layer — with the scheduling algorithm isolated from both web and DB concerns.")

question(25, "Why FastAPI, React and SQLAlchemy?")
answer_label()
bullets([
    [("FastAPI", {"bold": True}),
     (" — native async, Pydantic request/response validation, dependency injection "
      "for auth and DB sessions, and automatic OpenAPI docs at /docs which you can "
      "demo live. Python also keeps the scheduling algorithm readable.", {})],
    [("React + Vite", {"bold": True}),
     (" — component reuse across the admin and client dashboards, and instant "
      "hot-module reload during development.", {})],
    [("SQLAlchemy", {"bold": True}),
     (" — database portability. The project develops on SQLite with zero setup and "
      "deploys on PostgreSQL by changing one environment variable; database.py:14–22 "
      "even rewrites legacy postgres:// URLs and selects the psycopg v3 driver "
      "automatically.", {})],
    [("Tailwind", {"bold": True}),
     (" — consistent styling driven by CSS variables, enabling the light/dark theme "
      "toggle without duplicated stylesheets.", {})],
])
oneliner("FastAPI for validation and auto-generated docs, React for reusable "
         "dashboards, SQLAlchemy so SQLite in development becomes PostgreSQL in "
         "production with one variable.")

question(26, "Explain your data model.")
answer_label()
table(
    ["Table", "Purpose", "Notable fields"],
    [
        ["users", "Accounts and roles", "username, hashed_password, role (admin|client)"],
        ["course_items", "One scheduled class session", "department, academic_level, course_code, lecturer_name, day_of_the_week, time_start, time_end, units, session, description (venue)"],
        ["complaints", "Student-raised timetable issues", "faculty, subject, message, status, resolved_by, resolved_at"],
        ["complaint_messages", "Threaded admin↔student replies", "complaint_id, sender_role, message"],
    ],
    widths=[1.25, 1.7, 3.05],
)
para("One point invites a challenge, so raise it first: the venue is stored in the "
     "description column rather than a dedicated venue column. That is inherited "
     "from the original schema and is documented in the model ("
     "“description … used as venue/room”). Functionally correct, but in a future "
     "iteration I would rename it to venue_id and normalise venues into their own "
     "table with capacity and equipment attributes — which would also let the "
     "allocator match class size to room size.")
oneliner("Four tables — users, course_items, complaints and messages — with the "
         "venue currently stored in description, which I'd normalise into a proper "
         "venues table next.")

question(27, "What is the difference between Generate and Resolve?")
answer_label()
table(
    ["", "Generate (PUT /generate)", "Resolve (PUT /resolve)"],
    [
        ["Purpose", "Create a first draft timetable", "Make an existing timetable clash-free"],
        ["Method", "Randomised placement with light balancing", "DSATUR colouring + venue allocation + repair"],
        ["Function", "generate_for() — timetable.py:373", "resolve_for() — timetable.py:482"],
        ["Guarantee", "None — conflicts expected", "Hard time conflicts eliminated"],
        ["Typical use", "Start of a new semester", "After generating, or after manual edits"],
    ],
    widths=[0.85, 2.6, 2.55],
)
para("The two-step flow is intentional and pedagogically useful: Generate produces "
     "a deliberately imperfect draft so the conflict detector has something real to "
     "find and highlight in red, and Resolve then demonstrably fixes it. In a demo, "
     "click Generate, show the red rows and the conflict count, then click Resolve "
     "and show them disappear.")
oneliner("Generate creates a rough draft with conflicts; Resolve applies DSATUR and "
         "venue allocation to eliminate them — which also makes for a compelling demo.")

question(28, "How does PDF export work?")
answer_label()
para("GET /export-pdf (main.py:222) loads the faculty's courses, recomputes the "
     "conflict IDs, and passes both into build_timetable_pdf() (pdf_export.py), "
     "which uses ReportLab to lay out a printable timetable grouped by weekday. "
     "The result is returned as a StreamingResponse with a Content-Disposition "
     "attachment header, so the browser downloads it directly rather than buffering "
     "the whole file in memory first.")
para("Note that conflict IDs are passed into the PDF builder, so any residual "
     "clash remains visible in the exported document — the export does not quietly "
     "present a broken timetable as clean.")
oneliner("ReportLab builds a weekday-grouped PDF streamed straight to the browser, "
         "with any residual conflicts still flagged in the output.")

question(29, "How does the complaint system fit in?")
answer_label()
para("It closes the feedback loop. Automated scheduling cannot know that a "
     "particular lab is unavailable on Fridays or that a lecturer has an external "
     "commitment, so students and staff need a channel to report real-world "
     "problems the algorithm cannot see.")
para("A student submits a complaint (POST /complaints), optionally triggering an "
     "email to the admin (email_service.py, disabled unless SMTP is configured). "
     "The admin reviews it in ComplaintsPanel, replies through a threaded message "
     "system (complaint_messages), and marks it resolved or dismissed — which "
     "stamps resolved_at and resolved_by for accountability. The admin can then "
     "edit the affected course manually via PATCH /courses/{id}.")
oneliner("It's the human feedback loop for constraints the algorithm can't know "
         "about, with threaded replies and an audit trail of who resolved what.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION E
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section E — Security & access control", level=1)

question(30, "How is authentication implemented?")
answer_label()
para("Passwords are hashed with bcrypt through passlib (auth.py:25) — never stored "
     "in plain text, and bcrypt's per-password salt and deliberate slowness resist "
     "rainbow-table and brute-force attacks. On successful login the server issues "
     "a JWT signed with HS256 (auth.py:39) carrying the username as sub and an "
     "8-hour expiry. The React client attaches it as a Bearer token on every "
     "request through the single api.js wrapper.")
para("get_current_user() (auth.py:45) validates the signature and expiry on each "
     "request and loads the user, raising 401 with a WWW-Authenticate header on any "
     "failure. Because JWTs are stateless, no server-side session store is needed.")
oneliner("bcrypt-hashed passwords plus stateless HS256 JWTs with an 8-hour expiry, "
         "validated on every request.")

question(31, "How do you stop a student from editing the timetable?")
answer_label()
para("Enforcement is server-side, which is the only enforcement that counts. "
     "require_admin() (auth.py:69) is a FastAPI dependency that raises 403 unless "
     "role == 'admin', and it is attached to every mutating endpoint: /generate, "
     "/resolve, POST/PATCH/DELETE /courses, and all user management routes.")
para("Hiding buttons in the UI is convenience, not security. A student who crafted "
     "a direct PUT /resolve request with their own valid token would still be "
     "rejected with 403, because the check lives in the dependency chain of the "
     "route itself — the request never reaches the handler body.")
oneliner("A require_admin dependency guards every mutating route server-side, so "
         "hiding UI buttons is convenience — the 403 is the real protection.")

question(32, "Is anything about your security setup weak?")
answer_label()
para("Answer honestly; examiners reward it. Three known weaknesses:")
bullets([
    [("Default secret key", {"bold": True}),
     (" — auth.py:18 falls back to 'dev-secret-change-me-in-production' when "
      "SECRET_KEY is unset. Convenient for development, but in production an unset "
      "variable would let anyone forge tokens. It must be set in the deployment "
      "environment; a stricter version would refuse to start without it.", {})],
    [("No token revocation", {"bold": True}),
     (" — stateless JWTs remain valid until they expire, so a compromised token "
      "cannot be invalidated early. A refresh-token scheme or a short deny-list "
      "would address it.", {})],
    [("No rate limiting", {"bold": True}),
     (" — the login endpoint accepts unlimited attempts. bcrypt's slowness helps, "
      "but per-IP throttling would be the proper fix.", {})],
])
oneliner("Yes — a fallback dev secret, no token revocation, and no login rate "
         "limiting; I know each of them and how I'd fix them.")

question(33, "How are secrets and configuration managed?")
answer_label()
para("Configuration is read from environment variables via python-dotenv, with "
     "safe defaults for local development: DATABASE_URL (database.py:14), "
     "SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES (auth.py), and the SMTP settings "
     "(email_service.py:21–26). Nothing sensitive is hardcoded into committed "
     "source, and email is disabled by default so a missing configuration degrades "
     "gracefully — the complaint is still stored and shown on the dashboard, it "
     "just does not send mail.")
oneliner("Environment variables through python-dotenv with safe local defaults, and "
         "features like email degrade gracefully when unconfigured.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# SECTION F
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Section F — Limitations, testing & future work", level=1)

question(34, "How did you test the scheduler?")
answer_label()
para("backend/tests/test_scheduler.py drives the algorithm directly with "
     "SimpleNamespace course objects and a FakeDB stub, asserting structural "
     "properties rather than fixed outputs. Examples: all courses in one cohort end "
     "up in distinct (day, slot) pairs; a shared lecturer is never double-booked; "
     "find_residual_clashes() returns an empty list after scheduling.")
para("Property-based assertions are the right approach here, because a heuristic "
     "may legitimately produce different valid timetables on different runs — what "
     "must hold every time is the absence of clashes, not one specific arrangement.")
oneliner("Property-based unit tests with stub objects, asserting no residual "
         "clashes rather than one fixed expected timetable.")

question(35, "What are the main limitations of the system?")
answer_label()
bullets([
    "Venue conflicts are best-effort — if demand at an hour exceeds the number of "
    "rooms, some overlap remains and is reported.",
    "No room capacity or equipment matching — venues are interchangeable strings, "
    "so a 300-student class could be placed in a small hall.",
    "No lecturer availability windows — the model assumes lecturers are free all "
    "week except where already scheduled.",
    "General course slots are hardcoded in GENERAL_COURSE_SLOTS rather than being "
    "admin-configurable.",
    "No optimality guarantee — DSATUR is a heuristic (see Q18).",
    "Single-semester scope — no academic session or versioning model.",
])
oneliner("Best-effort venue allocation, no room capacity or lecturer availability "
         "modelling, and hardcoded general slots — all known and all addressable.")

question(36, "How would you extend it to handle room capacity?")
answer_label()
numbers([
    "Normalise venues into their own table with capacity, type (lab / lecture hall) "
    "and equipment columns.",
    "Add an expected_students field to course_items.",
    "Extend _pick_best_venue() (scheduler.py:514) to filter out rooms whose capacity "
    "is below the enrolment before sorting the remaining candidates.",
    "Add capacity mismatch to the sort key so a class is placed in the smallest "
    "adequate room, preserving large halls for large classes.",
])
rich([("The important point for the panel: this change is confined almost entirely "
       "to one function, ", {}),
      ("because venue selection is already decoupled from time assignment", {"bold": True}),
      (". That is the architectural payoff of separating the two algorithms.", {})])
oneliner("Add capacity to a normalised venues table and filter inside "
         "_pick_best_venue — a change confined to one function precisely because "
         "venue selection is decoupled from timing.")

question(37, "What would you do differently if you started again?")
answer_label()
bullets([
    "Normalise venues from day one instead of overloading the description column.",
    "Model lecturer availability as first-class data rather than assuming full "
    "availability.",
    "Make general-course slots admin-configurable instead of hardcoded.",
    "Add structured logging around the repair loop so the sequence of moves is "
    "auditable and explainable to an admin.",
    "Consider a metaheuristic — simulated annealing or tabu search — as an optional "
    "post-pass to reduce the soft penalty further after DSATUR reaches feasibility.",
])
oneliner("Normalise venues, model lecturer availability properly, make general "
         "slots configurable, and add a metaheuristic polish pass after DSATUR.")

question(38, "What is your single biggest technical contribution in this project?")
answer_label()
para("The correct decomposition of the scheduling problem into two coupled but "
     "independent sub-problems, with a proof that the coupling is safe.")
para("Most naive implementations treat every conflict identically and push all of "
     "them into a single search, which wastes time slots on room clashes that a "
     "simple reassignment would fix. By recognising that a venue clash is a space "
     "problem rather than a time problem, this system:")
bullets([
    "keeps the chromatic number — and therefore the number of slots and days used "
    "— minimal;",
    "guarantees that hard human constraints (students and lecturers) are eliminated;",
    "isolates the physically-bounded part of the problem (rooms) so failures there "
    "are reported honestly rather than corrupting the schedule;",
    "makes future extensions such as room capacity local to one function.",
])
oneliner("Recognising that room clashes are a space problem, not a time problem, "
         "and decomposing the solver accordingly with a one-way dependency that "
         "makes the two stages provably safe to compose.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ══════════════════════════════════════════════════════════════════════════
# APPENDIX
# ══════════════════════════════════════════════════════════════════════════
doc.add_heading("Appendix — Quick reference", level=1)

doc.add_heading("Key functions and where to point", level=2)
table(
    ["Function", "File : line", "Role"],
    [
        ["resolve_for()", "timetable.py:482", "Orchestrates the whole Resolve pipeline"],
        ["conflict_reason()", "timetable.py:62", "Single source of truth for what a clash is"],
        ["find_conflict_details()", "timetable.py:97", "Detailed clash report used by UI and resolver"],
        ["_precolour_general_nodes()", "timetable.py:145", "Locks general courses before colouring"],
        ["courses_conflict()", "scheduler.py:110", "Defines graph edges (venue deliberately excluded)"],
        ["build_graph()", "scheduler.py:138", "Builds the conflict graph"],
        ["dsatur_colour()", "scheduler.py:269", "DSATUR colouring — assigns day + time"],
        ["_selection_cost()", "scheduler.py:163", "Soft-constraint cost function"],
        ["apply_colours()", "scheduler.py:433", "Writes colours back as day/time"],
        ["reassign_venues()", "scheduler.py:466", "Two-phase greedy venue allocation"],
        ["_pick_best_venue()", "scheduler.py:514", "Chooses the best free room"],
        ["greedy_colour_count()", "scheduler.py:637", "Greedy baseline for benchmarking"],
    ],
    widths=[1.85, 1.35, 2.85],
)

doc.add_heading("API endpoints", level=2)
table(
    ["Method + path", "Access", "Purpose"],
    [
        ["POST /auth/login", "Public", "Issue JWT"],
        ["GET /courses", "Any user", "List courses (filterable)"],
        ["PUT /generate", "Admin", "Create a draft timetable"],
        ["PUT /resolve", "Admin", "Run DSATUR + venue allocation"],
        ["GET /conflicts", "Any user", "Conflict IDs + detailed causes"],
        ["PATCH /courses/{id}", "Admin", "Manual edit"],
        ["GET /export-pdf", "Any user", "Download timetable PDF"],
        ["POST /complaints", "Client", "Raise a timetable complaint"],
        ["PATCH /complaints/{id}", "Admin", "Resolve or dismiss a complaint"],
    ],
    widths=[1.85, 0.9, 3.3],
)

doc.add_heading("Constants worth quoting", level=2)
table(
    ["Constant", "Value", "Where"],
    [
        ["Days", "Monday–Friday (5)", "seed.py:57"],
        ["Time slots", "8 per day, 08:00–17:00, 12:00–13:00 is a break", "seed.py:43"],
        ["Colours (day × slot)", "5 × 8 = 40", "scheduler.py:29"],
        ["FPAS venues", "18 rooms", "seed.py:61"],
        ["FSMS venues", "11 rooms", "seed.py:68"],
        ["Shared venues", "Auditorium, NH LAB, NW HORIZON LB", "scheduler.py:481"],
        ["Repair loop cap", "50 attempts", "timetable.py:568"],
        ["Venue phase caps", "5 (conflicts) / 3 (balancing)", "scheduler.py:565, 593"],
    ],
    widths=[1.7, 2.5, 1.85],
)

doc.add_heading("The three sentences to memorise", level=2)
for i, s in enumerate([
    "Clicking Resolve calls one endpoint that runs a two-stage pipeline: DSATUR "
    "graph colouring decides WHEN each class holds, then a separate greedy "
    "allocator decides WHERE.",
    "Venue was deliberately excluded from the conflict graph because a room clash "
    "does not require a different time slot — only a different room — so making it "
    "an edge would waste time slots.",
    "The two stages are connected by a one-way dependency: changing a time "
    "invalidates a room, but changing a room never invalidates a time — which is "
    "why venue reassignment runs as a repair step after every time change.",
], 1):
    p = doc.add_paragraph()
    r = p.add_run(f"{i}.  ")
    r.bold = True
    r.font.color.rgb = ACCENT
    r2 = p.add_run(s)
    r2.italic = True
    r2.font.size = Pt(10.5)
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.space_after = Pt(8)
    shade(p, "EAF3F0")

doc.save("docs/Project_Defence_QA.docx")
print("Saved docs/Project_Defence_QA.docx")
