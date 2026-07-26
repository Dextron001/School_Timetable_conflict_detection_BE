import { useState, useEffect } from "react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

export default function MyComplaints() {
  const toast = useToast();
  const [complaints, setComplaints] = useState([]);
  const [busy, setBusy] = useState(false);

  async function loadMyComplaints() {
    setBusy(true);
    try {
      const data = await api.myComplaints();
      setComplaints(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadMyComplaints();
  }, []);

  const statusBadge = (s) => {
    if (s === "pending")
      return <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200">Pending</span>;
    if (s === "resolved")
      return <span className="badge bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200">Resolved ✔</span>;
    if (s === "dismissed")
      return <span className="badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200">Dismissed</span>;
    return <span className="badge bg-surface text-muted">{s}</span>;
  };

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">📋 My Complaints</h2>
          <p className="text-sm text-muted">
            Track the status of your submitted complaints.
          </p>
        </div>
        <button className="btn-ghost text-xs" onClick={loadMyComplaints}>
          🔄 Refresh
        </button>
      </div>

      {busy && complaints.length === 0 ? (
        <p className="text-sm text-muted text-center py-4">Loading…</p>
      ) : complaints.length === 0 ? (
        <p className="text-sm text-muted text-center py-4">
          You haven't submitted any complaints yet.
        </p>
      ) : (
        <div className="space-y-3">
          {complaints.map((c) => (
            <div key={c.id} className="border border-line rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  {statusBadge(c.status)}
                  <span className="font-semibold truncate">{c.subject}</span>
                </div>
                <span className="text-xs text-muted shrink-0">{c.created_at}</span>
              </div>

              <div className="text-xs text-muted flex gap-2">
                <span>{c.faculty}</span>
                {c.course_code && <span>· {c.course_code}</span>}
              </div>

              <p className="text-sm bg-surface rounded p-2">{c.message}</p>

              {c.admin_note && (
                <div className="border-l-2 border-brand pl-3">
                  <p className="text-xs font-semibold text-brand">Admin reply:</p>
                  <p className="text-sm">{c.admin_note}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}