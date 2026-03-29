import { useState, useEffect, useMemo, memo } from "react";

const API = "http://localhost:8000/api/v1";

// ─── SVG chart helpers ────────────────────────────────────

function makePath(
  values: number[],
  w: number,
  h: number,
  pad = 8
): { line: string; area: string } {
  if (values.length < 2) return { line: "", area: "" };
  const mn = Math.min(...values);
  const mx = Math.max(...values);
  const range = mx - mn || 1;
  const pts = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (w - pad * 2);
    const y = pad + (1 - (v - mn) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const first = pts[0].split(",");
  const last = pts[pts.length - 1].split(",");
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p}`).join(" ");
  const area = `M${first[0]},${h - pad} ${line.slice(1)} L${last[0]},${h - pad} Z`;
  return { line, area };
}

// ─── Metric Card ──────────────────────────────────────────

const MetricCard = memo(function MetricCard({
  label,
  value,
  sub,
  highlight,
  bad,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  bad?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3.5 transition-all hover:shadow-sm ${
        highlight
          ? "bg-emerald-500/5 border-emerald-500/20 dark:border-emerald-500/20"
          : bad
            ? "bg-red-500/5 border-red-500/20 dark:border-red-500/20"
            : "bg-white dark:bg-neutral-900/80 border-neutral-200/60 dark:border-neutral-800/60"
      }`}
    >
      <div className="text-[10px] uppercase tracking-widest text-neutral-400 dark:text-neutral-500 font-medium mb-1.5">
        {label}
      </div>
      <div
        className={`text-[22px] font-semibold tabular-nums leading-tight ${
          highlight
            ? "text-emerald-600 dark:text-emerald-400"
            : bad
              ? "text-red-600 dark:text-red-400"
              : "text-neutral-900 dark:text-neutral-50"
        }`}
      >
        {value}
      </div>
      {sub && (
        <div className="text-[10px] text-neutral-400 mt-1">{sub}</div>
      )}
    </div>
  );
});

// ─── Equity Chart ─────────────────────────────────────────

function EquityChart({ data }: { data: { value: number }[] }) {
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center h-40 text-[11px] text-neutral-400">
        No equity data yet — start the agent to populate this chart
      </div>
    );
  }
  const vals = data.map((d) => d.value);
  const w = 800;
  const h = 160;
  const { line, area } = makePath(vals, w, h, 10);
  const isUp = vals[vals.length - 1] >= vals[0];
  const color = isUp ? "#22c55e" : "#ef4444";
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const fmt = (n: number) =>
    n >= 1e6
      ? `$${(n / 1e6).toFixed(2)}M`
      : `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

  return (
    <div className="relative">
      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-[9px] text-neutral-400 tabular-nums py-2.5 pr-1 pointer-events-none">
        <span>{fmt(mx)}</span>
        <span>{fmt((mx + mn) / 2)}</span>
        <span>{fmt(mn)}</span>
      </div>
      <div className="pl-12">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }}>
          <defs>
            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.2" />
              <stop offset="100%" stopColor={color} stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#eqGrad)" />
          <path
            d={line}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>
        <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-1">
          <span>Start</span>
          <span>
            {data.length} steps · {isUp ? "▲" : "▼"}{" "}
            {Math.abs(((vals[vals.length - 1] - vals[0]) / vals[0]) * 100).toFixed(2)}%
          </span>
          <span>Now</span>
        </div>
      </div>
    </div>
  );
}

// ─── Drawdown Chart ───────────────────────────────────────

function DrawdownChart({ equity }: { equity: { value: number }[] }) {
  const drawdowns = useMemo(() => {
    if (equity.length === 0) return [];
    let peak = equity[0].value;
    return equity.map((pt) => {
      if (pt.value > peak) peak = pt.value;
      return peak > 0 ? ((pt.value - peak) / peak) * 100 : 0;
    });
  }, [equity]);

  if (drawdowns.length < 2) {
    return (
      <div className="flex items-center justify-center h-24 text-[11px] text-neutral-400">
        Drawdown chart appears after agent starts
      </div>
    );
  }

  const w = 800;
  const h = 100;
  const pad = 8;
  const minDD = Math.min(...drawdowns);
  const range = Math.abs(minDD) || 1;
  const pts = drawdowns.map((v, i) => {
    const x = pad + (i / (drawdowns.length - 1)) * (w - pad * 2);
    // drawdowns are negative; 0 = top, minDD = bottom
    const y = pad + (Math.abs(v) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const first = pts[0].split(",");
  const last = pts[pts.length - 1].split(",");
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p}`).join(" ");
  const area = `M${first[0]},${pad} ${line.slice(1)} L${last[0]},${pad} Z`;
  const maxDD = Math.abs(minDD);

  return (
    <div className="relative">
      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-[9px] text-neutral-400 tabular-nums py-2.5 pr-1 pointer-events-none">
        <span>0%</span>
        <span>{(maxDD / 2).toFixed(1)}%</span>
        <span>{maxDD.toFixed(1)}%</span>
      </div>
      <div className="pl-12">
        <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }}>
          <defs>
            <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.02" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.25" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#ddGrad)" />
          <path
            d={line}
            fill="none"
            stroke="#ef4444"
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>
        <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-1">
          <span>Start</span>
          <span>Max: -{maxDD.toFixed(2)}%</span>
          <span>Now: {drawdowns[drawdowns.length - 1].toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}

// ─── Allocation Bars ──────────────────────────────────────

function AllocationBars({ positions }: { positions: any[] }) {
  if (positions.length === 0) {
    return (
      <div className="text-[11px] text-neutral-400 text-center py-8">
        No open positions
      </div>
    );
  }
  const total = positions.reduce((s, p) => s + Math.abs(p.weight || 0), 0) || 1;
  const colors = [
    "#22c55e",
    "#3b82f6",
    "#a855f7",
    "#f59e0b",
    "#ef4444",
    "#06b6d4",
  ];

  return (
    <div className="space-y-3">
      {positions.map((p, i) => {
        const pct = ((Math.abs(p.weight || 0) / total) * 100).toFixed(1);
        const pnl = p.unrealized_pnl ?? p.unrealizedPnl ?? 0;
        const isPos = pnl >= 0;
        return (
          <div key={p.symbol || i}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ background: colors[i % colors.length] }}
                />
                <span className="text-[12px] font-semibold text-neutral-700 dark:text-neutral-300">
                  {p.symbol}
                </span>
                <span className="text-[10px] text-neutral-400">
                  {p.shares} shares
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-[11px] font-medium tabular-nums ${isPos ? "text-emerald-500" : "text-red-500"}`}
                >
                  {isPos ? "+" : ""}
                  {pnl >= 0
                    ? `$${pnl.toFixed(2)}`
                    : `-$${Math.abs(pnl).toFixed(2)}`}
                </span>
                <span className="text-[11px] text-neutral-400 tabular-nums w-10 text-right">
                  {pct}%
                </span>
              </div>
            </div>
            <div className="h-2 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${pct}%`,
                  background: colors[i % colors.length],
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Trade Stats ──────────────────────────────────────────

function TradeStats({ trades }: { trades: any[] }) {
  const stats = useMemo(() => {
    if (trades.length === 0) return null;
    const buys = trades.filter((t) => t.action === "BUY");
    const sells = trades.filter((t) => t.action === "SELL");
    const wins = trades.filter((t) => (t.pnl ?? 0) > 0);
    const losses = trades.filter((t) => (t.pnl ?? 0) < 0);
    const pnls = trades.map((t) => t.pnl ?? 0).filter((p) => p !== 0);
    const avgWin =
      wins.length > 0
        ? wins.reduce((s, t) => s + (t.pnl ?? 0), 0) / wins.length
        : 0;
    const avgLoss =
      losses.length > 0
        ? Math.abs(losses.reduce((s, t) => s + (t.pnl ?? 0), 0) / losses.length)
        : 0;
    const totalPnl = pnls.reduce((s, p) => s + p, 0);
    const profitFactor =
      losses.length > 0 && avgLoss > 0
        ? (wins.length * avgWin) / (losses.length * avgLoss)
        : 0;
    return {
      total: trades.length,
      buys: buys.length,
      sells: sells.length,
      wins: wins.length,
      losses: losses.length,
      winRate: trades.length > 0 ? (wins.length / trades.length) * 100 : 0,
      avgWin,
      avgLoss,
      totalPnl,
      profitFactor,
    };
  }, [trades]);

  if (!stats) {
    return (
      <div className="text-[11px] text-neutral-400 text-center py-8">
        No trade data
      </div>
    );
  }

  const rows = [
    { label: "Total Trades", value: String(stats.total) },
    { label: "Buys / Sells", value: `${stats.buys} / ${stats.sells}` },
    {
      label: "Win Rate",
      value: `${stats.winRate.toFixed(1)}%`,
      good: stats.winRate >= 50,
    },
    {
      label: "Avg Win",
      value: `+$${stats.avgWin.toFixed(2)}`,
      good: true,
    },
    {
      label: "Avg Loss",
      value: `-$${stats.avgLoss.toFixed(2)}`,
      bad: true,
    },
    {
      label: "Profit Factor",
      value: stats.profitFactor.toFixed(2),
      good: stats.profitFactor > 1,
      bad: stats.profitFactor <= 1,
    },
    {
      label: "Net P&L",
      value:
        (stats.totalPnl >= 0 ? "+$" : "-$") +
        Math.abs(stats.totalPnl).toFixed(2),
      good: stats.totalPnl >= 0,
      bad: stats.totalPnl < 0,
    },
  ];

  return (
    <div className="space-y-1.5">
      {rows.map((r) => (
        <div
          key={r.label}
          className="flex items-center justify-between py-1.5 px-3 rounded-lg hover:bg-neutral-50 dark:hover:bg-white/[0.02] transition-colors"
        >
          <span className="text-[12px] text-neutral-500 dark:text-neutral-400">
            {r.label}
          </span>
          <span
            className={`text-[12px] font-semibold tabular-nums ${
              r.good
                ? "text-emerald-600 dark:text-emerald-400"
                : r.bad
                  ? "text-red-600 dark:text-red-400"
                  : "text-neutral-700 dark:text-neutral-300"
            }`}
          >
            {r.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [equity, setEquity] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [online, setOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [mr, er, pr, tr] = await Promise.all([
          fetch(`${API}/portfolio/metrics`),
          fetch(`${API}/portfolio/equity`),
          fetch(`${API}/portfolio/positions`),
          fetch(`${API}/portfolio/trades`),
        ]);
        if (!alive) return;
        setMetrics((await mr.json()).data ?? null);
        setEquity((await er.json()).data ?? []);
        setPositions((await pr.json()).data ?? []);
        setTrades((await tr.json()).data ?? []);
        setOnline(true);
      } catch {
        setOnline(false);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 10_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const v = (k1: string, k2: string, fb: number = 0) =>
    metrics ? (metrics[k1] ?? metrics[k2] ?? fb) : fb;

  const fP = (n: number, d = 2) => (n * 100).toFixed(d) + "%";
  const fN = (n: number, d = 3) => Number(n).toFixed(d);
  const fM = (n: number) =>
    (n < 0 ? "-$" : "$") +
    Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 });

  const calmar = useMemo(() => {
    const ann = v("annualized_return", "annualizedReturn");
    const mdd = Math.abs(v("max_drawdown", "maxDrawdown"));
    return mdd > 0 ? (ann / mdd).toFixed(2) : "—";
  }, [metrics]);

  const perfCards = [
    {
      label: "Portfolio Value",
      value: metrics ? fM(v("portfolio_value", "portfolioValue", 1e6)) : "—",
      sub: metrics ? `PnL: ${fM(v("pnl_cumulative", "pnlCumulative"))}` : undefined,
      highlight: metrics ? v("pnl_cumulative", "pnlCumulative") >= 0 : false,
      bad: metrics ? v("pnl_cumulative", "pnlCumulative") < 0 : false,
    },
    {
      label: "Total Return",
      value: metrics ? fP(v("pnl_pct", "pnlPct")) : "—",
      highlight: metrics ? v("pnl_pct", "pnlPct") >= 0 : false,
      bad: metrics ? v("pnl_pct", "pnlPct") < 0 : false,
    },
    {
      label: "Sharpe Ratio",
      value: metrics ? fN(v("sharpe_ratio", "sharpeRatio")) : "—",
      sub: "> 1.0 is good",
      highlight: metrics ? v("sharpe_ratio", "sharpeRatio") >= 1 : false,
    },
    {
      label: "Sortino Ratio",
      value: metrics ? fN(v("sortino_ratio", "sortinoRatio")) : "—",
      sub: "> 2.0 is excellent",
      highlight: metrics ? v("sortino_ratio", "sortinoRatio") >= 2 : false,
    },
    {
      label: "Calmar Ratio",
      value: metrics ? calmar : "—",
      sub: "Ann. Return / Max DD",
      highlight: metrics ? Number(calmar) >= 1 : false,
    },
    {
      label: "Max Drawdown",
      value: metrics ? fP(v("max_drawdown", "maxDrawdown")) : "—",
      sub: `Current: ${metrics ? fP(v("current_drawdown", "currentDrawdown")) : "—"}`,
      bad: metrics ? Math.abs(v("max_drawdown", "maxDrawdown")) > 0.1 : false,
    },
    {
      label: "Volatility",
      value: metrics ? fP(v("volatility", "volatility")) : "—",
      sub: "Annualized",
    },
    {
      label: "Alpha",
      value: metrics ? fP(v("alpha", "alpha")) : "—",
      sub: "vs benchmark",
      highlight: metrics ? v("alpha", "alpha") > 0 : false,
      bad: metrics ? v("alpha", "alpha") < 0 : false,
    },
    {
      label: "Beta",
      value: metrics ? fN(v("beta", "beta"), 3) : "—",
      sub: "Market sensitivity",
    },
    {
      label: "Win Rate",
      value: metrics ? fP(v("win_rate", "winRate")) : "—",
      sub: `${v("total_trades", "totalTrades")} total trades`,
      highlight: metrics ? v("win_rate", "winRate") >= 0.5 : false,
      bad: metrics ? v("win_rate", "winRate") < 0.5 : false,
    },
  ];

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[16px] font-bold text-neutral-800 dark:text-neutral-100 tracking-tight">
            Portfolio Analytics
          </h1>
          <p className="text-[11px] text-neutral-400 mt-0.5">
            Risk-adjusted performance metrics and portfolio breakdown
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]" : "bg-red-400 animate-pulse"}`}
          />
          <span className="text-[11px] text-neutral-400 font-medium">
            {loading ? "Loading…" : online ? "Live" : "Offline"}
          </span>
        </div>
      </div>

      {/* Performance metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {perfCards.map((c) => (
          <MetricCard key={c.label} {...c} />
        ))}
      </div>

      {/* Equity curve + Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
              Equity Curve
            </span>
            <span className="text-[10px] text-neutral-400">
              {equity.length} data points
            </span>
          </div>
          <EquityChart data={equity} />
        </div>

        <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
              Allocation
            </span>
            <span className="text-[10px] text-neutral-400">
              {positions.length} positions
            </span>
          </div>
          <AllocationBars positions={positions} />
        </div>
      </div>

      {/* Drawdown chart + Trade stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
              Drawdown
            </span>
            {metrics && (
              <span className="text-[10px] text-red-400 tabular-nums">
                Max: {fP(Math.abs(v("max_drawdown", "maxDrawdown")))}
              </span>
            )}
          </div>
          <DrawdownChart equity={equity} />
        </div>

        <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
          <div className="mb-3">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
              Trade Statistics
            </span>
          </div>
          <TradeStats trades={trades} />
        </div>
      </div>
    </div>
  );
}
