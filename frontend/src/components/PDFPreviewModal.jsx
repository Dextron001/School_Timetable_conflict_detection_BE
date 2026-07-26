import { useState, useEffect } from "react";
import { api } from "../api";

export default function PDFPreviewModal({ faculty, onClose, onDownloaded }) {
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let urlToClean = null;
    async function loadPdf() {
      try {
        setLoading(true);
        const res = await api.exportPdf(faculty);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        urlToClean = url;
        setPdfUrl(url);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    loadPdf();

    // Clean up blob URL when modal closes or unmounts
    return () => {
      if (urlToClean) URL.revokeObjectURL(urlToClean);
    };
  }, [faculty]);

  function handleDownload() {
    if (!pdfUrl) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = `${faculty}_Combined_Timetable.pdf`;
    a.click();
    onDownloaded?.();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden border border-line">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-line bg-surface">
          <div>
            <h3 className="text-lg font-bold text-ink">PDF Preview</h3>
            <p className="text-xs text-muted">
              {faculty} — All Departments, All Levels (100–400)
            </p>
          </div>
          <div className="flex gap-3">
            <button
              className="btn-primary"
              onClick={handleDownload}
              disabled={!pdfUrl}
            >
              ⬇ Download PDF
            </button>
            <button className="btn-ghost" onClick={onClose}>
              ✕ Close
            </button>
          </div>
        </div>

        {/* PDF viewer */}
        <div className="flex-1 overflow-hidden bg-gray-100 dark:bg-gray-800">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-3">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand mx-auto"></div>
                <p className="text-muted text-sm">Generating PDF preview…</p>
              </div>
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-3">
                <p className="text-red-500 text-sm font-semibold">Error: {error}</p>
                <button className="btn-ghost" onClick={onClose}>Close</button>
              </div>
            </div>
          )}
          {pdfUrl && !loading && (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title="PDF Preview"
            />
          )}
        </div>
      </div>
    </div>
  );
}