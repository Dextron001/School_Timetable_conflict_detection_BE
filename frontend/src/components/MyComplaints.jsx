import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

export default function MyComplaints() {
  const toast = useToast();
  const [complaints, setComplaints] = useState([]);
  const [busy, setBusy] = useState(false);
  const [sectionOpen, setSectionOpen] = useState(false);
  const [messages, setMessages] = useState({});
  const [replyTexts, setReplyTexts] = useState({});
  const [activeReply, setActiveReply] = useState(null);
  const [sending, setSending] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const messagesEndRefs = useRef({});

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
    loadMyComplaints();
    loadNotifications();
  }, []);

  // Load messages for all complaints when section opens
  useEffect(() => {
    if (sectionOpen) {
      complaints.forEach((c) => {
        if (!messages[c.id]) {
          loadMessages(c.id);
        }
      });
    }
  }, [sectionOpen, complaints]);

  // Auto-poll for new messages every 15 seconds when section is open
  useEffect(() => {
    if (!sectionOpen) return;
    const interval = setInterval(() => {
      loadNotifications();
      complaints.forEach((c) => {
        loadMessages(c.id);
      });
    }, 15000);
    return () => clearInterval(interval);
  }, [sectionOpen, complaints]);

  async function handleSendReply(complaintId) {
    const text = replyTexts[complaintId] || "";
    if (!text.trim()) return;
    setSending(complaintId);
    try {
      await api.sendMessage(complaintId, text.trim());
      setReplyTexts((prev) => ({ ...prev, [complaintId]: "" }));
      setActiveReply(null);
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
      return <span className="badge bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200">Resolved ✔</span>;
    if (s === "dismissed")
      return <span className="badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200">Dismissed</span>;
    return <span className="badge bg-surface text-muted">{s}</span>;
  };

  const pendingCount = complaints.filter((c) => c.status === "pending").length;
  const totalUnread = notifications.reduce((sum, n) => sum + n.unread_count, 0);

  return (
    <div className="card p-6 space-y-4">
      {/* Collapsible header */}
      <div className="w-full">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h2 className="text-xl font-bold">
                📋 My Complaints
                {totalUnread > 0 && (
                  <span className="ml-2 badge bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 text-xs font-bold">
                    🔔 {totalUnread} new message{totalUnread > 1 ? "s" : ""}
                  </span>
                )}
              </h2>
              <p className="text-sm text-muted">
                Track the status of your submitted complaints.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {pendingCount > 0 && (
              <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 text-sm font-bold">
                {pendingCount} pending
              </span>
            )}
            <span
              className="btn-ghost text-xs"
              onClick={(e) => {
                e.stopPropagation();
                loadMyComplaints();
                loadNotifications();
              }}
            >
              🔄 Refresh
            </span>
          </div>
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

      {/* Collapsible content */}
      {sectionOpen && (
        <>
          {busy && complaints.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">Loading…</p>
          ) : complaints.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">
              You haven't submitted any complaints yet.
            </p>
          ) : (
            <div className="space-y-3">
              {complaints.map((c) => (
                <div key={c.id} className="border border-line rounded-lg overflow-hidden">
                  {/* Summary header */}
                  <div className="p-4 space-y-2 bg-surface/30">
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
                      <span className="text-xs text-muted shrink-0">{c.created_at}</span>
                    </div>
                    <div className="text-xs text-muted flex gap-2">
                      <span>{c.faculty}</span>
                      {c.course_code && <span>· {c.course_code}</span>}
                    </div>
                  </div>

                  {/* Chat area — always visible */}
                  <div className="border-t border-line p-4 space-y-3">
                    <div className="bg-surface rounded p-3 max-h-[300px] overflow-y-auto space-y-2">

                      {/* Student's original complaint — on the RIGHT (it's your message) */}
                      <div className="flex justify-end">
                        <div className="max-w-[80%]">
                          <p className="text-[10px] text-muted mb-0.5 text-right">You · {c.created_at}</p>
                          <div className="bg-gray-100 rounded-lg rounded-tr-none p-2 text-sm border border-line">
                            {c.message}
                          </div>
                        </div>
                      </div>

                      {/* Chat messages from the API */}
                      {(messages[c.id] || []).map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex ${msg.sender_role === "client" ? "justify-end" : "justify-start"}`}
                        >
                          <div className="max-w-[80%]">
                            <p className={`text-[10px] text-muted mb-0.5 ${msg.sender_role === "client" ? "text-right" : ""}`}>
                              {msg.sender_role === "admin" ? "Admin" : "You"} · {msg.created_at}
                            </p>
                            <div
                              className={`rounded-lg p-2 text-sm ${
                                msg.sender_role === "admin"
                                  ? "bg-brand/10 dark:bg-brand/20 rounded-tl-none border border-brand/20"
                                  : "bg-gray-100 rounded-tr-none border border-line"
                              }`}
                            >
                              {msg.message}
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Scroll anchor */}
                      <div ref={(el) => { messagesEndRefs.current[c.id] = el; }} />
                    </div>

                    {/* Reply button + text area */}
                    {c.status === "pending" && (
                      <div className="mt-2 space-y-2">
                        {activeReply === c.id ? (
                          <>
                            <textarea
                              value={replyTexts[c.id] || ""}
                              onChange={(e) =>
                                setReplyTexts((prev) => ({ ...prev, [c.id]: e.target.value }))
                              }
                              placeholder="Type your reply…"
                              className="input-field min-h-[60px] text-sm"
                              autoFocus
                            />
                            <div className="flex items-center justify-between">
                              <button
                                className="btn-primary text-sm"
                                disabled={!(replyTexts[c.id] || "").trim() || sending === c.id}
                                onClick={() => handleSendReply(c.id)}
                              >
                                {sending === c.id ? "Sending…" : "➤ Send"}
                              </button>
                              <button
                                className="btn-ghost text-sm"
                                onClick={() => {
                                  setActiveReply(null);
                                  setReplyTexts((prev) => ({ ...prev, [c.id]: "" }));
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </>
                        ) : (
                          <button
                            className="btn-ghost text-sm"
                            onClick={() => setActiveReply(c.id)}
                          >
                            💬 Reply
                          </button>
                        )}
                      </div>
                    )}

                    {/* Show resolved/dismissed info */}
                    {c.resolved_at && (
                      <p className="text-xs text-muted mt-2">
                        {c.status === "resolved" ? "Resolved" : "Dismissed"} by <b>{c.resolved_by || "Admin"}</b> on {c.resolved_at}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}