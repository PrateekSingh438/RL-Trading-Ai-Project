import { useState, useEffect, useMemo, useCallback, Fragment } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

type SortKey = "timestamp" | "symbol" | "action" | "price" | "confidence" | "pnl";
type SortDir = "asc" | "desc";

const ACTION_COLORS: Record<string, string> = {
  BUY: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
  SELL: "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20",
  HOLD: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
};

const REGIME_COLORS: Record<string, string> = {
  bull: "text-emerald-500",
  bear: "text-red-500",
  sideways: "text-amber-500",
  high_volatility: "text-purple-500",
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "text-emerald-500",
  negative: "text-red-500",
  neutral: "text-neutral-400",
};

const SYMBOLS = ["ALL", "AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"];
const ACTIONS = ["ALL", "BUY", "SELL", "HOLD"];
const REGIMES = ["ALL", "bull", "bear", "sideways", "high_volatility"];

// ─── CSV Export ───────────────────────────────────────────

function exportCSV(trades: any[]) {
  const headers = [
    "Time",
    "Symbol",
    "Action",
    "Price",
    "Quantity",
    "Confidence",
    "Regime",
    "Sentiment",
    "P&L",
    "Reasoning",
  ];
  const rows = trades.map((t) => [
    new Date(t.timestamp).toISOString(),
    t.symbol ?? "",
    t.action ?? "",
    Number(t.price ?? 0).toFixed(2),
    t.quantity ?? "",
    Number(t.confidence ?? 0).toFixed(3),
    t.regime ?? "",
    t.sentiment?.overall ?? "",
    Number(t.pnl ?? 0).toFixed(2),
    `"${(t.reasoning ?? "").replace(/"/g, '""')}"`,
  ]);
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Expanded Row ─────────────────────────────────────────

function ExpandedRow({ trade }: { trade: any }) {
  return (
    <tr className="bg-neutral-50/50 dark:bg-white/[0.015]">
      <td colSpan={9} className="px-4 py-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {trade.reasoning && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-400 mb-1 font-medium">
                Reasoning
              </div>
              <div className="text-[12px] text-neutral-600 dark:text-neutral-300 leading-relaxed">
                {trade.reasoning}
              </div>
            </div>
          )}
          {trade.sentiment && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-neutral-400 mb-1 font-medium">
                Sentiment
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-[12px] font-semibold capitalize ${SENTIMENT_COLORS[trade.sentiment.overall] ?? ""}`}
                >
                  {trade.sentiment.overall}
                </span>
                <span className="text-[11px] text-neutral-400">
                  {(trade.sentiment.confidence * 100).toFixed(0)}% confidence ·{" "}
                  {trade.sentiment.sources} sources
                </span>
              </div>
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

// ─── Summary Cards ────────────────────────────────────────

function SummaryCard({
  label,
  value,
  good,
  bad,
}: {
  label: string;
  value: string;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 px-4 py-3.5">
      <div className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium mb-1.5">
        {label}
      </div>
      <div
        className={`text-[20px] font-semibold tabular-nums ${
          good
            ? "text-emerald-600 dark:text-emerald-400"
            : bad
              ? "text-red-600 dark:text-red-400"
              : "text-neutral-900 dark:text-neutral-50"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

// ─── Sort Header ──────────────────────────────────────────

function SortTh({
  col,
  label,
  sort,
  dir,
  onSort,
}: {
  col: SortKey;
  label: string;
  sort: SortKey;
  dir: SortDir;
  onSort: (k: SortKey) => void;
}) {
  const active = sort === col;
  return (
    <th
      className="px-3 py-2.5 text-left cursor-pointer select-none group"
      onClick={() => onSort(col)}
    >
      <div className="flex items-center gap-1 text-[10px] uppercase tracking-widest font-semibold text-neutral-400 dark:text-neutral-500 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors">
        {label}
        <span className={`ml-0.5 ${active ? "opacity-100" : "opacity-0 group-hover:opacity-40"}`}>
          {active && dir === "asc" ? "▲" : "▼"}
        </span>
      </div>
    </th>
  );
}

// ─── Main Page ────────────────────────────────────────────

export default function TradeHistoryPage() {
  const [trades, setTrades] = useState<any[]>([]);
  const [online, setOnline] = useState(false);
  const [loading, setLoading] = useState(true);

  const [filterSymbol, setFilterSymbol] = useState("ALL");
  const [filterAction, setFilterAction] = useState("ALL");
  const [filterRegime, setFilterRegime] = useState("ALL");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`${API}/portfolio/trades`);
        const d = await r.json();
        if (!alive) return;
        setTrades(d.data ?? []);
        setOnline(true);
      } catch {
        setOnline(false);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 8000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("desc");
      }
      setPage(1);
    },
    [sortKey]
  );

  const filtered = useMemo(() => {
    let out = [...trades];
    if (filterSymbol !== "ALL") out = out.filter((t) => t.symbol === filterSymbol);
    if (filterAction !== "ALL") out = out.filter((t) => t.action === filterAction);
    if (filterRegime !== "ALL") out = out.filter((t) => t.regime === filterRegime);
    if (search.trim()) {
      const q = search.toLowerCase();
      out = out.filter(
        (t) =>
          t.symbol?.toLowerCase().includes(q) ||
          t.action?.toLowerCase().includes(q) ||
          t.reasoning?.toLowerCase().includes(q)
      );
    }
    out.sort((a, b) => {
      let av = a[sortKey] ?? 0;
      let bv = b[sortKey] ?? 0;
      if (sortKey === "symbol" || sortKey === "action") {
        av = String(av);
        bv = String(bv);
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === "asc" ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
    return out;
  }, [trades, filterSymbol, filterAction, filterRegime, search, sortKey, sortDir]);

  const summary = useMemo(() => {
    const wins = filtered.filter((t) => (t.pnl ?? 0) > 0);
    const totalPnl = filtered.reduce((s, t) => s + (t.pnl ?? 0), 0);
    const avgConf =
      filtered.length > 0
        ? filtered.reduce((s, t) => s + (t.confidence ?? 0), 0) / filtered.length
        : 0;
    return {
      total: filtered.length,
      winRate: filtered.length > 0 ? (wins.length / filtered.length) * 100 : 0,
      totalPnl,
      avgConf,
    };
  }, [filtered]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const fTime = (ts: number) =>
    new Date(ts).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-[16px] font-bold text-neutral-800 dark:text-neutral-100 tracking-tight">
            Trade History
          </h1>
          <p className="text-[11px] text-neutral-400 mt-0.5">
            {trades.length} total trades recorded
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`h-2 w-2 rounded-full ${online ? "bg-emerald-400" : "bg-red-400 animate-pulse"}`}
          />
          <span className="text-[11px] text-neutral-400">
            {loading ? "Loading…" : online ? "Live" : "Offline"}
          </span>
          <button
            onClick={() => exportCSV(filtered)}
            disabled={filtered.length === 0}
            className="rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 px-3 py-1.5 text-[11px] font-bold tracking-wide hover:opacity-80 transition-opacity disabled:opacity-30"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <SummaryCard label="Filtered Trades" value={String(summary.total)} />
        <SummaryCard
          label="Win Rate"
          value={`${summary.winRate.toFixed(1)}%`}
          good={summary.winRate >= 50}
          bad={summary.winRate < 50 && summary.total > 0}
        />
        <SummaryCard
          label="Net P&L"
          value={
            (summary.totalPnl >= 0 ? "+$" : "-$") +
            Math.abs(summary.totalPnl).toFixed(2)
          }
          good={summary.totalPnl >= 0}
          bad={summary.totalPnl < 0}
        />
        <SummaryCard
          label="Avg Confidence"
          value={`${(summary.avgConf * 100).toFixed(1)}%`}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Search symbol, action, reasoning…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 text-[11px] text-neutral-700 dark:text-neutral-300 placeholder-neutral-400 outline-none focus:border-emerald-500 transition-colors min-w-52"
        />
        {[
          { label: "Symbol", options: SYMBOLS, val: filterSymbol, set: setFilterSymbol },
          { label: "Action", options: ACTIONS, val: filterAction, set: setFilterAction },
          { label: "Regime", options: REGIMES, val: filterRegime, set: setFilterRegime },
        ].map(({ label, options, val, set }) => (
          <select
            key={label}
            value={val}
            onChange={(e) => { set(e.target.value); setPage(1); }}
            className="rounded-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 px-2 py-1.5 text-[11px] text-neutral-700 dark:text-neutral-300 outline-none focus:border-emerald-500 transition-colors"
          >
            {options.map((o) => (
              <option key={o} value={o}>
                {label}: {o}
              </option>
            ))}
          </select>
        ))}
        {(filterSymbol !== "ALL" || filterAction !== "ALL" || filterRegime !== "ALL" || search) && (
          <button
            onClick={() => {
              setFilterSymbol("ALL");
              setFilterAction("ALL");
              setFilterRegime("ALL");
              setSearch("");
              setPage(1);
            }}
            className="text-[11px] text-neutral-400 hover:text-red-500 transition-colors px-2 py-1"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-xl bg-white dark:bg-neutral-900/80 border border-neutral-200/60 dark:border-neutral-800/60 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-[12px] text-neutral-400">
            Loading trades…
          </div>
        ) : paged.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-2">
            <span className="text-2xl opacity-20">📋</span>
            <span className="text-[12px] text-neutral-400">
              {trades.length === 0 ? "No trades yet — start the agent" : "No trades match filters"}
            </span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-neutral-200/60 dark:border-neutral-800/60 bg-neutral-50/50 dark:bg-white/[0.02]">
                <tr>
                  <SortTh col="timestamp" label="Time" sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortTh col="symbol" label="Symbol" sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortTh col="action" label="Action" sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <SortTh col="price" label="Price" sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest font-semibold text-neutral-400">
                    Qty
                  </th>
                  <SortTh col="confidence" label="Conf." sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest font-semibold text-neutral-400">
                    Regime
                  </th>
                  <SortTh col="pnl" label="P&L" sort={sortKey} dir={sortDir} onSort={handleSort} />
                  <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest font-semibold text-neutral-400">
                    Detail
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800/60">
                {paged.map((t, i) => {
                  const id = t.id || String(i);
                  const expanded = expandedId === id;
                  const pnl = t.pnl ?? 0;
                  const isPos = pnl > 0;
                  return (
                    <Fragment key={id}>
                      <tr
                        className="hover:bg-neutral-50/50 dark:hover:bg-white/[0.015] transition-colors cursor-pointer"
                        onClick={() => setExpandedId(expanded ? null : id)}
                      >
                        <td className="px-3 py-2.5 text-[11px] text-neutral-400 tabular-nums whitespace-nowrap">
                          {fTime(t.timestamp)}
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="text-[12px] font-semibold text-neutral-800 dark:text-neutral-200">
                            {t.symbol}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${ACTION_COLORS[t.action] ?? ""}`}
                          >
                            {t.action}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-[12px] text-neutral-700 dark:text-neutral-300 tabular-nums">
                          ${Number(t.price ?? 0).toFixed(2)}
                        </td>
                        <td className="px-3 py-2.5 text-[11px] text-neutral-400 tabular-nums">
                          {t.quantity ?? "—"}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <div className="h-1.5 w-12 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-emerald-500"
                                style={{
                                  width: `${((t.confidence ?? 0) * 100).toFixed(0)}%`,
                                }}
                              />
                            </div>
                            <span className="text-[10px] text-neutral-400 tabular-nums">
                              {Math.round((t.confidence ?? 0) * 100)}%
                            </span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`text-[11px] font-medium capitalize ${REGIME_COLORS[t.regime] ?? "text-neutral-400"}`}
                          >
                            {t.regime?.replace("_", " ") ?? "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`text-[12px] font-semibold tabular-nums ${
                              pnl === 0
                                ? "text-neutral-400"
                                : isPos
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-red-600 dark:text-red-400"
                            }`}
                          >
                            {pnl === 0
                              ? "—"
                              : (isPos ? "+$" : "-$") + Math.abs(pnl).toFixed(2)}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-[11px] text-neutral-400">
                          {t.reasoning || t.sentiment ? (
                            <span className="text-emerald-500">
                              {expanded ? "▲" : "▼"}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                      {expanded && <ExpandedRow trade={t} />}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pageCount > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-200/60 dark:border-neutral-800/60 bg-neutral-50/50 dark:bg-white/[0.02]">
            <span className="text-[11px] text-neutral-400">
              Showing {(page - 1) * PAGE_SIZE + 1}–
              {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
            </span>
            <div className="flex items-center gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-md px-2.5 py-1 text-[11px] font-medium text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 disabled:opacity-30 transition-colors"
              >
                ← Prev
              </button>
              {(() => {
                const maxVisible = 7;
                let start = Math.max(1, page - Math.floor(maxVisible / 2));
                const end = Math.min(pageCount, start + maxVisible - 1);
                start = Math.max(1, end - maxVisible + 1);
                return Array.from({ length: end - start + 1 }, (_, i) => {
                  const n = start + i;
                  return (
                    <button
                      key={n}
                      onClick={() => setPage(n)}
                      className={`rounded-md w-7 h-7 text-[11px] font-medium transition-colors ${
                        page === n
                          ? "bg-neutral-900 dark:bg-white text-white dark:text-neutral-900"
                          : "text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200"
                      }`}
                    >
                      {n}
                    </button>
                  );
                });
              })()}
              <button
                disabled={page === pageCount}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-md px-2.5 py-1 text-[11px] font-medium text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 disabled:opacity-30 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
