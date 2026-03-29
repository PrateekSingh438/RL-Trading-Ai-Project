// Place at: src/components/ui/ThemeProvider.tsx
//
// Reads theme from Zustand store, applies "dark" class to <html>.
// Supports: "light", "dark", "system".

import { useEffect } from "react";
import { useUIStore } from "../../store";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUIStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;

    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      root.classList.toggle("dark", mq.matches);
      const handler = (e: MediaQueryListEvent) =>
        root.classList.toggle("dark", e.matches);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }

    root.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return <>{children}</>;
}

export function ThemeToggle() {
  const theme = useUIStore((s) => s.theme);
  const setTheme = useUIStore((s) => s.setTheme);

  const options = [
    { value: "light" as const, label: "☀" },
    { value: "dark" as const, label: "☾" },
    { value: "system" as const, label: "◐" },
  ];

  return (
    <div className="flex rounded-md bg-neutral-200 dark:bg-neutral-800 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTheme(opt.value)}
          className={`rounded px-2 py-1 text-xs transition-colors ${
            theme === opt.value
              ? "bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-sm"
              : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
          }`}
          title={opt.value}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
