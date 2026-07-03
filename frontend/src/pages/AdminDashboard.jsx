import { useState } from "react";
import { api } from "../api";
import DashboardHeader from "../components/DashboardHeader";
import ScopeSelector from "../components/ScopeSelector";
import TimetableTable from "../components/TimetableTable";
import EditCourseModal from "../components/EditCourseModal";
import AddCourseModal from "../components/AddCourseModal";
import { useToast } from "../context/ToastContext";

export default function AdminDashboard() {
  const toast = useToast();
  const [dept, setDept] = useState("");
  const [level, setLevel] = useState("");
  const [courses, setCourses] = useState([]);
  const [conflictIds, setConflictIds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);
  const [adding, setAdding] = useState(false);
  const [report, setReport] = useState(null);

  const scoped = dept && level;

  async function refresh() {
    const [data, conf] = await Promise.all([
      api.courses(dept, level),
      api.conflicts(dept, level),
    ]);
    setCourses(data);
    setConflictIds(conf.conflict_ids);
    return conf.conflict_ids;
  }

  async function handleGenerate() {
    if (!scoped) return toast.error("Select department and level first.");
    setBusy(true);
    try {
      setReport(null);
      await api.generate(dept, level);
      const ids = await refresh();
      toast.success(
        ids.length
          ? `Timetable generated — ${ids.length} clashing slot(s) detected.`
          : "Timetable generated — no conflicts."
      );
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleResolve() {
    if (!courses.length) return toast.error("Generate a timetable first.");
    setBusy(true);
    try {
      const res = await api.resolve(dept, level);
      setReport(res.report);
      const ids = await refresh();
      toast.success(
        ids.length
          ? "Some conflicts could not be auto-resolved (timetable too small)."
          : `Solved with ${res.report.algorithm} ✔`
      );
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEdit(id, payload) {
    try {
      await api.updateCourse(id, payload);
      setEditing(null);
      await refresh();
      toast.success("Course updated.");
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleAddCourse(payload) {
    try {
      await api.createCourse(payload);
      setAdding(false);
      await refresh();
      toast.success("Course added.");
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleDeleteCourse(course) {
    if (!confirm(`Delete "${course.course_code} — ${course.name}"?`)) return;
    try {
      await api.deleteCourse(course.id);
      await refresh();
      toast.success("Course deleted.");
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleDownload() {
    try {
      const res = await api.exportPdf(dept, level);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dept}_${level}_Timetable.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded.");
    } catch (e) {
      toast.error(e.message);
    }
  }

  return (
    <div className="min-h-full">
      <DashboardHeader title="Admin Console" subtitle="Manage timetables" />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-6 space-y-5">
          <div>
            <h2 className="text-xl font-bold">Generate &amp; Resolve</h2>
            <p className="text-sm text-muted">
              Pick a scope, generate a draft, then auto-resolve any clashes.
            </p>
          </div>

          <ScopeSelector
            dept={dept}
            level={level}
            onChange={({ dept: d, level: l }) => {
              setDept(d);
              setLevel(l);
            }}
          />

          <div className="flex flex-wrap gap-3 pt-1">
            <button className="btn-primary" disabled={!scoped || busy} onClick={handleGenerate}>
              {busy ? "Working…" : "Generate timetable"}
            </button>
            <button
              className="btn-ghost"
              disabled={!courses.length || busy}
              onClick={handleResolve}
            >
              Resolve conflicts
            </button>
            <button
              className="btn-ghost"
              disabled={!courses.length}
              onClick={handleDownload}
            >
              ⬇ Download PDF
            </button>
            <button
              className="btn-ghost"
              disabled={!scoped}
              onClick={() => setAdding(true)}
            >
              + Add course
            </button>
          </div>
        </div>

        {report && (
          <div className="card p-5 border-l-4 border-brand space-y-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-brand mb-2">
                Algorithm report
              </p>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                <span><span className="text-muted">Method:</span> <b>{report.algorithm}</b></span>
                <span><span className="text-muted">Courses (nodes):</span> <b>{report.nodes}</b></span>
                <span><span className="text-muted">Conflicts (edges):</span> <b>{report.edges}</b></span>
                <span><span className="text-muted">Slots used (colours):</span> <b>{report.colours_used}</b> / {report.slots_available}</span>
                <span><span className="text-muted">Soft-constraint penalty:</span> <b>{report.soft_penalty}</b></span>
              </div>
            </div>

            {report.comparison && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted mb-2">
                  DSATUR vs. naive Greedy (same input)
                </p>
                <div className="overflow-x-auto">
                  <table className="text-sm border border-line rounded-lg">
                    <thead>
                      <tr className="text-[11px] uppercase tracking-wide text-muted bg-surface">
                        <th className="px-4 py-2 text-left font-semibold">Metric</th>
                        <th className="px-4 py-2 text-left font-semibold">DSATUR</th>
                        <th className="px-4 py-2 text-left font-semibold">Greedy</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-line">
                        <td className="px-4 py-2">Slots used (fewer is better)</td>
                        <td className="px-4 py-2 font-semibold text-brand">{report.comparison.dsatur_slots}</td>
                        <td className="px-4 py-2">{report.comparison.greedy_slots}</td>
                      </tr>
                      <tr className="border-t border-line">
                        <td className="px-4 py-2">Soft penalty (lower is better)</td>
                        <td className="px-4 py-2 font-semibold text-brand">{report.comparison.dsatur_penalty}</td>
                        <td className="px-4 py-2">{report.comparison.greedy_penalty}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-muted mt-2">
                  DSATUR schedules the most-constrained course first, so it never
                  needs more slots than greedy and respects soft preferences better.
                </p>
              </div>
            )}
          </div>
        )}

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold uppercase tracking-wide text-muted">
              Timetable {scoped && `· ${dept} ${level}L`}
            </h3>
            {conflictIds.length > 0 && (
              <span className="badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200">
                {conflictIds.length} conflict slot(s)
              </span>
            )}
          </div>
          <TimetableTable
            courses={courses}
            conflictIds={conflictIds}
            editable
            onDelete={handleDeleteCourse}
            onEdit={setEditing}
          />
        </div>
      </main>

      {editing && (
        <EditCourseModal
          course={editing}
          onClose={() => setEditing(null)}
          onSave={handleSaveEdit}
        />
      )}

      {adding && (
        <AddCourseModal
          department={dept}
          academicLevel={level}
          onClose={() => setAdding(false)}
          onSave={handleAddCourse}
        />
      )}
    </div>
  );
}