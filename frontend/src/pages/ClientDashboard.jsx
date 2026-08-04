import { useState } from "react";
import { api } from "../api";
import DashboardHeader from "../components/DashboardHeader";
import ScopeSelector from "../components/ScopeSelector";
import TimetableTable from "../components/TimetableTable";
import PDFPreviewModal from "../components/PDFPreviewModal";
import ComplaintModal from "../components/ComplaintModal";
import MyComplaints from "../components/MyComplaints";
import { useToast } from "../context/ToastContext";

export default function ClientDashboard() {
  const toast = useToast();
  const [faculty, setFaculty] = useState("");
  const [courses, setCourses] = useState([]);
  const [conflictIds, setConflictIds] = useState([]);
  const [conflictDetails, setConflictDetails] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [complaining, setComplaining] = useState(false);
  const [refreshMyComplaints, setRefreshMyComplaints] = useState(0);

  async function handleView() {
    if (!faculty) return toast.error("Select a faculty first.");
    setBusy(true);
    try {
      const [data, conf] = await Promise.all([api.courses(faculty), api.conflicts(faculty)]);
      setCourses(data);
      setConflictIds(conf.conflict_ids);
      setConflictDetails(conf.conflicts || []);
      setLoaded(true);
      if (!data.length) toast.info("No courses published for this faculty yet.");
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  }

  async function handleDownload() {
    try {
      const res = await api.exportPdf(faculty);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${faculty}_Combined_Timetable.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded.");
    } catch (e) { toast.error(e.message); }
  }

  return (
    <div className="min-h-full">
      <DashboardHeader title="Student Portal" subtitle="View your timetable" />
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div className="card p-6 space-y-5">
          <div>
            <h2 className="text-xl font-bold">My Timetable</h2>
            <p className="text-sm text-muted">Choose your faculty to view the combined timetable for all departments and all levels (100–400). Preview or download the PDF.</p>
          </div>
          <ScopeSelector faculty={faculty} onChange={(f) => { setFaculty(f); setLoaded(false); }} />
          <div className="flex flex-wrap gap-3 pt-1">
            <button className="btn-primary" disabled={!faculty || busy} onClick={handleView}>{busy ? "Loading…" : "View timetable"}</button>
            <button className="btn-ghost" disabled={!courses.length} onClick={() => setPreviewing(true)}>👁 Preview PDF</button>
            <button className="btn-ghost" disabled={!courses.length} onClick={handleDownload}>⬇ Download PDF</button>
            <button className="btn-ghost" disabled={!faculty} onClick={() => setComplaining(true)}>📢 Report issue</button>
          </div>
        </div>

        {loaded && (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-muted">{faculty} · All Departments · All Levels</h3>
              {conflictIds.length > 0 && (<span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200">Provisional — pending review</span>)}
            </div>
            <TimetableTable courses={courses} conflictIds={conflictIds} conflictDetails={conflictDetails} />
          </div>
        )}

        <MyComplaints key={refreshMyComplaints} />
      </main>

      {previewing && <PDFPreviewModal faculty={faculty} onClose={() => setPreviewing(false)} onDownloaded={() => { setPreviewing(false); toast.success("PDF downloaded."); }} />}
      {complaining && <ComplaintModal faculty={faculty} onClose={() => setComplaining(false)} onSubmitted={() => setRefreshMyComplaints((n) => n + 1)} />}
    </div>
  );
}