import { useAuth } from "../context/AuthContext";
import ThemeToggle from "./ThemeToggle";

const PCU_LOGO_URL = "https://pcu.edu.ng/storage/settings/site_logo_header.png";

export default function DashboardHeader({ title, subtitle }) {
  const { user, logout } = useAuth();

  function displayRole(role) {
    return role === "admin" ? "Admin" : "Student";
  }

  return (
    <header className="border-b border-line bg-card/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-white shadow-soft grid place-items-center ring-1 ring-black/5 overflow-hidden">
            <img src={PCU_LOGO_URL} alt="PCU" className="h-8 w-8 object-contain" />
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
              {displayRole(user?.role)}
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