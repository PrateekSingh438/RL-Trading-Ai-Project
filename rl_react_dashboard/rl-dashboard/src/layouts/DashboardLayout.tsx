import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuthStore, useUIStore } from "../store";
import { ThemeToggle } from "../components/ui/ThemeProvider";
import { ToastContainer } from "../components/ui/Toast";
import { useState } from "react";

const NAV = [
  { path: "/dashboard", label: "Dashboard", icon: "◎", activeIcon: "◉" },
  { path: "/analytics", label: "Analytics", icon: "◫", activeIcon: "◧" },
  { path: "/history", label: "Trade History", icon: "◱", activeIcon: "◲" },
  { path: "/settings", label: "Settings", icon: "⚙", activeIcon: "⚙" },
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
          className="rounded-md p-1.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all text-[10px]"
        >
          {sidebarOpen ? "◂" : "▸"}
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
              <span className="text-sm w-5 text-center shrink-0">
                {active ? item.activeIcon : item.icon}
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
            className="w-full rounded-md py-1.5 text-sm text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all"
            title="Toggle theme"
          >
            ◐
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
            className="w-full rounded-md py-1.5 text-sm text-neutral-400 hover:text-red-500 transition-all"
            title="Logout"
          >
            ×
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
            className="text-neutral-500 text-lg"
          >
            ☰
          </button>
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-emerald-500 flex items-center justify-center">
              <span className="text-white text-[8px] font-black">RL</span>
            </div>
            <span className="text-[12px] font-bold">Trader</span>
          </div>
          <div className="w-6" />
        </div>

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Global toast notifications */}
      <ToastContainer />
    </div>
  );
}
