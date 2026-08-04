import { useEffect, useState } from "react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SLOTS = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"];
const UNIT_OPTIONS = [1, 2, 3];
const SESSION_OPTIONS = ["A", "B"];

export default function EditCourseModal({ course, onClose, onSave }) {
  const [form, setForm] = useState(null);

  useEffect(() => {
    if (course) {
      setForm({
        name: course.name,
        description: course.description || "",
        lecturer_name: course.lecturer_name,
        day_of_the_week: course.day_of_the_week,
        time_start: course.time_start,
        time_end: course.time_end,
        units: course.units || 1,
        session: course.session || "A",
      });
    }
  }, [course]);

  if (!course || !form) return null;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const unitLabel = (u) => {
    if (u === 3) return "3 units (2hrs + 1hr per week)";
    if (u === 2) return "2 units (2hr block per week)";
    return "1 unit (1hr per week)";
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div className="card w-full max-w-lg p-6 space-y-5">
        <div>
          <h3 className="text-lg font-bold">Edit Course</h3>
          <p className="text-sm text-muted">
            {course.course_code} · {course.department} {course.academic_level}L
            <span className="ml-2 text-brand font-semibold">
              ({course.units || 1} unit{course.units > 1 ? "s" : ""}, Session {course.session || "A"})
            </span>
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="label">Course name</label>
            <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div>
            <label className="label">Venue</label>
            <input className="input" value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
          <div>
            <label className="label">Lecturer</label>
            <input className="input" value={form.lecturer_name} onChange={(e) => set("lecturer_name", e.target.value)} />
          </div>
          <div>
            <label className="label">Units (credit hours)</label>
            <select className="input" value={form.units} onChange={(e) => set("units", Number(e.target.value))}>
              {UNIT_OPTIONS.map((u) => (<option key={u} value={u}>{unitLabel(u)}</option>))}
            </select>
          </div>
          <div>
            <label className="label">Session</label>
            <select className="input" value={form.session} onChange={(e) => set("session", e.target.value)}>
              {SESSION_OPTIONS.map((s) => (
                <option key={s} value={s}>{s === "A" ? "A — Main session" : "B — Additional session (3-unit only)"}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Day</label>
            <select className="input" value={form.day_of_the_week} onChange={(e) => set("day_of_the_week", e.target.value)}>
              {DAYS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Start</label>
              <select className="input" value={form.time_start} onChange={(e) => set("time_start", e.target.value)}>
                {SLOTS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="label">End</label>
              <select className="input" value={form.time_end} onChange={(e) => set("time_end", e.target.value)}>
                {SLOTS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={() => onSave(course.id, { ...form, units: Number(form.units) })}>Save changes</button>
        </div>
      </div>
    </div>
  );
}