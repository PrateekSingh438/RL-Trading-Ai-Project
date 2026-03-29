// ═══════════════════════════════════════════════════════════
// Formatters — consistent number/date formatting
// ═══════════════════════════════════════════════════════════

export function fmtMoney(n: number): string {
  const sign = n < 0 ? "-" : "";
  return sign + "$" + Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function fmtMoneyPrecise(n: number): string {
  const sign = n < 0 ? "-" : "";
  return sign + "$" + Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function fmtPct(n: number, decimals = 2): string {
  return (n * 100).toFixed(decimals) + "%";
}

export function fmtNumber(n: number, decimals = 2): string {
  return n.toFixed(decimals);
}

export function fmtDate(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function fmtTimestamp(ts: number): string {
  return `${fmtDate(ts)} ${fmtTime(ts)}`;
}

export function fmtCompact(n: number): string {
  if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toFixed(0);
}
