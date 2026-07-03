import { useState } from "react";
import { api } from "../api";
import DashboardHeader from "../components/DashboardHeader";
import ScopeSelector from "../components/ScopeSelector";
import TimetableTable from "../components/TimetableTable";
import { useToast } from "../context/ToastContext";

export default function ClientDashboard() {
  const toast = useToast();
  const [dept, setDept] = useState("");
  const [level, setLevel] = useState("");
  const [courses, setCourses] = useState([]);
  const [conflictIds, setConflictIds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const scoped = dept && level;

  async function handleView() {
    if (!scoped) return toast.error("Select department and level first.");
    setBusy(true);
    try {
      const [data, conf] = await Promise.all([
        api.courses(dept, level),
        api.conflicts(dept, level),
      ]);
      setCourses(data);
      setConflictIds(conf.conflict_ids);
      setLoaded(true);
      if (!data.length) toast.info("No courses published for this scope yet.");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
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
      <DashboardHeader title="Student Portal" subtitle="View your timetable" />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-6 space-y-5">
          <div>
            <h2 className="text-xl font-bold">My Timetable</h2>
            <p className="text-sm text-muted">
              Choose your department and level to view the published schedule.
            </p>
          </div>

          <ScopeSelector
            dept={dept}
            level={level}
            onChange={({ dept: d, level: l }) => {
              setDept(d);
              setLevel(l);
              setLoaded(false);
            }}
          />

          <div className="flex flex-wrap gap-3 pt-1">
            <button className="btn-primary" disabled={!scoped || busy} onClick={handleView}>
              {busy ? "Loading…" : "View timetable"}
            </button>
            <button className="btn-ghost" disabled={!courses.length} onClick={handleDownload}>
              ⬇ Download PDF
            </button>
          </div>
        </div>

        {loaded && (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-muted">
                {dept} · {level} Level
              </h3>
              {conflictIds.length > 0 && (
                <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200">
                  Provisional — pending review
                </span>
              )}
            </div>
            <TimetableTable courses={courses} conflictIds={conflictIds} />
          </div>
        )}
      </main>
    </div>
  );
}
