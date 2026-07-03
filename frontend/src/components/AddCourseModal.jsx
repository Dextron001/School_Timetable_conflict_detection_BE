import { useState } from "react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SLOTS = ["07:00", "08:30", "10:00", "11:30", "13:00", "14:30", "16:00"];

export default function AddCourseModal({ department, academicLevel, onClose, onSave }) {
  const [form, setForm] = useState({
    course_code: "",
    name: "",
    lecturer_name: "",
    description: "",
    day_of_the_week: "Monday",
    time_start: "08:30",
    time_end: "10:00",
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.course_code || !form.name || !form.lecturer_name) {
      return;
    }
    onSave({
      ...form,
      department,
      academic_level: academicLevel,
    });
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div className="card w-full max-w-lg p-6 space-y-5">
        <div>
          <h3 className="text-lg font-bold">Add Course</h3>
          <p className="text-sm text-muted">
            {department} · {academicLevel} Level
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="label">Course code *</label>
            <input
              className="input"
              placeholder="e.g. CSC301"
              value={form.course_code}
              onChange={(e) => set("course_code", e.target.value)}
              required
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Course name *</label>
            <input
              className="input"
              placeholder="e.g. Database Management"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Lecturer *</label>
            <input
              className="input"
              placeholder="e.g. Dr. Smith"
              value={form.lecturer_name}
              onChange={(e) => set("lecturer_name", e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">Venue</label>
            <input
              className="input"
              placeholder="e.g. Hall A"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </div>
          <div>
            <label className="label">Day</label>
            <select className="input" value={form.day_of_the_week} onChange={(e) => set("day_of_the_week", e.target.value)}>
              {DAYS.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Start</label>
              <select className="input" value={form.time_start} onChange={(e) => set("time_start", e.target.value)}>
                {SLOTS.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">End</label>
              <select className="input" value={form.time_end} onChange={(e) => set("time_end", e.target.value)}>
                {SLOTS.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="sm:col-span-2 flex justify-end gap-3 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Add course
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}