/**
 * DashboardPage v4 — interactive, real-time trading dashboard
 *
 * Panels:
 *  • Live price ticker bar (real quotes from /market/live)
 *  • 8 KPI cards with trend arrows
 *  • Drawdown / risk gauge
 *  • Equity curve sparkline
 *  • TradingView-style candlestick chart
 *  • Agent controls with training progress
 *  • Tabbed side panel: Signals | Positions | Sentiment | News | Importance
 *  • Live news feed (real headlines from /sentiment/news)
 *  • System log with level filter
 */
import { useState, useMemo, memo, useEffect, useRef } from "react";
import { useUIStore, useNotificationStore } from "../store";
import TradingChart from "../components/charts/TradingChart";

const API = "http://localhost:8000/api/v1";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt$ = (v: number) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(2)}M`
    : v >= 1_000
    ? `$${(v / 1_000).toFixed(1)}K`
    : `$${v.toFixed(2)}`;

const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
const fmtN   = (v: number, d = 3) => isNaN(v) ? "—" : v.toFixed(d);

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

// ─── Regime badge ─────────────────────────────────────────────────────────────

const REGIME_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  bull:           { label: "Bull",     color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/25", dot: "bg-emerald-400" },
  bear:           { label: "Bear",     color: "text-red-600 dark:text-red-400",         bg: "bg-red-500/10 border-red-500/25",         dot: "bg-red-400"     },
  sideways:       { label: "Sideways", color: "text-amber-600 dark:text-amber-400",     bg: "bg-amber-500/10 border-amber-500/25",     dot: "bg-amber-400"   },
  high_volatility:{ label: "High Vol", color: "text-purple-600 dark:text-purple-400",   bg: "bg-purple-500/10 border-purple-500/25",   dot: "bg-purple-400"  },
};

function RegimeBadge({ regime }: { regime: string | null }) {
  if (!regime) return null;
  const cfg = REGIME_CONFIG[regime] ?? REGIME_CONFIG.sideways;
  return (
    <div className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-1", cfg.bg)}>
      <span className={cn("h-1.5 w-1.5 rounded-full animate-pulse", cfg.dot)} />
      <span className={cn("text-[10px] font-bold uppercase tracking-wider", cfg.color)}>{cfg.label}</span>
    </div>
  );
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

const MC = memo(function MC({
  label, value, change, positive, icon, sub, accent,
}: {
  label: string; value: string; change?: string; positive?: boolean; icon?: React.ReactNode; sub?: React.ReactNode; accent?: "green" | "red" | "amber" | "blue" | "purple";
}) {
  const accentBar: Record<string, string> = {
    green:  "bg-emerald-500",
    red:    "bg-red-500",
    amber:  "bg-amber-500",
    blue:   "bg-sky-500",
    purple: "bg-violet-500",
  };
  const bar = accent ? accentBar[accent] : (positive === false ? accentBar.red : accentBar.green);
  return (
    <div className="group relative rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 px-4 py-3.5 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all duration-200 hover:shadow-md overflow-hidden">
      <div className={cn("absolute top-0 left-0 right-0 h-0.5", bar)} />
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] uppercase tracking-widest text-neutral-400 dark:text-neutral-500 font-semibold">{label}</span>
        {icon && <span className="opacity-25 group-hover:opacity-50 text-neutral-500 dark:text-neutral-400 transition-opacity">{icon}</span>}
      </div>
      <div className="text-[22px] font-bold text-neutral-900 dark:text-neutral-50 tabular-nums leading-tight">{value}</div>
      {change && (
        <div className={cn("flex items-center gap-1 text-[11px] mt-1 tabular-nums font-semibold", positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400")}>
          <span className="text-[9px]">{positive ? "▲" : "▼"}</span>
          {change}
        </div>
      )}
      {sub && <div className="mt-1.5">{sub}</div>}
    </div>
  );
});

// ─── Live price ticker bar ────────────────────────────────────────────────────

function LiveTicker({ prices }: { prices: Record<string, any> }) {
  const [flash, setFlash] = useState<Record<string, boolean>>({});
  const prevRef = useRef<Record<string, number>>({});

  // Flash a symbol briefly when its price changes
  useEffect(() => {
    const changed: Record<string, boolean> = {};
    for (const [sym, d] of Object.entries(prices)) {
      if (prevRef.current[sym] !== undefined && prevRef.current[sym] !== d.price) {
        changed[sym] = true;
      }
      prevRef.current[sym] = d.price;
    }
    if (Object.keys(changed).length) {
      setFlash(changed);
      const t = setTimeout(() => setFlash({}), 600);
      return () => clearTimeout(t);
    }
  }, [prices]);

  if (!Object.keys(prices).length) return null;

  const anyLive = Object.values(prices).some((d: any) => !d.simulated);

  return (
    <div className="flex gap-2 flex-wrap items-center">
      {/* LIVE or SIM badge */}
      {anyLive ? (
        <div className="flex items-center gap-1 rounded-full bg-sky-500/10 border border-sky-500/25 px-2 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" />
          <span className="text-[9px] font-bold text-sky-500 uppercase tracking-wider">Live</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200/60 dark:border-neutral-700/60 px-2 py-0.5">
          <span className="text-[9px] font-medium text-neutral-400 uppercase tracking-wider">Sim</span>
        </div>
      )}

      {Object.entries(prices).map(([sym, d]: [string, any]) => {
        const up = (d.change ?? 0) >= 0;
        const isFlashing = flash[sym];
        return (
          <div key={sym}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1 border transition-colors duration-300",
              isFlashing
                ? up
                  ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/40"
                  : "bg-red-50 dark:bg-red-500/10 border-red-300 dark:border-red-500/40"
                : "bg-white dark:bg-neutral-900/80 border-neutral-200/60 dark:border-neutral-800/60"
            )}>
            <span className="text-[10px] font-bold text-neutral-500 dark:text-neutral-400">{sym}</span>
            <span className="text-[12px] font-semibold tabular-nums text-neutral-800 dark:text-neutral-100">
              ${(d.price ?? 0).toFixed(2)}
            </span>
            <span className={cn("text-[10px] font-medium tabular-nums", up ? "text-emerald-500" : "text-red-500")}>
              {up ? "▲" : "▼"}{Math.abs(d.change_pct ?? 0).toFixed(2)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Drawdown gauge ───────────────────────────────────────────────────────────

function DrawdownGauge({ current, max }: { current: number; max: number }) {
  const pct = max !== 0 ? Math.min(Math.abs(current) / Math.abs(max), 1) * 100 : 0;
  const color = pct < 40 ? "bg-emerald-500" : pct < 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="mt-1.5">
      <div className="h-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${pct.toFixed(0)}%` }} />
      </div>
      <div className="flex justify-between text-[8px] text-neutral-400 tabular-nums mt-0.5">
        <span>Current {(Math.abs(current) * 100).toFixed(1)}%</span>
        <span>Max {(Math.abs(max) * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

// ─── Equity sparkline ─────────────────────────────────────────────────────────

function EquityCurve({ data }: { data: { value: number }[] }) {
  if (data.length < 2) return <div className="text-[11px] text-neutral-400 text-center py-6">Equity curve appears after agent starts</div>;
  const vals = data.map((d) => d.value);
  const mn = Math.min(...vals), mx = Math.max(...vals), range = mx - mn || 1;
  const W = 600, H = 80;
  const pts = vals.map((v, i) => `${((i / (vals.length - 1)) * W).toFixed(1)},${(H - ((v - mn) / range) * (H - 8) - 4).toFixed(1)}`).join(" ");
  const color = vals[vals.length - 1] >= vals[0] ? "#22c55e" : "#ef4444";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 80 }}>
      <defs>
        <linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.2" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${H} ${pts} ${W},${H}`} fill="url(#eqG)" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Risk meter (semicircle gauge) ────────────────────────────────────────────

function RiskMeter({ sharpe, sortino }: { sharpe: number; sortino: number }) {
  // Map sharpe [-2, 3] → [0, 100]
  const score = Math.round(Math.min(100, Math.max(0, ((sharpe + 2) / 5) * 100)));
  const color = score > 65 ? "#22c55e" : score > 35 ? "#f59e0b" : "#ef4444";
  const label = score > 65 ? "Healthy" : score > 35 ? "Moderate" : "Risky";
  const r = 36, cx = 50, cy = 50;
  const startAngle = Math.PI;
  const endAngle   = startAngle + (score / 100) * Math.PI;
  const x1 = cx + r * Math.cos(startAngle), y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle),   y2 = cy + r * Math.sin(endAngle);
  const large = score > 50 ? 1 : 0;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 100 55" style={{ width: 90, height: 50 }}>
        <path d={`M ${cx - r},${cy} A ${r},${r} 0 0 1 ${cx + r},${cy}`} fill="none" stroke="#e5e7eb" strokeWidth="8" strokeLinecap="round" className="dark:stroke-neutral-700" />
        {score > 0 && (
          <path d={`M ${x1},${y1} A ${r},${r} 0 ${large} 1 ${x2},${y2}`} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 4} textAnchor="middle" fontSize="12" fontWeight="700" fill={color}>{score}</text>
        <text x={cx} y={cy + 6} textAnchor="middle" fontSize="5.5" fill="#9ca3af">{label}</text>
      </svg>
      <div className="flex gap-3 text-[9px] text-neutral-400 tabular-nums">
        <span>Sharpe {fmtN(sharpe, 2)}</span>
        <span>Sortino {fmtN(sortino, 2)}</span>
      </div>
    </div>
  );
}

// ─── Signal row ───────────────────────────────────────────────────────────────

function SignalRow({ s }: { s: any }) {
  const [open, setOpen] = useState(false);
  const ac: Record<string, string> = {
    BUY:  "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/8",
    SELL: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/8",
    HOLD: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/8",
  };
  const dot: Record<string, string> = { BUY: "bg-emerald-500", SELL: "bg-red-500", HOLD: "bg-amber-500" };
  const sentColor: Record<string, string> = {
    positive: "text-emerald-500", negative: "text-red-500", neutral: "text-neutral-400",
  };
  const sent = s.sentiment?.overall ?? "neutral";
  return (
    <div>
      <div
        className={cn("flex items-center gap-3 rounded-lg px-3 py-2 cursor-pointer hover:opacity-90", ac[s.action] ?? ac.HOLD)}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", dot[s.action] ?? dot.HOLD)} />
        <div className="flex-1 min-w-0 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold">{s.action}</span>
            <span className="text-[11px] font-semibold opacity-80">{s.symbol}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] tabular-nums opacity-70">
            <span>${Number(s.price ?? 0).toFixed(2)}</span>
            <span>{Math.round((s.confidence ?? 0.5) * 100)}%</span>
            {sent && (
              <span className={cn("font-semibold", sentColor[sent])}>
                {sent === "positive" ? "↑" : sent === "negative" ? "↓" : "~"}
                {s.sentiment?.live && <span className="ml-0.5 text-[8px] text-sky-400">L</span>}
              </span>
            )}
          </div>
        </div>
        <span className="text-[9px] opacity-40">{open ? "▲" : "▼"}</span>
      </div>
      {open && s.reasoning && (
        <div className="mx-1 mb-1 px-3 py-2 rounded-b-lg bg-neutral-50 dark:bg-neutral-800/60 border-x border-b border-neutral-200/60 dark:border-neutral-700/40">
          <p className="text-[10px] text-neutral-500 dark:text-neutral-400 leading-relaxed">{s.reasoning}</p>
          {s.regime && (
            <span className={cn("inline-block mt-1 text-[9px] font-semibold uppercase tracking-wider", REGIME_CONFIG[s.regime]?.color ?? "text-neutral-400")}>
              {s.regime.replace("_", " ")} regime
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Positions panel ─────────────────────────────────────────────────────────

function PositionsPanel({ positions }: { positions: any[] }) {
  if (!positions.length)
    return <div className="text-[11px] text-neutral-400 text-center py-6">No open positions</div>;
  const totalMV = positions.reduce((s, p) => s + Math.abs(p.market_value), 0);
  return (
    <div className="space-y-2">
      {positions.map((p) => (
        <div key={p.symbol} className="rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-3 py-2.5">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-bold text-neutral-800 dark:text-neutral-200">{p.symbol}</span>
              <span className={cn("text-[9px] font-semibold px-1.5 py-0.5 rounded", p.shares >= 0 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400")}>
                {p.shares >= 0 ? "LONG" : "SHORT"}
              </span>
            </div>
            <span className="text-[12px] font-semibold tabular-nums">{fmt$(p.market_value)}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-neutral-400 tabular-nums">
            <span>{Math.abs(p.shares).toFixed(2)} sh</span>
            <span>@</span>
            <span>${p.current_price.toFixed(2)}</span>
            <span className="text-neutral-300 dark:text-neutral-700">·</span>
            <span>{p.weight.toFixed(1)}% wt</span>
          </div>
          <div className="mt-1.5 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div
              className="h-full rounded-full bg-sky-500 transition-all"
              style={{ width: `${Math.min((Math.abs(p.market_value) / Math.max(totalMV, 1)) * 100, 100).toFixed(0)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Sentiment panel ─────────────────────────────────────────────────────────

function SentimentPanel({ signals }: { signals: any[] }) {
  const stats = useMemo(() => {
    const recent = signals.slice(-50);
    if (!recent.length) return null;
    const counts = { positive: 0, negative: 0, neutral: 0 };
    let totalConf = 0;
    for (const s of recent) {
      const o = s.sentiment?.overall ?? "neutral";
      counts[o as keyof typeof counts]++;
      totalConf += s.sentiment?.confidence ?? 0;
    }
    const dom = (Object.entries(counts) as [string, number][]).sort((a, b) => b[1] - a[1])[0][0];
    return { counts, total: recent.length, avgConf: totalConf / recent.length, dominant: dom };
  }, [signals]);

  const bySymbol = useMemo(() => {
    const map: Record<string, { pos: number; neg: number; neu: number; count: number }> = {};
    for (const s of signals.slice(-80)) {
      const sym = s.symbol;
      const o   = s.sentiment?.overall ?? "neutral";
      if (!map[sym]) map[sym] = { pos: 0, neg: 0, neu: 0, count: 0 };
      if (o === "positive") map[sym].pos++;
      else if (o === "negative") map[sym].neg++;
      else map[sym].neu++;
      map[sym].count++;
    }
    return Object.entries(map).slice(0, 6);
  }, [signals]);

  if (!stats)
    return <div className="flex flex-col items-center justify-center h-full gap-2">
      <span className="text-2xl opacity-20">📊</span>
      <span className="text-[11px] text-neutral-400">Sentiment data appears after agent starts</span>
    </div>;

  const domColors: Record<string, string> = {
    positive: "text-emerald-600 dark:text-emerald-400",
    negative: "text-red-600 dark:text-red-400",
    neutral:  "text-neutral-500 dark:text-neutral-400",
  };
  const barC: Record<string, string> = { positive: "bg-emerald-500", negative: "bg-red-500", neutral: "bg-neutral-400" };

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-3 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium">Overall (last 50 signals)</span>
          <span className="text-[10px] text-neutral-400 tabular-nums">{(stats.avgConf * 100).toFixed(0)}% avg conf</span>
        </div>
        <div className={cn("text-[15px] font-bold capitalize mb-2", domColors[stats.dominant])}>{stats.dominant}</div>
        <div className="flex gap-1 h-2 rounded-full overflow-hidden">
          {(["positive", "negative", "neutral"] as const).map((k) => {
            const pct = (stats.counts[k] / stats.total) * 100;
            return pct > 0 ? <div key={k} className={cn("h-full", barC[k])} style={{ width: `${pct.toFixed(1)}%` }} /> : null;
          })}
        </div>
        <div className="flex justify-between mt-1 text-[9px] text-neutral-400 tabular-nums">
          <span>+{stats.counts.positive}</span><span>~{stats.counts.neutral}</span><span>-{stats.counts.negative}</span>
        </div>
      </div>
      {bySymbol.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium">By Symbol</div>
          {bySymbol.map(([sym, d]) => {
            const t2 = d.count || 1;
            const posPct = (d.pos / t2) * 100;
            const negPct = (d.neg / t2) * 100;
            return (
              <div key={sym}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300">{sym}</span>
                  <span className="text-[9px] text-neutral-400">{d.count} signals</span>
                </div>
                <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                  <div className="h-full bg-emerald-500" style={{ width: `${posPct.toFixed(1)}%` }} />
                  <div className="h-full bg-red-500"     style={{ width: `${negPct.toFixed(1)}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Live news panel ──────────────────────────────────────────────────────────

function NewsPanel({ news, onRefresh }: { news: any[]; onRefresh?: () => Promise<void> }) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    await onRefresh();
    setTimeout(() => setRefreshing(false), 1500);
  };

  if (!news.length)
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" />
          <span className="text-[11px] text-neutral-400">Fetching live news…</span>
        </div>
        {onRefresh && (
          <button onClick={handleRefresh} disabled={refreshing}
            className="rounded-lg px-3 py-1.5 text-[10px] font-semibold bg-sky-500/10 border border-sky-500/25 text-sky-600 dark:text-sky-400 hover:bg-sky-500/20 transition-all disabled:opacity-50">
            {refreshing ? "Refreshing…" : "Fetch now"}
          </button>
        )}
      </div>
    );

  const liveCount  = news.filter((n) => n.is_live).length;
  const aiCount    = news.filter((n) => n.ai_scored).length;
  const sentDot: Record<string, string> = {
    positive: "bg-emerald-400", negative: "bg-red-400", neutral: "bg-neutral-400",
  };
  const sentBg: Record<string, string> = {
    positive: "border-l-emerald-400", negative: "border-l-red-400", neutral: "border-l-neutral-300 dark:border-l-neutral-700",
  };

  return (
    <div className="space-y-2">
      {/* Header row */}
      <div className="flex items-center justify-between px-1 mb-1">
        <span className="text-[10px] text-neutral-400">{news.length} articles</span>
        <div className="flex items-center gap-1.5">
          {onRefresh && (
            <button onClick={handleRefresh} disabled={refreshing}
              title="Refresh news"
              className="rounded-md p-1 text-neutral-400 hover:text-sky-500 hover:bg-sky-500/10 transition-all disabled:opacity-40">
              <svg className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
            </button>
          )}
          {aiCount > 0 && (
            <div className="flex items-center gap-1 rounded-full bg-violet-500/10 border border-violet-500/25 px-2 py-0.5">
              <svg className="w-2.5 h-2.5 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2z"/>
              </svg>
              <span className="text-[9px] font-bold text-violet-500 uppercase tracking-wider">AI · {aiCount}</span>
            </div>
          )}
          {liveCount > 0 && (
            <div className="flex items-center gap-1 rounded-full bg-sky-500/10 border border-sky-500/25 px-2 py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" />
              <span className="text-[9px] font-bold text-sky-500 uppercase tracking-wider">{liveCount} live</span>
            </div>
          )}
        </div>
      </div>

      {news.map((item, i) => (
        <div key={i}
          className={cn(
            "rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-3 py-2.5 border-l-2",
            sentBg[item.sentiment] ?? sentBg.neutral
          )}>
          <div className="flex items-start gap-2">
            <span className={cn("h-1.5 w-1.5 rounded-full mt-1.5 shrink-0", sentDot[item.sentiment] ?? sentDot.neutral)} />
            <div className="flex-1 min-w-0">
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer"
                   className="text-[11px] font-medium text-neutral-800 dark:text-neutral-200 leading-snug hover:text-sky-600 dark:hover:text-sky-400 line-clamp-2">
                  {item.title}
                </a>
              ) : (
                <p className="text-[11px] font-medium text-neutral-800 dark:text-neutral-200 leading-snug line-clamp-2">{item.title}</p>
              )}
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-[9px] text-neutral-400">
                <span className="font-bold text-neutral-600 dark:text-neutral-300">{item.ticker}</span>
                <span>{item.source}</span>
                {item.is_live ? (
                  <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-600 dark:text-sky-400 font-semibold">
                    <span className="h-1 w-1 rounded-full bg-sky-400 animate-pulse" />
                    LIVE
                  </span>
                ) : (
                  <span className="px-1 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-400 font-medium">SIM</span>
                )}
                {item.ai_scored && (
                  <span className="px-1.5 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-600 dark:text-violet-400 font-semibold">AI</span>
                )}
                <span>{item.timestamp}</span>
                <span className={cn("font-semibold",
                  item.impact_score > 0 ? "text-emerald-500" : item.impact_score < 0 ? "text-red-500" : "text-neutral-400")}>
                  {item.impact_score > 0 ? "+" : ""}{(item.impact_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Feature importance ───────────────────────────────────────────────────────

function FeatureImportance({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).slice(0, 10);
  if (!entries.length)
    return <div className="text-[11px] text-neutral-400 text-center py-4">Feature importance computed after 30 steps</div>;
  const mx = Math.max(...entries.map((e) => e[1]));
  return (
    <div className="space-y-1.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2">
          <span className="text-[10px] text-neutral-500 w-12 text-right tabular-nums font-mono truncate">{k}</span>
          <div className="flex-1 h-3 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
            <div className="h-full rounded-full bg-emerald-500 transition-all duration-500" style={{ width: `${((v / mx) * 100).toFixed(0)}%` }} />
          </div>
          <span className="text-[9px] text-neutral-400 tabular-nums w-8">{(v * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// ─── Log line ─────────────────────────────────────────────────────────────────

// ─── Trade Performance Analytics ────────────────────────────────────────────

function TradeAnalytics({ trades }: { trades: any[] }) {
  const completed = trades.filter((t) => t.action === "BUY" || t.action === "SELL");
  const recent = completed.slice(-40);

  // Rolling win rate: pair up BUY→SELL as round trips, or treat each trade return
  // Use pnl_pct if present, otherwise fall back to action-based coloring
  const bars = recent.slice(-20).map((t) => {
    const ret = t.pnl_pct ?? t.return ?? (t.action === "BUY" ? null : null);
    const won = ret != null ? ret > 0 : t.action === "SELL" ? (t.pnl_pct ?? 0) > 0 : null;
    return { won, ret, action: t.action };
  });

  // Stats from all completed trades with return info
  const withReturn = completed.filter((t) => t.pnl_pct != null || t.return != null);
  const returns    = withReturn.map((t) => t.pnl_pct ?? t.return ?? 0);
  const wins       = returns.filter((r) => r > 0);
  const losses     = returns.filter((r) => r < 0);
  const winRate    = returns.length > 0 ? wins.length / returns.length : null;
  const avgRet     = returns.length > 0 ? returns.reduce((a, b) => a + b, 0) / returns.length : null;
  const bestRet    = returns.length > 0 ? Math.max(...returns) : null;
  const worstRet   = returns.length > 0 ? Math.min(...returns) : null;
  const avgWin     = wins.length   > 0 ? wins.reduce((a, b) => a + b, 0) / wins.length : null;
  const avgLoss    = losses.length > 0 ? losses.reduce((a, b) => a + b, 0) / losses.length : null;

  // Current streak
  let streak = 0;
  let streakType: "W" | "L" | null = null;
  for (let i = returns.length - 1; i >= 0; i--) {
    const w = returns[i] > 0;
    if (streakType === null) { streakType = w ? "W" : "L"; streak = 1; }
    else if ((streakType === "W") === w) streak++;
    else break;
  }

  // Buy vs sell count from all signals
  const buys  = completed.filter((t) => t.action === "BUY").length;
  const sells = completed.filter((t) => t.action === "SELL").length;

  const pf = (v: number | null, d = 2) =>
    v == null ? "—" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(d)}%`;

  return (
    <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-100 dark:border-neutral-800/60">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-sky-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <span className="text-[12px] font-semibold text-neutral-700 dark:text-neutral-300">Trade Analytics</span>
          <span className="text-[9px] text-neutral-400 tabular-nums">{completed.length} trades</span>
        </div>
        {streakType && streak >= 2 && (
          <span className={cn(
            "rounded-full px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wide",
            streakType === "W"
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
              : "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20"
          )}>
            {streak}{streakType} Streak
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Rolling win-rate bar chart — last 20 trades */}
        {completed.length === 0 ? (
          <div className="text-[11px] text-neutral-400 text-center py-4">No trades yet</div>
        ) : (
          <>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-semibold">Last 20 Trades</span>
                {winRate != null && (
                  <span className={cn("text-[11px] font-bold tabular-nums", winRate >= 0.5 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400")}>
                    {(winRate * 100).toFixed(0)}% win rate
                  </span>
                )}
              </div>
              <div className="flex items-end gap-0.5 h-8">
                {bars.length === 0 ? (
                  <span className="text-[10px] text-neutral-400">Waiting for trades…</span>
                ) : (
                  bars.map((b, i) => {
                    // height proportional to |return|, capped at full bar
                    const mag  = b.ret != null ? Math.min(Math.abs(b.ret) * 400, 1) : 0.5;
                    const h    = Math.max(mag * 100, 20);
                    const bg   = b.ret != null
                      ? (b.ret > 0 ? "bg-emerald-500" : "bg-red-500")
                      : (b.action === "BUY" ? "bg-sky-400" : "bg-amber-400");
                    return (
                      <div
                        key={i}
                        title={b.ret != null ? pf(b.ret) : b.action}
                        className={cn("flex-1 rounded-sm transition-all", bg)}
                        style={{ height: `${h}%` }}
                      />
                    );
                  })
                )}
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Avg Return",  val: pf(avgRet),   pos: (avgRet ?? 0) >= 0 },
                { label: "Avg Win",     val: pf(avgWin),   pos: true },
                { label: "Avg Loss",    val: pf(avgLoss),  pos: false },
                { label: "Best Trade",  val: pf(bestRet),  pos: true },
                { label: "Worst Trade", val: pf(worstRet), pos: false },
                { label: "Buy / Sell",  val: `${buys} / ${sells}`, pos: null },
              ].map(({ label, val, pos }) => (
                <div key={label} className="rounded-lg bg-neutral-50 dark:bg-neutral-800/60 px-3 py-2">
                  <div className="text-[9px] uppercase tracking-wider text-neutral-400 font-semibold mb-0.5">{label}</div>
                  <div className={cn(
                    "text-[13px] font-bold tabular-nums",
                    pos === null
                      ? "text-neutral-700 dark:text-neutral-200"
                      : pos
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-red-500 dark:text-red-400"
                  )}>{val}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── AI Analyst ───────────────────────────────────────────────────────────────

function AIAnalyst() {
  const [text, setText]           = useState("");
  const [loading, setLoading]     = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError]         = useState("");
  const scrollRef                 = useRef<HTMLDivElement>(null);
  const abortRef                  = useRef<AbortController | null>(null);

  const analyze = async () => {
    if (loading) {
      abortRef.current?.abort();
      return;
    }
    setLoading(true);
    setError("");
    setText("");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await fetch(`${API}/portfolio/analysis`, { signal: ctrl.signal });
      if (!res.ok) {
        setError(`Server error ${res.status}`);
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) { setError("No response body"); return; }
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setText((prev) => prev + chunk);
        // Auto-scroll as text streams in
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }
      setLastUpdated(new Date());
    } catch (e: any) {
      if (e?.name !== "AbortError") setError("Connection failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-100 dark:border-neutral-800/60">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-violet-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2z"/>
          </svg>
          <span className="text-[12px] font-semibold text-neutral-700 dark:text-neutral-300">AI Portfolio Analyst</span>
          {loading && (
            <div className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
              <span className="text-[9px] text-violet-500 font-medium">Analyzing…</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && !loading && (
            <span className="text-[9px] text-neutral-400 tabular-nums">
              {lastUpdated.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          )}
          <button
            onClick={analyze}
            className={cn(
              "rounded-lg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide transition-all",
              loading
                ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-500 hover:bg-neutral-200 dark:hover:bg-neutral-700"
                : "bg-violet-500 text-white hover:bg-violet-600 shadow-sm shadow-violet-500/20"
            )}>
            {loading ? "Stop" : text ? "Re-analyze" : "Analyze"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div
        ref={scrollRef}
        className={cn("overflow-y-auto overscroll-contain scrollbar-thin transition-all", text || loading || error ? "h-52" : "h-20")}
      >
        {error && (
          <div className="px-4 py-3 text-[11px] text-red-500 dark:text-red-400">{error}</div>
        )}
        {!text && !loading && !error && (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <svg className="w-5 h-5 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2z"/>
            </svg>
            <span className="text-[11px] text-neutral-400">Click Analyze for an AI-powered portfolio report</span>
          </div>
        )}
        {(text || loading) && (
          <div className="px-4 py-3 space-y-2 text-[11px] text-neutral-700 dark:text-neutral-300 leading-relaxed">
            {text.split("\n").map((line, i) => {
              if (/^###\s/.test(line))
                return <div key={i} className="text-[12px] font-bold text-neutral-800 dark:text-neutral-100 mt-3">{line.replace(/^###\s/, "")}</div>;
              if (/^##\s/.test(line))
                return <div key={i} className="text-[13px] font-bold text-violet-600 dark:text-violet-400 mt-4 border-b border-neutral-100 dark:border-neutral-800 pb-1">{line.replace(/^##\s/, "")}</div>;
              if (/^#\s/.test(line))
                return <div key={i} className="text-[14px] font-bold text-neutral-900 dark:text-neutral-50 mt-4">{line.replace(/^#\s/, "")}</div>;
              // Lines that are entirely **bold** (AI uses these as section headings)
              if (/^\*\*(.+)\*\*$/.test(line)) {
                const title = line.replace(/^\*\*/, "").replace(/\*\*$/, "");
                return <div key={i} className="text-[13px] font-bold text-violet-600 dark:text-violet-400 mt-4 border-b border-neutral-100 dark:border-neutral-800 pb-1">{title}</div>;
              }
              if (/^\*\s|^-\s/.test(line)) {
                const content = line.replace(/^\*\s|^-\s/, "").replace(/\*\*(.+?)\*\*/g, "§§$1§§");
                return (
                  <div key={i} className="flex gap-2">
                    <span className="text-violet-400 shrink-0 mt-0.5">•</span>
                    <span>{content.split("§§").map((part, j) =>
                      j % 2 === 1 ? <strong key={j} className="font-semibold text-neutral-800 dark:text-neutral-100">{part}</strong> : part
                    )}</span>
                  </div>
                );
              }
              if (line.trim() === "") return <div key={i} className="h-1" />;
              const inlined = line.replace(/\*\*(.+?)\*\*/g, "§§$1§§");
              return (
                <div key={i}>{inlined.split("§§").map((part, j) =>
                  j % 2 === 1 ? <strong key={j} className="font-semibold text-neutral-800 dark:text-neutral-100">{part}</strong> : part
                )}</div>
              );
            })}
            {loading && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-violet-400 animate-pulse rounded-sm align-text-bottom" />}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Agent controls ───────────────────────────────────────────────────────────

const EP_QUICK = [10, 25, 50, 100, 200];

function AgentCtrl() {
  const [mode, setMode]         = useState<"paper" | "live">("paper");
  const [running, setRunning]   = useState(false);
  const [model, setModel]       = useState("ensemble");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [tStatus, setTStatus]   = useState("");
  const [tProgress, setTProgress] = useState(0);
  const [nEp, setNEp]           = useState(50);
  const [showCfg, setShowCfg]   = useState(false);
  // Track whether user has manually changed config — if so, don't let poll overwrite
  const userEditedRef = useRef(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/agents/status`);
        const d = await r.json();
        const a = d.data?.[0];
        if (a) {
          setRunning(a.status === "running");
          setTStatus(a.training_status ?? "");
          setTProgress(a.training_progress ?? 0);
          // Only sync config fields from server on first load (before user touches anything)
          if (!userEditedRef.current) {
            setModel(a.model ?? "ensemble");
            setMode(a.mode ?? "paper");
            if (a.n_episodes) setNEp(a.n_episodes);
          }
        }
      } catch {}
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, []);

  const toggle = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/agents/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: running ? "stop" : "start", model, mode, n_episodes: nEp }),
      });
      if (r.ok) setRunning(!running);
      else {
        const d = await r.json();
        setError(d.detail ?? "Failed");
      }
    } catch {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  };

  const fmt = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

  return (
    <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-neutral-800 dark:text-neutral-200">Agent</h3>
        <div className="flex items-center gap-1.5">
          <span className={cn("h-2 w-2 rounded-full", running ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)] animate-pulse" : "bg-neutral-300 dark:bg-neutral-600")} />
          <span className="text-[10px] text-neutral-500 font-medium">
            {tStatus === "training" ? `Training ${tProgress}%` : running ? "Running" : "Stopped"}
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 px-3 py-2 text-[11px] text-red-600 dark:text-red-400 mb-3">{error}</div>
      )}

      {/* Paper / Live */}
      <div className="flex rounded-lg bg-neutral-100 dark:bg-neutral-800/80 p-0.5 mb-3">
        {(["paper", "live"] as const).map((m) => (
          <button key={m} onClick={() => { userEditedRef.current = true; setMode(m); }}
            className={cn("flex-1 rounded-md px-3 py-1.5 text-[11px] font-semibold transition-all",
              mode === m
                ? m === "live" ? "bg-red-500 text-white shadow-sm" : "bg-white dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100 shadow-sm"
                : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300")}>
            {m === "paper" ? "Paper" : "⚠ Live"}
          </button>
        ))}
      </div>

      {/* Model */}
      <select value={model} onChange={(e) => { userEditedRef.current = true; setModel(e.target.value); }}
        className="w-full rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-3 py-2 text-[11px] text-neutral-700 dark:text-neutral-300 mb-3 outline-none focus:border-emerald-500 font-medium">
        <option value="ensemble">Ensemble (PPO + SAC)</option>
        <option value="ppo">PPO only</option>
        <option value="sac">SAC only</option>
        <option value="ppo_lstm">PPO + LSTM</option>
        <option value="sac_lstm">SAC + LSTM</option>
      </select>

      {/* Episodes */}
      <button onClick={() => setShowCfg((v) => !v)}
        className="w-full flex items-center justify-between rounded-lg bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200/60 dark:border-neutral-700/40 px-3 py-2 mb-3 hover:border-neutral-300 dark:hover:border-neutral-600 transition-colors">
        <div className="flex items-center gap-2">
          <span className="text-[10px]">🏋</span>
          <span className="text-[11px] font-medium text-neutral-600 dark:text-neutral-400">Episodes</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{fmt(nEp)}</span>
          <span className="text-[9px] text-neutral-400">{showCfg ? "▲" : "▼"}</span>
        </div>
      </button>

      {showCfg && (
        <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/40 bg-neutral-50/50 dark:bg-neutral-800/30 p-3 mb-3">
          <div className="flex flex-wrap gap-1 mb-3">
            {EP_QUICK.map((n) => (
              <button key={n} onClick={() => { userEditedRef.current = true; setNEp(n); }}
                className={cn("rounded-md px-2.5 py-1 text-[10px] font-bold border transition-all",
                  nEp === n
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                    : "border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:border-neutral-400")}>
                {fmt(n)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input type="range" min={5} max={500} step={5} value={nEp} onChange={(e) => { userEditedRef.current = true; setNEp(Number(e.target.value)); }}
              className="flex-1 h-1.5 rounded-full appearance-none bg-neutral-200 dark:bg-neutral-700 accent-emerald-500 cursor-pointer" />
            <input type="number" min={1} max={2000} value={nEp} onChange={(e) => { userEditedRef.current = true; setNEp(Math.max(1, Number(e.target.value))); }}
              className="w-16 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-2 py-1 text-[11px] text-center font-bold outline-none focus:border-emerald-500" />
          </div>
          <p className="text-[9px] text-neutral-400 mt-2">Tip: 10–50 episodes trains in ~1–3 min on CPU.</p>
        </div>
      )}

      {/* Start / Stop */}
      <button onClick={toggle} disabled={loading || tStatus === "training"}
        className={cn(
          "w-full rounded-lg py-2.5 text-[11px] font-bold tracking-wide uppercase transition-all active:scale-[0.98]",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100",
          running
            ? "bg-red-500 text-white hover:bg-red-600 shadow-sm shadow-red-500/25 hover:shadow-red-500/40"
            : "bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600 shadow-sm shadow-emerald-500/25 hover:shadow-emerald-500/40"
        )}>
        {loading
          ? <span className="flex items-center justify-center gap-2"><span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />Processing…</span>
          : tStatus === "training"
          ? `Training ${tProgress}%`
          : running
          ? "■ Stop Agent"
          : `▶ Start · ${fmt(nEp)} ep`}
      </button>

      {tStatus === "training" && (
        <div className="mt-2">
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-800 overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300" style={{ width: `${tProgress}%` }} />
          </div>
          <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-0.5">
            <span>Training…</span><span>{tProgress}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

type SideTab = "signals" | "positions" | "sentiment" | "news" | "importance";

export default function DashboardPage() {
  const chartSymbol  = useUIStore((s) => s.chartSymbol);
  const setChart     = useUIStore((s) => s.setChartSymbol);
  const push         = useNotificationStore((s) => s.push);

  const [m,         setM]         = useState<any>(null);
  const [sigs,      setSigs]      = useState<any[]>([]);
  const [online,    setOnline]    = useState(false);
  const [equity,    setEquity]    = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [featImp,   setFeatImp]   = useState<Record<string, number>>({});
  const [regime,    setRegime]    = useState<string | null>(null);
  const [liveP,     setLiveP]     = useState<Record<string, any>>({});
  const [news,      setNews]      = useState<any[]>([]);
  const [tab,       setTab]       = useState<SideTab>("signals");
  const [symbols,   setSymbols]   = useState<string[]>([]);

  const refreshNews = async () => {
    try {
      await fetch(`${API}/sentiment/news/refresh`, { method: "POST" });
      // Re-fetch news immediately after triggering refresh
      const r = await fetch(`${API}/sentiment/news?limit=20`);
      const d = await r.json();
      setNews(d.data ?? []);
    } catch {}
  };
  const prevSigsLen  = useRef(0);
  const prevRegime   = useRef<string | null>(null);
  const chartFitRef  = useRef<(() => void) | null>(null);

  // Main polling
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [mr, tr, er, pr, fr, sr, lpr, nr] = await Promise.all([
          fetch(`${API}/portfolio/metrics`),
          fetch(`${API}/portfolio/trades`),
          fetch(`${API}/portfolio/equity`),
          fetch(`${API}/portfolio/positions`),
          fetch(`${API}/portfolio/feature_importance`),
          fetch(`${API}/market/symbols`),
          fetch(`${API}/market/live`),
          fetch(`${API}/sentiment/news?limit=20`),
        ]);
        if (!alive) return;
        setM((await mr.json()).data);
        const newSigs = (await tr.json()).data ?? [];
        setSigs(newSigs);
        setEquity((await er.json()).data ?? []);
        setPositions((await pr.json()).data ?? []);
        setFeatImp((await fr.json()).data ?? {});
        setSymbols((await sr.json()).data ?? []);
        setLiveP((await lpr.json()).data ?? {});
        setNews((await nr.json()).data ?? []);
        setOnline(true);

        if (newSigs.length > prevSigsLen.current && prevSigsLen.current > 0) {
          const newest = newSigs[newSigs.length - 1];
          if (newest)
            push({
              type: newest.action === "BUY" ? "success" : newest.action === "SELL" ? "error" : "info",
              title: `${newest.action} ${newest.symbol ?? ""}`,
              message: `$${Number(newest.price ?? 0).toFixed(2)} · ${Math.round((newest.confidence ?? 0) * 100)}% conf`,
            });
        }
        prevSigsLen.current = newSigs.length;
      } catch {
        if (!alive) return;
        setOnline(false);
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => { alive = false; clearInterval(id); };
  }, [push]);

  // Regime polling (slower)
  useEffect(() => {
    let alive = true;
    const pollRegime = async () => {
      try {
        const r = await fetch(`${API}/market/regime`);
        const d = await r.json();
        const nr = d.data?.current ?? d.data ?? null;
        if (!alive) return;
        if (nr && nr !== prevRegime.current) {
          if (prevRegime.current !== null)
            push({ type: "warning", title: "Regime Change", message: `${String(prevRegime.current).replace("_", " ")} → ${String(nr).replace("_", " ")}` });
          prevRegime.current = nr;
          setRegime(nr);
        }
      } catch {}
    };
    pollRegime();
    const id = setInterval(pollRegime, 5000);
    return () => { alive = false; clearInterval(id); };
  }, [push]);

  const SIDE_TABS: { id: SideTab; label: string; count?: number }[] = [
    { id: "signals",    label: "Signals",    count: sigs.length },
    { id: "positions",  label: "Positions",  count: positions.length },
    { id: "sentiment",  label: "Sentiment" },
    { id: "news",       label: "News",       count: news.length },
    { id: "importance", label: "Features" },
  ];

  return (
    <div className="flex flex-col min-h-full">

      {/* ── Sticky top bar: status + live tickers ──────────── */}
      <div className="sticky top-0 z-20 flex flex-wrap items-center gap-3 px-4 py-2.5 bg-white/98 dark:bg-neutral-950/98 backdrop-blur-md border-b border-neutral-200/80 dark:border-neutral-800/80 shrink-0 shadow-sm shadow-neutral-200/50 dark:shadow-neutral-900/50">
        <div className={cn("h-2 w-2 rounded-full shrink-0", online ? "bg-emerald-400 animate-pulse" : "bg-red-400")} />
        <span className="text-[11px] text-neutral-500 font-medium">{online ? "Connected" : "Offline"}</span>
        {regime && <RegimeBadge regime={regime} />}
        {Object.keys(liveP).length > 0
          ? <LiveTicker prices={liveP} />
          : (
            <div className="flex items-center gap-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200/60 dark:border-neutral-700/60 px-2.5 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-neutral-300 dark:bg-neutral-600 animate-pulse" />
              <span className="text-[9px] font-medium text-neutral-400 uppercase tracking-wider">Fetching prices…</span>
            </div>
          )
        }
      </div>

    <div className="p-4 space-y-4 bg-neutral-50/80 dark:bg-neutral-950 min-h-full">

      {/* ── KPI cards ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3">
        <MC label="Portfolio"  value={fmt$(m?.portfolio_value  ?? 1_000_000)}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>}
          change={m ? fmtPct(m.pnl_pct) : undefined} positive={(m?.pnl_pct ?? 0) >= 0}
          accent={(m?.pnl_pct ?? 0) >= 0 ? "green" : "red"}
          sub={<EquityCurve data={equity.slice(-80)} />} />
        <MC label="Sharpe"    value={fmtN(m?.sharpe_ratio ?? 0)}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>}
          change={m?.sortino_ratio != null ? `Sortino ${fmtN(m.sortino_ratio)}` : undefined}
          positive={(m?.sharpe_ratio ?? 0) >= 1}
          accent={(m?.sharpe_ratio ?? 0) >= 1 ? "green" : (m?.sharpe_ratio ?? 0) >= 0 ? "amber" : "red"} />
        <MC label="Drawdown"  value={fmtPct(Math.abs(m?.max_drawdown ?? 0))}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>}
          positive={false}
          accent={(m?.max_drawdown ?? 0) < 0.1 ? "green" : (m?.max_drawdown ?? 0) < 0.2 ? "amber" : "red"}
          sub={<DrawdownGauge current={m?.current_drawdown ?? 0} max={m?.max_drawdown ?? 0} />} />
        <MC label="Win Rate"  value={`${((m?.win_rate ?? 0) * 100).toFixed(0)}%`}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>}
          positive={(m?.win_rate ?? 0) >= 0.5}
          accent={(m?.win_rate ?? 0) >= 0.55 ? "green" : (m?.win_rate ?? 0) >= 0.45 ? "amber" : "red"} />
        <MC label="Alpha"     value={fmtPct(m?.alpha ?? 0)}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M12 2 2 19h20L12 2z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>}
          positive={(m?.alpha ?? 0) >= 0}
          accent={(m?.alpha ?? 0) >= 0 ? "green" : "red"} />
        <MC label="Beta"      value={fmtN(m?.beta ?? 1, 2)}
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M6 3v18"/><path d="M6 3h8a4 4 0 0 1 0 8H6"/><path d="M6 11h9a4 4 0 0 1 0 8H6"/></svg>}
          positive={Math.abs((m?.beta ?? 1) - 1) < 0.2}
          accent="blue" />
        <MC label="Cash"      value={fmt$(m?.cash ?? 1_000_000)}
          accent="blue"
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>} />
        <MC label="Trades"    value={String(m?.total_trades ?? 0)}
          accent="purple"
          icon={<svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m3 7 5 5-5 5"/><path d="m21 17-5-5 5-5"/><line x1="9" y1="12" x2="15" y2="12"/></svg>} />
      </div>

      {/* ── Main grid ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left 2/3 : chart + analytics */}
        <div className="lg:col-span-2 space-y-4">

          {/* Chart */}
          <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-neutral-100 dark:border-neutral-800/60">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-semibold text-neutral-700 dark:text-neutral-300">Price Chart</span>
                {liveP[chartSymbol] && (
                  <span className="text-[10px] text-sky-500 font-bold">
                    ${liveP[chartSymbol].price?.toFixed(2)} {liveP[chartSymbol].change_pct >= 0 ? "▲" : "▼"}{Math.abs(liveP[chartSymbol].change_pct ?? 0).toFixed(2)}%
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {symbols.map((s) => (
                  <button key={s} onClick={() => setChart(s)}
                    className={cn("rounded-md px-2 py-1 text-[10px] font-bold transition-all",
                      chartSymbol === s
                        ? "bg-emerald-500 text-white"
                        : "bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700")}>
                    {s}
                  </button>
                ))}
                <div className="w-px h-3.5 bg-neutral-200 dark:bg-neutral-700 mx-0.5" />
                <button
                  onClick={() => chartFitRef.current?.()}
                  title="Reset zoom"
                  className="rounded-md p-1 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-all">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
                  </svg>
                </button>
              </div>
            </div>
            <TradingChart symbol={chartSymbol} signals={sigs} fitRef={chartFitRef} />
          </div>

          {/* Risk summary row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-3 flex flex-col items-center justify-center hover:shadow-sm transition-shadow">
              <RiskMeter sharpe={m?.sharpe_ratio ?? 0} sortino={m?.sortino_ratio ?? 0} />
            </div>
            <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-3 hover:shadow-sm transition-shadow overflow-hidden relative">
              <div className={cn("absolute top-0 left-0 right-0 h-0.5", (m?.pnl_daily ?? 0) >= 0 ? "bg-emerald-500" : "bg-red-500")} />
              <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-semibold mb-2">Daily P&L</div>
              <div className={cn("text-[20px] font-bold tabular-nums", (m?.pnl_daily ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400")}>
                {(m?.pnl_daily ?? 0) >= 0 ? "+" : ""}{fmt$(m?.pnl_daily ?? 0)}
              </div>
              <div className="text-[10px] text-neutral-400 mt-1 tabular-nums">
                Cumul: <span className={cn("font-semibold", (m?.pnl_cumulative ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500")}>{(m?.pnl_cumulative ?? 0) >= 0 ? "+" : ""}{fmt$(m?.pnl_cumulative ?? 0)}</span>
              </div>
            </div>
            <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-3 hover:shadow-sm transition-shadow overflow-hidden relative">
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-sky-500" />
              <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-semibold mb-2">Volatility</div>
              <div className="text-[20px] font-bold tabular-nums text-neutral-800 dark:text-neutral-100">{fmtPct(m?.volatility ?? 0)}</div>
              <div className="text-[10px] text-neutral-400 mt-1 tabular-nums">β <span className="font-semibold text-neutral-600 dark:text-neutral-300">{fmtN(m?.beta ?? 1, 2)}</span> · α <span className={cn("font-semibold", (m?.alpha ?? 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-500")}>{fmtPct(m?.alpha ?? 0)}</span></div>
            </div>
          </div>

          {/* AI Analyst */}
          <AIAnalyst />

          {/* Trade Analytics */}
          <TradeAnalytics trades={sigs} />
        </div>

        {/* Right 1/3 : agent + side panel */}
        <div className="space-y-4">
          <AgentCtrl />

          {/* Side tabs */}
          <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 flex flex-col" style={{ minHeight: 400 }}>
            {/* Tab bar */}
            <div className="flex border-b border-neutral-100 dark:border-neutral-800/60 overflow-x-auto scrollbar-none shrink-0 p-1 gap-0.5">
              {SIDE_TABS.map(({ id, label, count }) => (
                <button key={id} onClick={() => setTab(id)}
                  className={cn(
                    "flex-1 min-w-max px-2 py-1.5 text-[10px] font-semibold whitespace-nowrap rounded-lg transition-all",
                    tab === id
                      ? "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-sm"
                      : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800/60"
                  )}>
                  {label}
                  {count != null && count > 0 && (
                    <span className={cn("ml-1 text-[8px] rounded-full px-1.5 py-0.5 tabular-nums",
                      tab === id ? "bg-white/20 dark:bg-neutral-900/20" : "bg-neutral-100 dark:bg-neutral-800"
                    )}>{count}</span>
                  )}
                </button>
              ))}
            </div>
            {/* Scrollable content — grows to fill available space */}
            <div className="flex-1 overflow-y-auto overscroll-contain scrollbar-thin p-3" style={{ maxHeight: 520 }}>
              {tab === "signals"    && (
                <div className="space-y-1.5">
                  {sigs.length === 0
                    ? <div className="text-[11px] text-neutral-400 text-center py-6">No signals yet</div>
                    : [...sigs].reverse().slice(0, 60).map((s) => <SignalRow key={s.id} s={s} />)}
                </div>
              )}
              {tab === "positions"  && <PositionsPanel positions={positions} />}
              {tab === "sentiment"  && <SentimentPanel signals={sigs} />}
              {tab === "news"       && <NewsPanel news={news} onRefresh={refreshNews} />}
              {tab === "importance" && <FeatureImportance data={featImp} />}
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
