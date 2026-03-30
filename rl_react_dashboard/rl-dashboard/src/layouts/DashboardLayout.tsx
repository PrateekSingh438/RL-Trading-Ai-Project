import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuthStore, useUIStore } from "../store";
import { ThemeToggle } from "../components/ui/ThemeProvider";
import { ToastContainer } from "../components/ui/Toast";
import { useState } from "react";

// ─── Nav icon helpers ──────────────────────────────────────────────────────────
const IC = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  ),
  analytics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  ),
};

const NAV = [
  { path: "/dashboard", label: "Dashboard",    icon: IC.dashboard },
  { path: "/analytics", label: "Analytics",    icon: IC.analytics  },
  { path: "/history",   label: "Trade History", icon: IC.history   },
  { path: "/settings",  label: "Settings",     icon: IC.settings   },
];

export default function DashboardLayout() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebar = (
    <>
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b border-neutral-200/60 dark:border-neutral-800/60 px-4">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-emerald-500 flex items-center justify-center">
              <span className="text-white text-[10px] font-black">RL</span>
            </div>
            <span className="text-[13px] font-bold tracking-tight text-neutral-800 dark:text-neutral-100">
              Trader
            </span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all"
        >
          {sidebarOpen ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="w-3.5 h-3.5">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="w-3.5 h-3.5">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          )}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => {
          const active =
            location.pathname === item.path ||
            (item.path === "/dashboard" && location.pathname === "/");
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] transition-all duration-150 ${
                active
                  ? "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-sm font-semibold"
                  : "text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800/60"
              }`}
            >
              <span className="w-5 flex items-center justify-center shrink-0">
                {item.icon}
              </span>
              {sidebarOpen && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Theme */}
      <div className="px-3 pb-2">
        {sidebarOpen ? (
          <ThemeToggle />
        ) : (
          <button
            onClick={() => {
              const s = useUIStore.getState();
              s.setTheme(s.theme === "dark" ? "light" : "dark");
            }}
            className="w-full rounded-md py-1.5 flex items-center justify-center text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all"
            title="Toggle theme"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-4 h-4">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          </button>
        )}
      </div>

      {/* User */}
      <div className="border-t border-neutral-200/60 dark:border-neutral-800/60 p-3">
        {sidebarOpen ? (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shrink-0">
              <span className="text-white text-[10px] font-bold">
                {(user?.name || "U")[0]}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-semibold text-neutral-700 dark:text-neutral-300 truncate">
                {user?.name || "User"}
              </div>
              <div className="text-[10px] text-neutral-400 truncate">
                {user?.email}
              </div>
            </div>
            <button
              onClick={logout}
              className="rounded-md px-2 py-1 text-[10px] text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all font-medium"
            >
              Exit
            </button>
          </div>
        ) : (
          <button
            onClick={logout}
            className="w-full rounded-md py-1.5 flex items-center justify-center text-neutral-400 hover:text-red-500 transition-all"
            title="Logout"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-4 h-4">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        )}
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-neutral-100/50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors duration-200">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-56 flex flex-col bg-white dark:bg-neutral-950 border-r border-neutral-200/60 dark:border-neutral-800/60 transform transition-transform duration-200 lg:hidden ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebar}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={`hidden lg:flex flex-col border-r border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950 transition-all duration-200 ${
          sidebarOpen ? "w-52" : "w-14"
        }`}
      >
        {sidebar}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between h-12 px-4 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-white dark:bg-neutral-950">
          <button
            onClick={() => setMobileOpen(true)}
            className="text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-5 h-5">
              <line x1="3" y1="6"  x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-emerald-500 flex items-center justify-center">
              <span className="text-white text-[8px] font-black">RL</span>
            </div>
            <span className="text-[12px] font-bold">Trader</span>
          </div>
          <div className="w-6" />
        </div>

        <main className="flex-1 overflow-y-auto min-h-0">
          <Outlet />
        </main>
      </div>

      {/* Global toast notifications */}
      <ToastContainer />
    </div>
  );
}
