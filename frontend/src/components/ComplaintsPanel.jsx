import { useState, useEffect } from "react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

export default function ComplaintsPanel() {
  const toast = useToast();
  const [complaints, setComplaints] = useState([]);
  const [filterFaculty, setFilterFaculty] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(null); // id of expanded complaint
  const [noteText, setNoteText] = useState("");

  async function loadComplaints() {
    setBusy(true);
    try {
      const data = await api.complaints(filterFaculty, filterStatus);
      setComplaints(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadComplaints();
  }, [filterFaculty, filterStatus]);

  async function handleResolve(id, status, note) {
    try {
      await api.resolveComplaint(id, { status, admin_note: note.trim() || null });
      toast.success(`Complaint ${status === "resolved" ? "resolved" : "dismissed"}.`);
      setExpanded(null);
      setNoteText("");
      loadComplaints();
    } catch (err) {
      toast.error(err.message);
    }
  }

  const statusBadge = (s) => {
    if (s === "pending")
      return <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200">Pending</span>;
    if (s === "resolved")
      return <span className="badge bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200">Resolved</span>;
    if (s === "dismissed")
      return <span className="badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200">Dismissed</span>;
    return <span className="badge bg-surface text-muted">{s}</span>;
  };

  const pendingCount = complaints.filter((c) => c.status === "pending").length;

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">📢 Complaints</h2>
          <p className="text-sm text-muted">
            Review and resolve timetable complaints from students.
          </p>
        </div>
        {pendingCount > 0 && (
          <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 text-sm font-bold">
            {pendingCount} pending
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={filterFaculty}
          onChange={(e) => setFilterFaculty(e.target.value)}
          className="input-field w-auto"
        >
          <option value="">All faculties</option>
          <option value="FPAS">FPAS</option>
          <option value="FSMS">FSMS</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="input-field w-auto"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <button className="btn-ghost text-xs" onClick={loadComplaints}>
          🔄 Refresh
        </button>
      </div>

      {/* Complaints list */}
      {busy && complaints.length === 0 ? (
        <p className="text-sm text-muted text-center py-4">Loading complaints…</p>
      ) : complaints.length === 0 ? (
        <p className="text-sm text-muted text-center py-4">No complaints found.</p>
      ) : (
        <div className="space-y-3">
          {complaints.map((c) => (
            <div
              key={c.id}
              className="border border-line rounded-lg p-4 space-y-2 cursor-pointer hover:border-brand transition-colors"
              onClick={() => {
                setExpanded(expanded === c.id ? null : c.id);
                setNoteText("");
              }}
            >
              {/* Summary row */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  {statusBadge(c.status)}
                  <span className="font-semibold truncate">{c.subject}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted shrink-0">
                  <span>{c.faculty}</span>
                  {c.course_code && <span>· {c.course_code}</span>}
                  <span>· {c.created_at}</span>
                </div>
              </div>

              <div className="text-xs text-muted">
                By <b>{c.full_name || c.username || `User #${c.user_id}`}</b>
              </div>

              {/* Expanded detail */}
              {expanded === c.id && (
                <div className="space-y-3 pt-2 border-t border-line">
                  <div>
                    <p className="text-xs font-semibold mb-1">Complaint message:</p>
                    <p className="text-sm bg-surface rounded p-3">{c.message}</p>
                  </div>

                  {c.admin_note && (
                    <div>
                      <p className="text-xs font-semibold mb-1">Admin note:</p>
                      <p className="text-sm bg-surface rounded p-3">{c.admin_note}</p>
                    </div>
                  )}

                  {c.resolved_at && (
                    <p className="text-xs text-muted">
                      {c.status === "resolved" ? "Resolved" : "Dismissed"} by
                      <b> {c.resolved_by || "Admin"}</b> on {c.resolved_at}
                    </p>
                  )}

                  {c.status === "pending" && (
                    <div className="space-y-2 pt-2">
                      <textarea
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Write a note/reply to the student (optional)…"
                        className="input-field min-h-[60px] text-sm"
                      />
                      <div className="flex gap-2">
                        <button
                          className="btn-primary text-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolve(c.id, "resolved", noteText);
                          }}
                        >
                          ✓ Resolve
                        </button>
                        <button
                          className="btn-ghost text-sm text-red-600 dark:text-red-400"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleResolve(c.id, "dismissed", noteText);
                          }}
                        >
                          ✕ Dismiss
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}