// Renders timetable as a grid matching the institution pattern:
// rows = days (Mon-Fri), columns = time slots (8am-5pm), with a lunch break.
// Each course shows: course_code (dept level) · venue — compact.
// Conflicting courses are highlighted in red.
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

export default function TimetableTable({ courses, conflictIds = [], editable = false, onDelete, onEdit }) {
  if (!courses || courses.length === 0) {
    return (
      <div className="text-center py-16 text-muted">
        <p className="text-sm">No courses to display yet.</p>
      </div>
    );
  }

  const conflictSet = new Set(conflictIds);

  // Build a map: { day -> { start -> [courses] } }
  const grid = {};
  for (const day of DAYS) {
    grid[day] = {};
    for (const slot of TEACHING_SLOTS) {
      grid[day][slot.start] = [];
    }
  }

  for (const c of courses) {
    if (grid[c.day_of_the_week] && grid[c.day_of_the_week][c.time_start]) {
      grid[c.day_of_the_week][c.time_start].push(c);
    }
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
          {DAYS.map((day) => (
            <tr key={day} className="border-b border-line">
              <td className="px-3 py-2 font-bold text-xs uppercase tracking-wide border-r border-line bg-surface">
                {day.slice(0, 3)}
              </td>
              {SLOT_LABELS.map((slot, i) => {
                if (slot.label === "B R E A K") {
                  return (
                    <td key={i} className="px-3 py-2 border-r border-line bg-brand/5 text-center italic text-brand text-xs">
                      Break
                    </td>
                  );
                }

                const cellCourses = grid[day][slot.start] || [];
                const hasConflict = cellCourses.some(c => conflictSet.has(c.id));

                return (
                  <td
                    key={i}
                    className={`px-2 py-2 border-r border-line ${
                      hasConflict ? "bg-red-50 dark:bg-red-950/40" : ""
                    }`}
                  >
                    {cellCourses.map((c) => {
                      const clash = conflictSet.has(c.id);
                      const venue = c.description || "TBA";
                      return (
                        <div
                          key={c.id}
                          className={`mb-1 last:mb-0 rounded px-1.5 py-1 text-xs leading-tight ${
                            clash
                              ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                              : "bg-surface text-ink"
                          }`}
                        >
                          <span className="font-semibold">{c.course_code}</span>
                          <span className="text-muted"> ({c.department} {c.academic_level}L)</span>
                          <span className="text-muted"> · {venue}</span>
                          {clash && <span className="ml-1 text-red-500">⚠</span>}
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
          ))}
        </tbody>
      </table>
    </div>
  );
}