// Renders timetable as a grid matching the institution pattern:
// rows = days (Mon-Fri), columns = time slots (8am-5pm), with a lunch break.
// Multi-hour courses (2hr) MERGE across 2 adjacent columns using colspan.
// When 1hr and 2hr courses share a time block, the day gets two sub-rows:
//   - Top sub-row: 2hr courses with merged cells
//   - Bottom sub-row: 1hr courses with individual cells
import { useMemo } from "react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

const SLOT_LABELS = [
  { start: "08:00", end: "09:00", label: "8 – 9am" },
  { start: "09:00", end: "10:00", label: "9 – 10am" },
  { start: "10:00", end: "11:00", label: "10 – 11am" },
  { start: "11:00", end: "12:00", label: "11 – 12noon" },
  { start: "12:00", end: "13:00", label: "B R E A K" },
  { start: "13:00", end: "14:00", label: "1 – 2pm" },
  { start: "14:00", end: "15:00", label: "2 – 3pm" },
  { start: "15:00", end: "16:00", label: "3 – 4pm" },
  { start: "16:00", end: "17:00", label: "4 – 5pm" },
];

const TEACHING_SLOTS = SLOT_LABELS.filter(s => s.label !== "B R E A K");

const CAUSE_LABELS = {
  cohort: "Same student group",
  lecturer: "Same lecturer",
  venue: "Same venue/room",
};

export default function TimetableTable({ courses, conflictIds = [], conflictDetails = [], editable = false, onDelete, onEdit }) {
  if (!courses || courses.length === 0) {
    return (
      <div className="text-center py-16 text-muted">
        <p className="text-sm">No courses to display yet.</p>
      </div>
    );
  }

  const conflictSet = new Set(conflictIds);

  const causeMap = useMemo(() => {
    const map = {};
    for (const d of conflictDetails) {
      if (!map[d.course_id_1]) map[d.course_id_1] = [];
      if (!map[d.course_id_2]) map[d.course_id_2] = [];
      const label = `${CAUSE_LABELS[d.cause] || d.cause}: ${d.detail}`;
      if (!map[d.course_id_1].includes(label)) map[d.course_id_1].push(label);
      if (!map[d.course_id_2].includes(label)) map[d.course_id_2].push(label);
    }
    return map;
  }, [conflictDetails]);

  // Build grid: each course goes into its START slot only.
  const grid = {};
  for (const day of DAYS) {
    grid[day] = {};
    for (const slot of TEACHING_SLOTS) {
      grid[day][slot.start] = [];
    }
  }

  for (const c of courses) {
    const daySlots = grid[c.day_of_the_week];
    if (!daySlots) continue;
    if (daySlots[c.time_start]) {
      const already = daySlots[c.time_start].some(
        existing => existing.course_code === c.course_code
      );
      if (!already) {
        daySlots[c.time_start].push(c);
      }
    }
  }

  // Check if a day needs two sub-rows (mixed 1hr + 2hr courses)
  function dayNeedsSplit(day) {
    for (const slot of TEACHING_SLOTS) {
      const coursesAtSlot = grid[day][slot.start] || [];
      const durs = new Set(coursesAtSlot.map(c =>
        parseInt(c.time_end.split(":")[0]) - parseInt(c.time_start.split(":")[0])
      ));
      if (durs.size > 1) return true;
    }
    return false;
  }

  // Build row cells for a sub-row of a day
  function buildDayCells(day, subRow) {
    const needsSplit = dayNeedsSplit(day);
    const cells = [];
    const consumedIndices = new Set();

    for (let si = 0; si < SLOT_LABELS.length; si++) {
      if (consumedIndices.has(si)) continue;

      const slot = SLOT_LABELS[si];

      if (slot.label === "B R E A K") {
        cells.push({ key: si, colspan: 1, isBreak: true, courses: [], hasConflict: false });
        continue;
      }

      const allCourses = grid[day][slot.start] ? [...grid[day][slot.start]] : [];

      let myCourses;
      if (needsSplit) {
        if (subRow === 0) {
          myCourses = allCourses.filter(c => {
            const hours = parseInt(c.time_end.split(":")[0]) - parseInt(c.time_start.split(":")[0]);
            return hours >= 2;
          });
        } else {
          myCourses = allCourses.filter(c => {
            const hours = parseInt(c.time_end.split(":")[0]) - parseInt(c.time_start.split(":")[0]);
            return hours === 1;
          });
        }
      } else {
        myCourses = allCourses;
      }

      let colspan = 1;
      if (subRow === 0 || !needsSplit) {
        for (const c of myCourses) {
          const hours = parseInt(c.time_end.split(":")[0]) - parseInt(c.time_start.split(":")[0]);
          if (hours > colspan) colspan = hours;
        }
      }

      if (colspan > 1) {
        for (let h = 1; h < colspan; h++) {
          let nextSi = si + h;
          while (nextSi < SLOT_LABELS.length && SLOT_LABELS[nextSi].label === "B R E A K") {
            nextSi++;
          }
          if (nextSi < SLOT_LABELS.length && !consumedIndices.has(nextSi)) {
            consumedIndices.add(nextSi);
          }
        }
      }

      const hasConflict = myCourses.some(c => conflictSet.has(c.id));

      cells.push({
        key: si,
        colspan,
        isBreak: false,
        courses: myCourses,
        hasConflict,
      });
    }

    return cells;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm border border-line rounded-lg">
        <thead>
          <tr className="text-[11px] uppercase tracking-wide text-muted bg-surface">
            <th className="px-3 py-2 font-semibold border-b border-line border-r border-line w-24">DAY / Time</th>
            {SLOT_LABELS.map((s, i) => (
              <th
                key={i}
                className={`px-3 py-2 font-semibold border-b border-line border-r border-line text-center ${
                  s.label === "B R E A K" ? "bg-brand/10 text-brand italic" : ""
                }`}
              >
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DAYS.map((day) => {
            const needsSplit = dayNeedsSplit(day);
            const numSubRows = needsSplit ? 2 : 1;

            const subRows = [];
            for (let sr = 0; sr < numSubRows; sr++) {
              subRows.push(buildDayCells(day, sr));
            }

            return subRows.map((cells, sr) => (
              <tr key={`${day}-${sr}`} className="border-b border-line">
                {sr === 0 ? (
                  <td
                    rowSpan={numSubRows}
                    className="px-3 py-2 font-bold text-xs uppercase tracking-wide border-r border-line bg-surface align-middle"
                  >
                    {day.slice(0, 3)}
                  </td>
                ) : null}
                {cells.map((cell) => {
                  if (cell.isBreak) {
                    return (
                      <td key={cell.key} className="px-3 py-2 border-r border-line bg-brand/5 text-center italic text-brand text-xs">
                        Break
                      </td>
                    );
                  }

                  return (
                    <td
                      key={cell.key}
                      colSpan={cell.colspan}
                      className={`px-2 py-2 border-r border-line ${
                        cell.hasConflict ? "bg-red-50 dark:bg-red-950/40" : ""
                      }`}
                    >
                      {cell.courses.map((c) => {
                        const clash = conflictSet.has(c.id);
                        const causes = causeMap[c.id] || [];
                        const venue = c.description || "TBA";
                        const hours = parseInt(c.time_end.split(":")[0]) - parseInt(c.time_start.split(":")[0]);
                        const is2hr = hours > 1;

                        return (
                          <div
                            key={c.id}
                            className={`mb-1 last:mb-0 rounded px-1.5 py-1 text-xs leading-tight ${
                              clash
                                ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                                : is2hr
                                ? "bg-surface text-ink border-l-2 border-gray-400"
                                : "bg-surface text-ink"
                            }`}
                            title={clash && causes.length ? `Conflict: ${causes.join("; ")}` : ""}
                          >
                            <span className="font-semibold">{c.course_code}</span>
                            <span className="text-muted"> ({c.department} {c.academic_level}L)</span>
                            <span className="text-muted"> · {venue}</span>
                            {clash && <span className="ml-1 text-red-500">⚠</span>}
                            {clash && causes.length > 0 && (
                              <span className="ml-1 text-[10px] text-red-400 italic">
                                {causes.join("; ")}
                              </span>
                            )}
                            {editable && (
                              <span className="ml-1 flex gap-0.5">
                                <button className="text-brand font-semibold hover:underline text-[10px]" onClick={() => onEdit?.(c)}>Ed</button>
                                <button className="text-red-500 font-semibold hover:underline text-[10px]" onClick={() => onDelete?.(c)}>✕</button>
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </td>
                  );
                })}
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}