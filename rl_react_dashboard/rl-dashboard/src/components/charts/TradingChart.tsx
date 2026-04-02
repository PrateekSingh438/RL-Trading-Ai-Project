// TradingChart — lightweight-charts candlestick with signal markers.
//
// Fix: Chart is created ONCE and updated in-place (no destroy-on-data-update).
// This preserves user zoom/scroll state across live data refreshes.

import { useEffect, useRef, useState } from "react";

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export default function TradingChart({
  symbol,
  signals = [],
  height = 380,
  fitRef,
}: {
  symbol: string;
  signals?: any[];
  height?: number;
  fitRef?: React.MutableRefObject<(() => void) | null>;
}) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const chartRef      = useRef<any>(null);
  const seriesRef     = useRef<any>(null);
  const firstLoadRef  = useRef(false);          // fit-to-content only once per symbol
  const [candles, setCandles] = useState<Candle[]>([]);
  const [error,   setError  ] = useState("");
  const [lwcReady, setLwcReady] = useState(false);

  // ── 1. Load LWC library once ──────────────────────────────────────────────
  useEffect(() => {
    if ((window as any).LightweightCharts) {
      setLwcReady(true);
      return;
    }
    const script = document.createElement("script");
    script.src =
      "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js";
    script.onload = () => setLwcReady(true);
    document.head.appendChild(script);
  }, []);

  // ── 2. Create chart once (when LWC is ready or height changes) ────────────
  useEffect(() => {
    if (!lwcReady || !containerRef.current) return;
    const LWC = (window as any).LightweightCharts;
    if (!LWC) return;

    const isDark = document.documentElement.classList.contains("dark");

    // Remove old chart if height changed
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = null;
    }

    const chart = LWC.createChart(containerRef.current, {
      autoSize: true,       // handles container resize automatically
      height,
      layout: {
        background: { type: "solid", color: isDark ? "#0a0a0a" : "#fafafa" },
        textColor: isDark ? "#737373" : "#a3a3a3",
        fontFamily: "system-ui, -apple-system, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: isDark ? "#1a1a1a" : "#f0f0f0" },
        horzLines: { color: isDark ? "#1a1a1a" : "#f0f0f0" },
      },
      crosshair: { mode: 1 },      // Normal crosshair
      rightPriceScale: { borderColor: isDark ? "#262626" : "#e5e5e5" },
      timeScale: {
        borderColor: isDark ? "#262626" : "#e5e5e5",
        timeVisible: false,
        rightOffset: 5,
        barSpacing: 6,
      },
      // Scroll and zoom are enabled by default — explicitly confirm
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: true,
        axisDoubleClickReset: true,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor:        "#22c55e",
      downColor:      "#ef4444",
      borderUpColor:  "#22c55e",
      borderDownColor:"#ef4444",
      wickUpColor:    "#22c55e",
      wickDownColor:  "#ef4444",
    });

    chartRef.current  = chart;
    seriesRef.current = candleSeries;
    firstLoadRef.current = false;

    // Expose fitContent so parent can add a "Reset zoom" button
    if (fitRef) {
      fitRef.current = () => chart.timeScale().fitContent();
    }

    return () => {
      if (fitRef) fitRef.current = null;
      chart.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, [lwcReady, height, fitRef]);

  // ── 3. Update series data WITHOUT recreating chart ────────────────────────
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    seriesRef.current.setData(candles);
    // Only fit-to-content on initial load per symbol; preserve zoom afterwards
    if (!firstLoadRef.current) {
      chartRef.current?.timeScale().fitContent();
      firstLoadRef.current = true;
    }
  }, [candles]);

  // ── 4. Update signal markers WITHOUT recreating chart ────────────────────
  useEffect(() => {
    if (!seriesRef.current || candles.length === 0) return;
    if (signals.length === 0) return;
    const base = candles[0]?.time ?? 0;
    const markers = signals
      .filter((s) => s.action === "BUY" || s.action === "SELL")
      .slice(-30)
      .map((s: any, i: number) => {
        const idx = Math.min(s.step ?? i * 5, candles.length - 1);
        return {
          time: candles[idx]?.time ?? base + idx * 86400,
          position: s.action === "BUY" ? "belowBar" : "aboveBar",
          color:     s.action === "BUY" ? "#22c55e"  : "#ef4444",
          shape:     s.action === "BUY" ? "arrowUp"  : "arrowDown",
          text: `${s.action} ${s.symbol ?? ""}`,
        };
      })
      .sort((a: any, b: any) => a.time - b.time);

    if (markers.length > 0) {
      try {
        seriesRef.current.setMarkers(markers);
      } catch {
        // series may not be ready yet on first render
      }
    }
  }, [signals, candles]);

  // ── 5. Fetch OHLCV data (symbol change resets fit-to-content) ────────────
  useEffect(() => {
    let active = true;
    firstLoadRef.current = false;   // re-fit when symbol changes

    const fetchData = async () => {
      try {
        const res  = await fetch(`http://localhost:8000/api/v1/market/history/${symbol}`);
        const json = await res.json();
        if (!active) return;
        if (json.data?.length > 0) {
          const base = new Date("2023-01-01").getTime() / 1000;
          setCandles(
            json.data.map((d: any, i: number) => ({
              time:  base + i * 86400,
              open:  d.open,
              high:  d.high,
              low:   d.low,
              close: d.close,
            })),
          );
          setError("");
        }
      } catch {
        if (active) setError("Backend offline");
      }
    };

    fetchData();
    const id = setInterval(fetchData, 15_000);
    return () => { active = false; clearInterval(id); };
  }, [symbol]);

  // ── Render ────────────────────────────────────────────────────────────────
  // Always render the container so containerRef is available for chart creation.
  // Overlay loading / error states on top using absolute positioning.
  return (
    <div className="relative" style={{ height }}>
      {/* Chart canvas target — always in DOM */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-50 dark:bg-neutral-900 z-10">
          <span className="text-xs text-neutral-500">{error} — start the backend first</span>
        </div>
      )}

      {/* Loading overlay — hide once candles arrive */}
      {!error && candles.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-50 dark:bg-neutral-900 z-10">
          <div className="flex flex-col items-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 dark:border-neutral-700 border-t-emerald-500" />
            <span className="text-xs text-neutral-400">Loading {symbol}…</span>
          </div>
        </div>
      )}
    </div>
  );
}
