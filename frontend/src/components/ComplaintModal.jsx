import { useState } from "react";
import { api } from "../api";
import { useToast } from "../context/ToastContext";

export default function ComplaintModal({ faculty, onClose, onSubmitted }) {
  const toast = useToast();
  const [courseCode, setCourseCode] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!subject.trim()) return toast.error("Please enter a subject.");
    if (!message.trim()) return toast.error("Please enter your complaint.");
    setBusy(true);
    try {
      await api.submitComplaint({
        faculty,
        course_code: courseCode.trim() || null,
        subject: subject.trim(),
        message: message.trim(),
      });
      toast.success("Complaint submitted! Admin will review it.");
      onSubmitted?.();
      onClose();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <form
        onSubmit={handleSubmit}
        className="card p-6 w-full max-w-lg space-y-4 animate-in"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">📢 Submit a Complaint</h2>
          <button type="button" onClick={onClose} className="text-muted hover:text-foreground text-xl">✕</button>
        </div>

        <p className="text-sm text-muted">
          Report a timetable conflict, scheduling issue, or any concern about
          the <b>{faculty}</b> timetable. The admin will review your complaint.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold mb-1">
              Course code <span className="text-muted">(optional — if about a specific course)</span>
            </label>
            <input
              type="text"
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value)}
              placeholder="e.g. CSC206"
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Clash between CSC206 and SEN201"
              className="input-field"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1">Your complaint</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Describe the issue in detail..."
              className="input-field min-h-[100px]"
              required
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Submitting…" : "Submit complaint"}
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}