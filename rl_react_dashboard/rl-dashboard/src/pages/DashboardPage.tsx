import {
  useState,
  useMemo,
  memo,
  useEffect,
  useRef,
} from "react";
import { useUIStore } from "../store";
import { useNotificationStore } from "../store";
import TradingChart from "../components/charts/TradingChart";

const API = "http://localhost:8000/api/v1";

// ─── Metric Card ──────────────────────────────────────────

const MC = memo(function MC({
  label,
  value,
  change,
  positive,
  icon,
  sub,
}: {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
  icon?: string;
  sub?: React.ReactNode;
}) {
  return (
    <div className="group rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 px-4 py-3.5 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all duration-200 hover:shadow-sm">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] uppercase tracking-widest text-neutral-400 dark:text-neutral-500 font-medium">
          {label}
        </span>
        {icon && <span className="text-xs opacity-30">{icon}</span>}
      </div>
      <div className="text-[22px] font-semibold text-neutral-900 dark:text-neutral-50 tabular-nums leading-tight">
        {value}
      </div>
      {change && (
        <div
          className={`text-[11px] mt-1 tabular-nums font-medium ${positive ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}
        >
          {positive ? "▲" : "▼"} {change}
        </div>
      )}
      {sub && <div className="mt-1">{sub}</div>}
    </div>
  );
});

// ─── Regime Badge ─────────────────────────────────────────

const REGIME_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; dot: string }
> = {
  bull: {
    label: "Bull",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/25",
    dot: "bg-emerald-400",
  },
  bear: {
    label: "Bear",
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-500/10 border-red-500/25",
    dot: "bg-red-400",
  },
  sideways: {
    label: "Sideways",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/25",
    dot: "bg-amber-400",
  },
  high_volatility: {
    label: "High Vol",
    color: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/25",
    dot: "bg-purple-400",
  },
};

function RegimeBadge({ regime }: { regime: string | null }) {
  if (!regime) return null;
  const cfg = REGIME_CONFIG[regime] ?? REGIME_CONFIG.sideways;
  return (
    <div
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${cfg.bg}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${cfg.dot}`} />
      <span className={`text-[10px] font-bold uppercase tracking-wider ${cfg.color}`}>
        {cfg.label}
      </span>
    </div>
  );
}

// ─── Price Tick ───────────────────────────────────────────

function PriceTick({
  symbol,
  price,
  prev,
}: {
  symbol: string;
  price: number | null;
  prev: number | null;
}) {
  const change = price && prev && prev > 0 ? ((price - prev) / prev) * 100 : null;
  const up = change !== null ? change >= 0 : null;
  return (
    <div className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60">
      <span className="text-[10px] font-bold text-neutral-500 dark:text-neutral-400">
        {symbol}
      </span>
      {price !== null ? (
        <>
          <span className="text-[11px] font-semibold tabular-nums text-neutral-800 dark:text-neutral-200">
            ${price.toFixed(2)}
          </span>
          {change !== null && (
            <span
              className={`text-[10px] font-medium tabular-nums ${
                up ? "text-emerald-500" : "text-red-500"
              }`}
            >
              {up ? "▲" : "▼"} {Math.abs(change).toFixed(2)}%
            </span>
          )}
        </>
      ) : (
        <span className="text-[10px] text-neutral-300 dark:text-neutral-700">—</span>
      )}
    </div>
  );
}

// ─── Signal Row ───────────────────────────────────────────

function SR({ s }: { s: any }) {
  const [open, setOpen] = useState(false);
  const c: Record<string, string> = {
    BUY: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/8",
    SELL: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/8",
    HOLD: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/8",
  };
  const dc: Record<string, string> = {
    BUY: "bg-emerald-500",
    SELL: "bg-red-500",
    HOLD: "bg-amber-500",
  };
  const sentColor: Record<string, string> = {
    positive: "text-emerald-500",
    negative: "text-red-500",
    neutral: "text-neutral-400",
  };

  return (
    <div>
      <div
        className={`flex items-center gap-3 rounded-lg px-3 py-2 cursor-pointer transition-opacity hover:opacity-90 ${c[s.action] || c.HOLD}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${dc[s.action] || dc.HOLD} shrink-0`}
        />
        <div className="flex-1 min-w-0 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold">{s.action}</span>
            <span className="text-[11px] font-semibold opacity-80">{s.symbol}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] tabular-nums opacity-70">
            <span>${Number(s.price || 0).toFixed(2)}</span>
            <span>{Math.round((s.confidence || 0.5) * 100)}%</span>
            {s.sentiment?.overall && (
              <span
                className={`font-semibold ${sentColor[s.sentiment.overall] ?? ""}`}
              >
                {s.sentiment.overall === "positive"
                  ? "↑"
                  : s.sentiment.overall === "negative"
                    ? "↓"
                    : "~"}
              </span>
            )}
          </div>
        </div>
        <span className="text-[9px] opacity-40">{open ? "▲" : "▼"}</span>
      </div>
      {open && s.reasoning && (
        <div className="mx-1 mb-1 px-3 py-2 rounded-b-lg bg-neutral-50 dark:bg-neutral-800/60 border-x border-b border-neutral-200/60 dark:border-neutral-700/40">
          <p className="text-[10px] text-neutral-500 dark:text-neutral-400 leading-relaxed">
            {s.reasoning}
          </p>
          {s.regime && (
            <span
              className={`inline-block mt-1 text-[9px] font-semibold uppercase tracking-wider ${
                REGIME_CONFIG[s.regime]?.color ?? "text-neutral-400"
              }`}
            >
              {s.regime.replace("_", " ")} regime
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Sentiment Summary ────────────────────────────────────

function SentimentPanel({ signals }: { signals: any[] }) {
  const stats = useMemo(() => {
    const recent = signals.slice(-30);
    if (recent.length === 0) return null;
    const counts = { positive: 0, negative: 0, neutral: 0 };
    let totalConf = 0;
    for (const s of recent) {
      const o = s.sentiment?.overall ?? "neutral";
      counts[o as keyof typeof counts] = (counts[o as keyof typeof counts] || 0) + 1;
      totalConf += s.sentiment?.confidence ?? 0;
    }
    const dom = (Object.entries(counts) as [string, number][]).sort(
      (a, b) => b[1] - a[1]
    )[0][0];
    return {
      counts,
      total: recent.length,
      avgConf: totalConf / recent.length,
      dominant: dom,
    };
  }, [signals]);

  const bySymbol = useMemo(() => {
    const map: Record<string, { pos: number; neg: number; neu: number; count: number }> =
      {};
    for (const s of signals.slice(-50)) {
      const sym = s.symbol;
      const o = s.sentiment?.overall ?? "neutral";
      if (!map[sym]) map[sym] = { pos: 0, neg: 0, neu: 0, count: 0 };
      if (o === "positive") map[sym].pos++;
      else if (o === "negative") map[sym].neg++;
      else map[sym].neu++;
      map[sym].count++;
    }
    return Object.entries(map).slice(0, 5);
  }, [signals]);

  if (!stats) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2">
        <span className="text-2xl opacity-20">📰</span>
        <span className="text-[11px] text-neutral-400">
          Sentiment data appears after agent starts
        </span>
      </div>
    );
  }

  const domColors: Record<string, string> = {
    positive: "text-emerald-600 dark:text-emerald-400",
    negative: "text-red-600 dark:text-red-400",
    neutral: "text-neutral-500 dark:text-neutral-400",
  };
  const barColors: Record<string, string> = {
    positive: "bg-emerald-500",
    negative: "bg-red-500",
    neutral: "bg-neutral-400",
  };

  return (
    <div className="space-y-4">
      {/* Overall */}
      <div className="rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-3 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium">
            Overall (last 30 signals)
          </span>
          <span className="text-[10px] text-neutral-400 tabular-nums">
            {(stats.avgConf * 100).toFixed(0)}% avg conf
          </span>
        </div>
        <div
          className={`text-[15px] font-bold capitalize mb-2 ${domColors[stats.dominant]}`}
        >
          {stats.dominant}
        </div>
        <div className="flex gap-1 h-2 rounded-full overflow-hidden">
          {(["positive", "negative", "neutral"] as const).map((k) => {
            const pct = (stats.counts[k] / stats.total) * 100;
            return pct > 0 ? (
              <div
                key={k}
                className={`h-full ${barColors[k]}`}
                style={{ width: `${pct.toFixed(1)}%` }}
              />
            ) : null;
          })}
        </div>
        <div className="flex justify-between mt-1 text-[9px] text-neutral-400 tabular-nums">
          <span>+{stats.counts.positive}</span>
          <span>~{stats.counts.neutral}</span>
          <span>-{stats.counts.negative}</span>
        </div>
      </div>

      {/* By symbol */}
      {bySymbol.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium">
            By Symbol
          </div>
          {bySymbol.map(([sym, d]) => {
            const total = d.count || 1;
            const posPct = (d.pos / total) * 100;
            const negPct = (d.neg / total) * 100;
            return (
              <div key={sym}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300">
                    {sym}
                  </span>
                  <span className="text-[9px] text-neutral-400">{d.count} signals</span>
                </div>
                <div className="flex gap-0.5 h-1.5 rounded-full overflow-hidden bg-neutral-100 dark:bg-neutral-800">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${posPct.toFixed(1)}%` }}
                  />
                  <div
                    className="h-full bg-red-500"
                    style={{ width: `${negPct.toFixed(1)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Equity Sparkline ─────────────────────────────────────

function EquityCurve({ data }: { data: { value: number }[] }) {
  if (data.length < 2)
    return (
      <div className="text-[11px] text-neutral-400 text-center py-6">
        Equity curve appears after agent starts
      </div>
    );
  const vals = data.map((d) => d.value);
  const mn = Math.min(...vals),
    mx = Math.max(...vals),
    range = mx - mn || 1;
  const w = 600,
    h = 80;
  const pts = vals
    .map(
      (v, i) =>
        `${((i / (vals.length - 1)) * w).toFixed(1)},${(h - ((v - mn) / range) * (h - 8) - 4).toFixed(1)}`,
    )
    .join(" ");
  const color = vals[vals.length - 1] >= vals[0] ? "#22c55e" : "#ef4444";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: 80 }}>
      <defs>
        <linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.15" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill="url(#eqG)" />
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Feature Importance ───────────────────────────────────

function FeatureImportance({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).slice(0, 8);
  if (entries.length === 0)
    return (
      <div className="text-[11px] text-neutral-400 text-center py-4">
        Feature importance computed after 30 steps
      </div>
    );
  const mx = Math.max(...entries.map((e) => e[1]));
  return (
    <div className="space-y-1.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2">
          <span className="text-[10px] text-neutral-500 w-10 text-right tabular-nums font-mono truncate">
            {k}
          </span>
          <div className="flex-1 h-3 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${((v / mx) * 100).toFixed(0)}%` }}
            />
          </div>
          <span className="text-[9px] text-neutral-400 tabular-nums w-8">
            {(v * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Log Line ─────────────────────────────────────────────

function LL({ l }: { l: any }) {
  const c: Record<string, string> = {
    INFO: "text-sky-600 dark:text-sky-400",
    WARN: "text-amber-600 dark:text-amber-400",
    ERROR: "text-red-600 dark:text-red-400",
    DEBUG: "text-neutral-400",
  };
  const t = new Date(l.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return (
    <div className="flex gap-2 text-[11px] font-mono leading-6 px-3 hover:bg-neutral-100/50 dark:hover:bg-white/[0.02]">
      <span className="text-neutral-300 dark:text-neutral-700 tabular-nums shrink-0 select-none">
        {t}
      </span>
      <span className={`shrink-0 w-11 font-semibold ${c[l.level] || ""}`}>
        {l.level}
      </span>
      <span className="text-neutral-600 dark:text-neutral-400 break-all">
        {l.message}
      </span>
    </div>
  );
}

// ─── Agent Controls ───────────────────────────────────────

const EPISODE_QUICK = [50, 100, 250, 500, 1000];

function AgentCtrl() {
  const [mode, setMode] = useState<"paper" | "live">("paper");
  const [running, setRunning] = useState(false);
  const [model, setModel] = useState("ensemble");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tStatus, setTStatus] = useState("");
  const [tProgress, setTProgress] = useState(0);
  const [nEpisodes, setNEpisodes] = useState(500);
  const [showTrainCfg, setShowTrainCfg] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/agents/status`);
        const d = await r.json();
        if (d.data?.[0]) {
          const a = d.data[0];
          setRunning(a.status === "running");
          setModel(a.model || "ensemble");
          setMode(a.mode || "paper");
          setTStatus(a.training_status || "");
          setTProgress(a.training_progress || 0);
          if (a.n_episodes) setNEpisodes(a.n_episodes);
        }
      } catch {}
    };
    poll();
    const i = setInterval(poll, 2000);
    return () => clearInterval(i);
  }, []);

  const toggle = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/agents/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: running ? "stop" : "start",
          model,
          mode,
          n_episodes: nEpisodes,
        }),
      });
      if (r.ok) setRunning(!running);
      else {
        const d = await r.json();
        setError(d.detail || "Failed");
      }
    } catch {
      setError("Backend offline");
    } finally {
      setLoading(false);
    }
  };

  const fmtEp = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n));

  return (
    <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-neutral-800 dark:text-neutral-200">
          Agent
        </h3>
        <div className="flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${running ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)] animate-pulse" : "bg-neutral-300 dark:bg-neutral-600"}`}
          />
          <span className="text-[10px] text-neutral-500 font-medium">
            {tStatus === "training"
              ? `Training ${tProgress}%`
              : running
                ? "Running"
                : "Stopped"}
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 px-3 py-2 text-[11px] text-red-600 dark:text-red-400 mb-3">
          {error}
        </div>
      )}

      {/* Mode */}
      <div className="flex rounded-lg bg-neutral-100 dark:bg-neutral-800/80 p-0.5 mb-3">
        {(["paper", "live"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 rounded-md px-3 py-1.5 text-[11px] font-semibold transition-all ${mode === m ? (m === "live" ? "bg-red-500 text-white shadow-sm" : "bg-white dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100 shadow-sm") : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"}`}
          >
            {m === "paper" ? "Paper" : "⚠ Live"}
          </button>
        ))}
      </div>

      {/* Model */}
      <select
        value={model}
        onChange={(e) => setModel(e.target.value)}
        className="w-full rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-3 py-2 text-[11px] text-neutral-700 dark:text-neutral-300 mb-3 outline-none focus:border-emerald-500 font-medium"
      >
        <option value="ensemble">Ensemble (PPO + SAC)</option>
        <option value="ppo">PPO only</option>
        <option value="sac">SAC only</option>
        <option value="ppo_lstm">PPO + LSTM</option>
        <option value="sac_lstm">SAC + LSTM</option>
      </select>

      {/* Episodes config toggle */}
      <button
        onClick={() => setShowTrainCfg((v) => !v)}
        className="w-full flex items-center justify-between rounded-lg bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200/60 dark:border-neutral-700/40 px-3 py-2 mb-3 transition-colors hover:border-neutral-300 dark:hover:border-neutral-600"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px]">🏋</span>
          <span className="text-[11px] font-medium text-neutral-600 dark:text-neutral-400">
            Training episodes
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {fmtEp(nEpisodes)}
          </span>
          <span className="text-[9px] text-neutral-400">{showTrainCfg ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Episodes expanded panel */}
      {showTrainCfg && (
        <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/40 bg-neutral-50/50 dark:bg-neutral-800/30 p-3 mb-3">
          <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-semibold mb-2">
            Quick select
          </div>
          <div className="flex flex-wrap gap-1 mb-3">
            {EPISODE_QUICK.map((n) => (
              <button
                key={n}
                onClick={() => setNEpisodes(n)}
                className={`rounded-md px-2 py-1 text-[10px] font-bold border transition-all ${
                  nEpisodes === n
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                    : "border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:border-neutral-400"
                }`}
              >
                {fmtEp(n)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={50}
              max={2000}
              step={50}
              value={nEpisodes}
              onChange={(e) => setNEpisodes(Number(e.target.value))}
              className="flex-1 h-1.5 rounded-full appearance-none bg-neutral-200 dark:bg-neutral-700 accent-emerald-500 cursor-pointer"
            />
            <input
              type="number"
              min={1}
              max={10000}
              value={nEpisodes}
              onChange={(e) =>
                setNEpisodes(Math.max(1, Number(e.target.value)))
              }
              className="w-16 rounded-md bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-2 py-1 text-[11px] text-center font-bold text-neutral-700 dark:text-neutral-300 outline-none focus:border-emerald-500"
            />
          </div>
        </div>
      )}

      {/* Start/Stop button */}
      <button
        onClick={toggle}
        disabled={loading || tStatus === "training"}
        className={`w-full rounded-lg py-2.5 text-[11px] font-bold tracking-wide uppercase transition-all disabled:opacity-40 ${running ? "bg-red-500 text-white hover:bg-red-600 shadow-sm shadow-red-500/20" : "bg-emerald-500 text-white hover:bg-emerald-600 shadow-sm shadow-emerald-500/20"}`}
      >
        {loading
          ? "•••"
          : tStatus === "training"
            ? `Training ${tProgress}%`
            : running
              ? "Stop Agent"
              : `Start · ${fmtEp(nEpisodes)} episodes`}
      </button>

      {/* Training progress bar */}
      {tStatus === "training" && (
        <div className="mt-2">
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
              style={{ width: `${tProgress}%` }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-neutral-400 tabular-nums mt-0.5">
            <span>Training…</span>
            <span>{tProgress}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Drawdown Indicator ───────────────────────────────────

function DrawdownBar({
  current,
  max,
}: {
  current: number;
  max: number;
}) {
  const pct = max !== 0 ? Math.min(Math.abs(current) / Math.abs(max), 1) * 100 : 0;
  const color =
    pct < 40 ? "bg-emerald-500" : pct < 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="mt-1.5">
      <div className="h-1 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct.toFixed(0)}%` }}
        />
      </div>
      <div className="flex justify-between text-[8px] text-neutral-400 tabular-nums mt-0.5">
        <span>Current: {(Math.abs(current) * 100).toFixed(1)}%</span>
        <span>Max: {(Math.abs(max) * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────

export default function DashboardPage() {
  const logFilter = useUIStore((s) => s.logFilter);
  const setLogFilter = useUIStore((s) => s.setLogFilter);
  const chartSymbol = useUIStore((s) => s.chartSymbol);
  const setChartSymbol = useUIStore((s) => s.setChartSymbol);
  const push = useNotificationStore((s) => s.push);

  const [m, setM] = useState<any>(null);
  const [sigs, setSigs] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [online, setOnline] = useState(false);
  const [equity, setEquity] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [featImp, setFeatImp] = useState<Record<string, number>>({});
  const [regime, setRegime] = useState<string | null>(null);
  const [tab, setTab] = useState<
    "signals" | "positions" | "sentiment" | "importance"
  >("signals");
  const logEnd = useRef<HTMLDivElement>(null);
  const prevSigsLen = useRef(0);
  const prevRegime = useRef<string | null>(null);

  // Derive latest price per symbol from signals
  const priceTicks = useMemo(() => {
    const latest: Record<string, { price: number; prev: number | null }> = {};
    for (const s of sigs) {
      const sym = s.symbol;
      if (!sym) continue;
      if (!latest[sym]) {
        latest[sym] = { price: s.price, prev: null };
      } else {
        latest[sym] = { price: s.price, prev: latest[sym].price };
      }
    }
    return latest;
  }, [sigs]);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const [mr, tr, lr, er, pr, fr] = await Promise.all([
          fetch(`${API}/portfolio/metrics`),
          fetch(`${API}/portfolio/trades`),
          fetch(`${API}/logs?limit=100`),
          fetch(`${API}/portfolio/equity`),
          fetch(`${API}/portfolio/positions`),
          fetch(`${API}/portfolio/feature_importance`),
        ]);
        if (!alive) return;
        setM((await mr.json()).data);
        const newSigs = (await tr.json()).data || [];
        setSigs(newSigs);
        setLogs(((await lr.json()).data || []).reverse());
        setEquity((await er.json()).data || []);
        setPositions((await pr.json()).data || []);
        setFeatImp((await fr.json()).data || {});
        setOnline(true);

        // Notify on new trade signals
        if (newSigs.length > prevSigsLen.current && prevSigsLen.current > 0) {
          const newest = newSigs[newSigs.length - 1];
          if (newest) {
            push({
              type: newest.action === "BUY" ? "success" : newest.action === "SELL" ? "error" : "info",
              title: `${newest.action} ${newest.symbol ?? ""}`,
              message: `$${Number(newest.price ?? 0).toFixed(2)} · ${Math.round((newest.confidence ?? 0) * 100)}% confidence`,
            });
          }
        }
        prevSigsLen.current = newSigs.length;
      } catch {
        if (!alive) return;
        setOnline(false);
      }
    };
    poll();
    const i = setInterval(poll, 1500);
    return () => {
      alive = false;
      clearInterval(i);
    };
  }, [push]);

  // Poll regime separately (slower)
  useEffect(() => {
    let alive = true;
    const pollRegime = async () => {
      try {
        const r = await fetch(`${API}/market/regime`);
        const d = await r.json();
        const newRegime = d.data?.current ?? d.data ?? null;
        if (!alive) return;
        if (newRegime && newRegime !== prevRegime.current) {
          if (prevRegime.current !== null) {
            push({
              type: "warning",
              title: "Regime Change",
              message: `${(prevRegime.current ?? "").replace("_", " ")} → ${String(newRegime).replace("_", " ")}`,
            });
          }
          prevRegime.current = newRegime;
          setRegime(newRegime);
        }
      } catch {}
    };
    pollRegime();
    const i = setInterval(pollRegime, 30_000);
    return () => {
      alive = false;
      clearInterval(i);
    };
  }, [push]);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  const v = (k1: string, k2: string, fb: any = 0) =>
    m ? (m[k1] ?? m[k2] ?? fb) : fb;
  const fM = (n: number) =>
    (n < 0 ? "-$" : "$") +
    Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const fP = (n: number) => (n * 100).toFixed(2) + "%";
  const fLogs = useMemo(
    () =>
      logFilter === "ALL"
        ? logs
        : logs.filter((l: any) => l.level === logFilter),
    [logs, logFilter],
  );

  const SYM = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"];

  return (
    <div className="flex flex-col gap-3 p-3 sm:p-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className={`h-2.5 w-2.5 rounded-full ${online ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]" : "bg-red-400 animate-pulse"}`}
          />
          <span className="text-[12px] text-neutral-500 font-medium">
            {online ? "Connected" : "Offline"}
          </span>
          {regime && <RegimeBadge regime={regime} />}
        </div>
        <div className="flex gap-1 flex-wrap">
          {SYM.map((s) => (
            <button
              key={s}
              onClick={() => setChartSymbol(s)}
              className={`rounded-md px-2.5 py-1 text-[10px] font-bold tracking-wide transition-all ${chartSymbol === s ? "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 shadow-sm" : "text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Price ticks */}
      {Object.keys(priceTicks).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {SYM.filter((s) => priceTicks[s]).map((s) => (
            <PriceTick
              key={s}
              symbol={s}
              price={priceTicks[s]?.price ?? null}
              prev={priceTicks[s]?.prev ?? null}
            />
          ))}
        </div>
      )}

      {/* Metrics — row 1: core */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <MC
          icon="💰"
          label="Portfolio"
          value={m ? fM(v("portfolio_value", "portfolioValue", 1e6)) : "$1,000,000"}
          change={m ? fP(v("pnl_pct", "pnlPct")) : undefined}
          positive={m ? v("pnl_pct", "pnlPct") >= 0 : true}
        />
        <MC
          icon="📊"
          label="Daily P&L"
          value={m ? fM(v("pnl_daily", "pnlDaily")) : "$0"}
          positive={m ? v("pnl_daily", "pnlDaily") >= 0 : true}
        />
        <MC
          icon="⚡"
          label="Sharpe"
          value={m ? Number(v("sharpe_ratio", "sharpeRatio")).toFixed(3) : "—"}
        />
        <MC
          icon="🛡"
          label="Sortino"
          value={m ? Number(v("sortino_ratio", "sortinoRatio")).toFixed(3) : "—"}
        />
        <MC
          icon="📉"
          label="Max DD"
          value={m ? fP(v("max_drawdown", "maxDrawdown")) : "—"}
          sub={
            m ? (
              <DrawdownBar
                current={v("current_drawdown", "currentDrawdown")}
                max={v("max_drawdown", "maxDrawdown")}
              />
            ) : undefined
          }
        />
        <MC
          icon="🎯"
          label="Win Rate"
          value={m ? fP(v("win_rate", "winRate")) : "—"}
          change={m ? `${v("total_trades", "totalTrades")} trades` : undefined}
          positive
        />
      </div>

      {/* Metrics — row 2: risk/alpha */}
      {m && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <MC
            icon="α"
            label="Alpha"
            value={fP(v("alpha", "alpha"))}
            positive={v("alpha", "alpha") >= 0}
          />
          <MC
            icon="β"
            label="Beta"
            value={Number(v("beta", "beta")).toFixed(3)}
          />
          <MC
            icon="σ"
            label="Volatility"
            value={fP(v("volatility", "volatility"))}
          />
          <MC
            icon="💵"
            label="Cash"
            value={fM(v("cash", "cash"))}
          />
          <MC
            icon="📈"
            label="Cum P&L"
            value={fM(v("pnl_cumulative", "pnlCumulative"))}
            positive={v("pnl_cumulative", "pnlCumulative") >= 0}
          />
          <MC
            icon="🔢"
            label="Cur DD"
            value={fP(Math.abs(v("current_drawdown", "currentDrawdown")))}
          />
        </div>
      )}

      {/* Equity Curve */}
      <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
            Equity curve
          </span>
          {equity.length > 0 && (
            <span className="text-[10px] text-neutral-400 tabular-nums">
              {equity.length} steps
            </span>
          )}
        </div>
        <EquityCurve data={equity} />
      </div>

      {/* Chart + Right Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2">
          <TradingChart symbol={chartSymbol} signals={sigs} height={400} />
        </div>
        <div className="flex flex-col gap-3">
          <AgentCtrl />
          {/* Tabbed panel */}
          <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 flex-1 overflow-hidden flex flex-col min-h-[180px]">
            <div className="flex border-b border-neutral-200/60 dark:border-neutral-800/60 overflow-x-auto">
              {(
                ["signals", "positions", "sentiment", "importance"] as const
              ).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`flex-1 py-2 text-[10px] font-semibold capitalize whitespace-nowrap px-1 transition-colors ${tab === t ? "text-neutral-800 dark:text-neutral-200 border-b-2 border-emerald-500" : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"}`}
                >
                  {t}
                  {t === "signals" && sigs.length > 0 && (
                    <span className="ml-1 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 px-1 text-[8px]">
                      {sigs.length}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              {tab === "signals" &&
                (sigs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2">
                    <span className="text-2xl opacity-20">📡</span>
                    <span className="text-[11px] text-neutral-400">
                      Start the agent
                    </span>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {sigs
                      .slice(-20)
                      .reverse()
                      .map((s: any, i: number) => (
                        <SR key={s.id || i} s={s} />
                      ))}
                  </div>
                ))}
              {tab === "positions" &&
                (positions.length === 0 ? (
                  <div className="text-[11px] text-neutral-400 text-center py-6">
                    No open positions
                  </div>
                ) : (
                  <div className="space-y-1">
                    {positions.map((p: any, i: number) => {
                      const pnl = p.unrealized_pnl ?? p.unrealizedPnl ?? 0;
                      const isPos = pnl >= 0;
                      return (
                        <div
                          key={i}
                          className="flex items-center justify-between rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-3 py-2"
                        >
                          <div>
                            <div className="text-[12px] font-semibold text-neutral-800 dark:text-neutral-200">
                              {p.symbol}
                            </div>
                            <div className="text-[10px] text-neutral-400">
                              {p.shares} shares · avg ${Number(p.avg_entry_price ?? p.avgEntryPrice ?? 0).toFixed(2)}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-[12px] tabular-nums text-neutral-700 dark:text-neutral-300">
                              ${Number(p.current_price ?? p.currentPrice ?? 0).toFixed(2)}
                            </div>
                            <div
                              className={`text-[10px] tabular-nums font-medium ${isPos ? "text-emerald-500" : "text-red-500"}`}
                            >
                              {isPos ? "+" : ""}
                              {pnl >= 0
                                ? `$${pnl.toFixed(2)}`
                                : `-$${Math.abs(pnl).toFixed(2)}`}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              {tab === "sentiment" && (
                <SentimentPanel signals={sigs} />
              )}
              {tab === "importance" && <FeatureImportance data={featImp} />}
            </div>
          </div>
        </div>
      </div>

      {/* Logs */}
      <div className="rounded-xl bg-neutral-50 dark:bg-[#0c0c0c] border border-neutral-200/60 dark:border-neutral-800/60 min-h-[150px] max-h-[220px] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-200/60 dark:border-neutral-800/60 bg-neutral-100/50 dark:bg-neutral-900/50">
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/60" />
            </div>
            <span className="text-[10px] font-mono text-neutral-400 ml-1">
              logs ({logs.length})
            </span>
          </div>
          <div className="flex gap-0.5">
            {(["ALL", "INFO", "WARN", "ERROR"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLogFilter(l)}
                className={`rounded-md px-2 py-0.5 text-[9px] font-bold tracking-wide ${logFilter === l ? "bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300" : "text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"}`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {fLogs.length === 0 ? (
            <div className="text-[11px] text-neutral-300 dark:text-neutral-700 text-center py-6 font-mono">
              ░░░ waiting ░░░
            </div>
          ) : (
            <>
              {fLogs.slice(0, 80).map((l: any, i: number) => (
                <LL key={l.id || i} l={l} />
              ))}
              <div ref={logEnd} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
