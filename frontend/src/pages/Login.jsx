import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ThemeToggle from "../components/ThemeToggle";

export default function Login() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const user = await login(username.trim(), password);
      toast.success(`Welcome, ${user.full_name}`);
      navigate(user.role === "admin" ? "/admin" : "/client", { replace: true });
    } catch (err) {
      toast.error(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const quickFill = (u, p) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="min-h-full grid place-items-center px-4 relative">
      <div className="absolute top-5 right-5">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md">
               <div className="text-center mb-8">
          {/* Hand-crafted brand mark: two nodes joined by a link line */}
          <div className="mx-auto mb-5 h-16 w-16 rounded-2xl bg-brand shadow-soft grid place-items-center ring-1 ring-black/5">
            <svg viewBox="0 0 48 48" className="h-9 w-9" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M16 32 L32 16" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="15" cy="33" r="6.5" stroke="white" strokeWidth="2.5" />
              <circle cx="33" cy="15" r="6.5" fill="white" />
            </svg>
          </div>

          <h1 className="font-serif text-4xl tracking-tight text-ink select-none">
            Resolv<span className="text-brand italic">It</span>
          </h1>

          <div className="mx-auto mt-3 mb-2 h-px w-16 bg-brand/40" />

          <p className="text-[11px] uppercase tracking-[0.25em] text-muted">
            Academic Timetable System
          </p>
        </div>

        <form onSubmit={submit} className="card p-7 space-y-5">
          <div>
            <label className="label">Username</label>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin or client"
              required
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <div className="text-center text-xs text-muted">
            <p className="mb-2">Demo accounts — click to fill:</p>
            <div className="flex gap-2 justify-center">
              <button
                type="button"
                onClick={() => quickFill("admin", "admin123")}
                className="badge bg-brand/15 text-brand hover:bg-brand/25"
              >
                admin / admin123
              </button>
              <button
                type="button"
                onClick={() => quickFill("client", "client123")}
                className="badge bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900 dark:text-emerald-300"
              >
                client / client123
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
