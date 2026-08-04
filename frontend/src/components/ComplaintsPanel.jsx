import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

export default function ComplaintsPanel() {
  const toast = useToast();
  const [complaints, setComplaints] = useState([]);
  const [filterFaculty, setFilterFaculty] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [sectionOpen, setSectionOpen] = useState(false);
  const [messages, setMessages] = useState({});
  const [replyTexts, setReplyTexts] = useState({});
  const [sending, setSending] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [openComplaints, setOpenComplaints] = useState({});
  const messagesEndRefs = useRef({});

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

  async function loadNotifications() {
    try {
      const data = await api.notifications();
      setNotifications(data);
    } catch {
      /* ignore */
    }
  }

  async function loadMessages(complaintId) {
    try {
      const data = await api.getMessages(complaintId);
      setMessages((prev) => ({ ...prev, [complaintId]: data }));
    } catch (err) {
      toast.error(err.message);
    }
  }

  useEffect(() => {
    loadComplaints();
    loadNotifications();
  }, [filterFaculty, filterStatus]);

  useEffect(() => {
    Object.keys(openComplaints).forEach((id) => {
      if (openComplaints[id] && !messages[id]) {
        loadMessages(id);
      }
    });
  }, [openComplaints]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadNotifications();
      Object.keys(openComplaints).forEach((id) => {
        if (openComplaints[id]) {
          loadMessages(id);
        }
      });
    }, 15000);
    return () => clearInterval(interval);
  }, [openComplaints]);

  function toggleComplaint(id) {
    setOpenComplaints((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      if (next[id] && !messages[id]) {
        loadMessages(id);
      }
      return next;
    });
  }

  async function handleResolve(id, status) {
    try {
      await api.resolveComplaint(id, { status, admin_note: null });
      toast.success(`Complaint ${status === "resolved" ? "resolved" : "dismissed"}.`);
      loadComplaints();
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function handleSendReply(complaintId) {
    const text = replyTexts[complaintId] || "";
    if (!text.trim()) return;
    setSending(complaintId);
    try {
      await api.sendMessage(complaintId, text.trim());
      setReplyTexts((prev) => ({ ...prev, [complaintId]: "" }));
      await loadMessages(complaintId);
      toast.success("Reply sent!");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSending(null);
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
  const totalUnread = notifications.reduce((sum, n) => sum + n.unread_count, 0);

  return (
    <div className="card p-6 space-y-4">
      <div className="w-full">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h2 className="text-xl font-bold">
                📢 Complaints
                {totalUnread > 0 && (
                  <span className="ml-2 badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 text-xs font-bold">
                    🔔 {totalUnread} new message{totalUnread > 1 ? "s" : ""}
                  </span>
                )}
              </h2>
              <p className="text-sm text-muted">
                Review and resolve timetable complaints from students.
              </p>
            </div>
          </div>
          {pendingCount > 0 && (
            <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 text-sm font-bold">
              {pendingCount} pending
            </span>
          )}
        </div>
        <button
          className="w-full flex flex-col items-center mt-3 group"
          onClick={() => setSectionOpen(!sectionOpen)}
        >
          <svg
            className={`w-5 h-5 text-gray-400 dark:text-gray-500 transition-transform duration-300 group-hover:text-gray-600 dark:group-hover:text-gray-300 ${
              sectionOpen ? "rotate-180" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
          <span className="text-[11px] text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 font-semibold uppercase tracking-wide mt-0.5">
            {sectionOpen ? "Collapse" : "Expand"}
          </span>
        </button>
      </div>

      {sectionOpen && (
        <>
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
            <button className="btn-ghost text-xs" onClick={() => { loadComplaints(); loadNotifications(); }}>
              🔄 Refresh
            </button>
          </div>

          {busy && complaints.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">Loading complaints…</p>
          ) : complaints.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">No complaints found.</p>
          ) : (
            <div className="space-y-3">
              {complaints.map((c) => {
                const isOpen = openComplaints[c.id];
                return (
                  <div
                    key={c.id}
                    className="border border-line rounded-lg overflow-hidden"
                  >
                    <div
                      className="p-4 space-y-2 bg-surface/30 cursor-pointer hover:bg-surface/60 transition-colors"
                      onClick={() => toggleComplaint(c.id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          {statusBadge(c.status)}
                          <span className="font-semibold truncate">{c.subject}</span>
                          {c.unread_count > 0 && (
                            <span className="badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 text-xs font-bold">
                              {c.unread_count} new
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted shrink-0">
                          <span>{c.faculty}</span>
                          {c.course_code && <span>· {c.course_code}</span>}
                          <span>· {c.created_at}</span>
                        </div>
                      </div>
                      <div className="text-xs text-muted flex items-center gap-2">
                        <span>By <b>{c.full_name || c.username || `User #${c.user_id}`}</b></span>
                        <button
                          className="px-2 py-0.5 text-[11px] font-semibold rounded border border-line bg-surface hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          onClick={(e) => { e.stopPropagation(); toggleComplaint(c.id); }}
                        >
                          {isOpen ? "Close" : "Open"}
                        </button>
                      </div>
                    </div>

                    {isOpen && (
                      <div className="border-t border-line p-4 space-y-3">
                        <div className="bg-surface rounded p-3 max-h-[300px] overflow-y-auto space-y-2">
                          <div className="flex justify-start">
                            <div className="max-w-[80%]">
                              <p className="text-[10px] text-muted mb-0.5">
                                {c.full_name || c.username || "Student"} · {c.created_at}
                              </p>
                              <div className="bg-gray-100 rounded-lg rounded-tl-none p-2 text-sm border border-line">
                                {c.message}
                              </div>
                            </div>
                          </div>

                          {(messages[c.id] || []).map((msg) => (
                            <div
                              key={msg.id}
                              className={`flex ${msg.sender_role === "admin" ? "justify-end" : "justify-start"}`}
                            >
                              <div className="max-w-[80%]">
                                <p className={`text-[10px] text-muted mb-0.5 ${msg.sender_role === "admin" ? "text-right" : ""}`}>
                                  {msg.sender_name} · {msg.created_at}
                                </p>
                                <div
                                  className={`rounded-lg p-2 text-sm ${
                                    msg.sender_role === "admin"
                                      ? "bg-brand/10 dark:bg-brand/20 rounded-tr-none border border-brand/20"
                                      : "bg-gray-100 rounded-tl-none border border-line"
                                  }`}
                                >
                                  {msg.message}
                                </div>
                              </div>
                            </div>
                          ))}

                          <div ref={(el) => { messagesEndRefs.current[c.id] = el; }} />
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

                        <div className="space-y-2 pt-2">
                          <textarea
                            value={replyTexts[c.id] || ""}
                            onChange={(e) =>
                              setReplyTexts((prev) => ({ ...prev, [c.id]: e.target.value }))
                            }
                            placeholder="Type a reply to the student…"
                            className="input-field min-h-[60px] text-sm"
                          />
                          <div className="flex items-center justify-between">
                            <button
                              className="btn-primary text-sm"
                              disabled={!(replyTexts[c.id] || "").trim() || sending === c.id}
                              onClick={() => handleSendReply(c.id)}
                            >
                              {sending === c.id ? "Sending…" : "➤ Send"}
                            </button>
                            {c.status === "pending" && (
                              <div className="flex gap-2">
                                <button
                                  className="btn-ghost text-sm text-green-700 dark:text-green-400"
                                  onClick={() => handleResolve(c.id, "resolved")}
                                >
                                  ✓ Resolve
                                </button>
                                <button
                                  className="btn-ghost text-sm text-red-600 dark:text-red-400"
                                  onClick={() => handleResolve(c.id, "dismissed")}
                                >
                                  ✕ Dismiss
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}