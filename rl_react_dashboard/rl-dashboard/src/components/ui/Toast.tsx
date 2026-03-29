import { useEffect, useState } from "react";
import { useNotificationStore } from "../../store";
import type { AppNotification } from "../../store";

const STYLES: Record<AppNotification["type"], string> = {
  success:
    "border-emerald-500/40 bg-emerald-950/80 text-emerald-300 dark:bg-emerald-950/90",
  error:
    "border-red-500/40 bg-red-950/80 text-red-300 dark:bg-red-950/90",
  warning:
    "border-amber-500/40 bg-amber-950/80 text-amber-300 dark:bg-amber-950/90",
  info:
    "border-sky-500/40 bg-sky-950/80 text-sky-300 dark:bg-sky-950/90",
};

const ICONS: Record<AppNotification["type"], string> = {
  success: "▲",
  error: "▼",
  warning: "⚠",
  info: "ℹ",
};

function ToastItem({ n }: { n: AppNotification }) {
  const dismiss = useNotificationStore((s) => s.dismiss);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setVisible(true), 10);
    const t2 = setTimeout(() => {
      setVisible(false);
      setTimeout(() => dismiss(n.id), 300);
    }, 3800);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [n.id, dismiss]);

  return (
    <div
      className={`
        flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur-md
        transition-all duration-300 select-none
        ${visible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-10"}
        ${STYLES[n.type]}
      `}
    >
      <span className="text-[13px] font-bold shrink-0 mt-px">{ICONS[n.type]}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-semibold leading-tight">{n.title}</div>
        {n.message && (
          <div className="text-[11px] opacity-70 mt-0.5 line-clamp-2 leading-relaxed">
            {n.message}
          </div>
        )}
      </div>
      <button
        onClick={() => dismiss(n.id)}
        className="text-[16px] leading-none opacity-30 hover:opacity-70 shrink-0 transition-opacity"
      >
        ×
      </button>
    </div>
  );
}

export function ToastContainer() {
  const notifications = useNotificationStore((s) => s.notifications);
  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-[9999] w-72 flex flex-col gap-2 pointer-events-none">
      <div className="pointer-events-auto flex flex-col gap-2">
        {notifications.map((n) => (
          <ToastItem key={n.id} n={n} />
        ))}
      </div>
    </div>
  );
}
