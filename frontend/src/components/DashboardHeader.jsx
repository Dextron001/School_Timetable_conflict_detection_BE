import { useAuth } from "../context/AuthContext";
import ThemeToggle from "./ThemeToggle";

export default function DashboardHeader({ title, subtitle }) {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-line bg-card/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-brand shadow-soft grid place-items-center ring-1 ring-black/5">
            <svg viewBox="0 0 48 48" className="h-5 w-5" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M16 32 L32 16" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="15" cy="33" r="6.5" stroke="white" strokeWidth="2.5" />
              <circle cx="33" cy="15" r="6.5" fill="white" />
            </svg>
          </div>
          <div className="leading-tight">
            <p className="font-bold text-sm">{title}</p>
            <p className="text-[11px] text-muted uppercase tracking-wide">{subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user?.role === "admin" && (
            <a
              href="/users"
              className="text-xs font-semibold text-brand hover:underline hidden sm:inline"
            >
              Manage Users
            </a>
          )}
          <ThemeToggle />
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold">{user?.full_name}</p>
            <span
              className={`badge ${
                user?.role === "admin"
                  ? "bg-brand/15 text-brand"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300"
              }`}
            >
              {user?.role}
            </span>
          </div>
          <button className="btn-ghost !py-2" onClick={logout}>
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}