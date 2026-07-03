import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 4000);
  }, []);

  const toast = {
    info: (m) => push(m, "info"),
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error"),
  };

  const colors = {
    info: "border-brand bg-card",
    success: "border-emerald-500 bg-card",
    error: "border-red-500 bg-card",
  };
  const dot = {
    info: "bg-brand",
    success: "bg-emerald-500",
    error: "bg-red-500",
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`card border-l-4 ${colors[t.type]} px-4 py-3 flex items-start gap-3 animate-[fadeIn_.2s_ease]`}
          >
            <span className={`mt-1 h-2 w-2 rounded-full ${dot[t.type]}`} />
            <p className="text-sm text-ink leading-snug">{t.message}</p>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
