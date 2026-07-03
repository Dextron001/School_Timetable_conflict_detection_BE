// Renders courses grouped by weekday. Conflicting rows are highlighted in red.
// If `editable` is true (admin), shows Edit and Delete buttons per row.
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

function sortByTime(a, b) {
  return a.time_start.localeCompare(b.time_start);
}

export default function TimetableTable({ courses, conflictIds = [], editable = false, onEdit, onDelete }) {
  if (!courses || courses.length === 0) {
    return (
      <div className="text-center py-16 text-muted">
        <p className="text-sm">No courses to display yet.</p>
      </div>
    );
  }

  const conflictSet = new Set(conflictIds);
  const groups = DAYS.map((day) => ({
    day,
    items: courses.filter((c) => c.day_of_the_week === day).sort(sortByTime),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-8">
      {groups.map(({ day, items }) => (
        <div key={day}>
          <h4 className="text-xs font-bold uppercase tracking-widest text-muted border-b border-line pb-2 mb-3">
            {day}
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-muted">
                  <th className="py-2 pr-4 font-semibold">Time</th>
                  <th className="py-2 pr-4 font-semibold">Course</th>
                  <th className="py-2 pr-4 font-semibold">Venue</th>
                  <th className="py-2 pr-4 font-semibold">Lecturer</th>
                  {editable && <th className="py-2 pr-4 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {items.map((c) => {
                  const clash = conflictSet.has(c.id);
                  return (
                    <tr
                      key={c.id}
                      className={
                        clash
                          ? "border-b border-red-200 bg-red-50 text-red-700 dark:bg-red-950/40 dark:border-red-900 dark:text-red-300"
                          : "border-b border-line hover:bg-surface transition"
                      }
                    >
                      <td className="py-3 pr-4 font-mono text-[13px] whitespace-nowrap">
                        {c.time_start} – {c.time_end}
                        {clash && (
                          <span className="badge ml-2 bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200">
                            conflict
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        <span className="font-semibold">{c.course_code}</span>
                        <span className="text-muted"> · {c.name}</span>
                      </td>
                      <td className="py-3 pr-4">{c.description || "—"}</td>
                      <td className="py-3 pr-4">{c.lecturer_name}</td>
                      {editable && (
                        <td className="py-3 pr-4 text-right space-x-2">
                          <button
                            className="text-brand font-semibold text-xs hover:underline"
                            onClick={() => onEdit?.(c)}
                          >
                            Edit
                          </button>
                          <button
                            className="text-red-500 font-semibold text-xs hover:underline"
                            onClick={() => onDelete?.(c)}
                          >
                            Delete
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}