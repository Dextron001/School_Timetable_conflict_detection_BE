import { useState, useEffect } from "react";
import { api } from "../api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SLOTS = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"];
const LEVELS = ["100", "200", "300", "400"];

export default function AddCourseModal({ faculty, onClose, onSave }) {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    course_code: "",
    name: "",
    lecturer_name: "",
    description: "",
    department: "",
    academic_level: "100",
    day_of_the_week: "Monday",
    time_start: "08:00",
    time_end: "09:00",
  });

  // Load departments for this faculty
  useEffect(() => {
    if (!faculty) return;
    api.faculties().then((faculties) => {
      const fac = faculties.find(f => f.code === faculty);
      if (fac) {
        setDepartments(fac.departments);
        // Auto-select first department
        if (fac.departments.length > 0 && !form.department) {
          setForm((f) => ({ ...f, department: fac.departments[0].code }));
        }
      }
    }).catch(() => setDepartments([]));
  }, [faculty]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.course_code || !form.name || !form.lecturer_name || !form.department) {
      return;
    }
    onSave({
      ...form,
      department: form.department,
    });
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div className="card w-full max-w-lg p-6 space-y-5">
        <div>
          <h3 className="text-lg font-bold">Add Course</h3>
          <p className="text-sm text-muted">
            Adding to {faculty} — pick a department within this faculty
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Department *</label>
            <select className="input" value={form.department} onChange={(e) => set("department", e.target.value)} required>
              <option value="">Select department</option>
              {departments.map((d) => (
                <option key={d.code} value={d.code}>{d.name} ({d.code})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Level</label>
            <select className="input" value={form.academic_level} onChange={(e) => set("academic_level", e.target.value)}>
              {LEVELS.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label">Course code *</label>
            <input className="input" placeholder="e.g. CSC301" value={form.course_code} onChange={(e) => set("course_code", e.target.value)} required />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Course name *</label>
            <input className="input" placeholder="e.g. Database Management" value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div>
            <label className="label">Lecturer *</label>
            <input className="input" placeholder="e.g. Dr. Smith" value={form.lecturer_name} onChange={(e) => set("lecturer_name", e.target.value)} required />
          </div>
          <div>
            <label className="label">Venue</label>
            <input className="input" placeholder="e.g. FPAS CSC LH" value={form.description} onChange={(e) => set("description", e.target.value)} />
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
          <div className="sm:col-span-2 flex justify-end gap-3 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary">Add course</button>
          </div>
        </form>
      </div>
    </div>
  );
}