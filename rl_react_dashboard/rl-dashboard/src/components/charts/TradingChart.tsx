// Place at: src/components/charts/TradingChart.tsx
//
// Lightweight Charts candlestick with trade signal markers.
// Fetches OHLCV from backend and updates in real-time.

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
}: {
  symbol: string;
  signals?: any[];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [error, setError] = useState("");

  // Fetch candle data from backend
  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/market/history/${symbol}`,
        );
        const json = await res.json();
        if (!active) return;
        if (json.data && json.data.length > 0) {
          // Convert step index to date-like timestamps
          const base = new Date("2023-01-01").getTime() / 1000;
          const mapped = json.data.map((d: any, i: number) => ({
            time: base + i * 86400,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          }));
          setCandles(mapped);
          setError("");
        }
      } catch {
        setError("Backend offline");
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [symbol]);

  // Create / update chart
  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    const loadChart = async () => {
      // Dynamic import — lightweight-charts loaded from CDN via importmap or bundled
      let LWC: any;
      if ((window as any).LightweightCharts) {
        LWC = (window as any).LightweightCharts;
      } else {
        // Load from CDN
        await new Promise<void>((resolve) => {
          const script = document.createElement("script");
          script.src =
            "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js";
          script.onload = () => resolve();
          document.head.appendChild(script);
        });
        LWC = (window as any).LightweightCharts;
      }

      if (!LWC || !containerRef.current) return;

      // Detect dark mode
      const isDark = document.documentElement.classList.contains("dark");

      // Destroy previous chart
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }

      const chart = LWC.createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height,
        layout: {
          background: { type: "solid", color: isDark ? "#0a0a0a" : "#fafafa" },
          textColor: isDark ? "#737373" : "#a3a3a3",
          fontFamily: "DM Sans, system-ui, sans-serif",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: isDark ? "#1a1a1a" : "#f0f0f0" },
          horzLines: { color: isDark ? "#1a1a1a" : "#f0f0f0" },
        },
        crosshair: { mode: 0 },
        rightPriceScale: {
          borderColor: isDark ? "#262626" : "#e5e5e5",
        },
        timeScale: {
          borderColor: isDark ? "#262626" : "#e5e5e5",
          timeVisible: false,
        },
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      candleSeries.setData(candles);

      // Add signal markers
      if (signals.length > 0) {
        const base = candles[0]?.time || 0;
        const markers = signals
          .filter((s) => s.action === "BUY" || s.action === "SELL")
          .slice(-30)
          .map((s: any, i: number) => {
            const idx = Math.min(s.step || i * 5, candles.length - 1);
            return {
              time: candles[idx]?.time || base + idx * 86400,
              position: s.action === "BUY" ? "belowBar" : "aboveBar",
              color: s.action === "BUY" ? "#22c55e" : "#ef4444",
              shape: s.action === "BUY" ? "arrowUp" : "arrowDown",
              text: `${s.action} ${s.symbol || ""}`,
            };
          })
          .sort((a: any, b: any) => a.time - b.time);

        if (markers.length > 0) {
          candleSeries.setMarkers(markers);
        }
      }

      chart.timeScale().fitContent();
      chartRef.current = chart;
      seriesRef.current = candleSeries;

      // Resize observer
      const ro = new ResizeObserver(() => {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({
            width: containerRef.current.clientWidth,
          });
        }
      });
      ro.observe(containerRef.current);

      return () => ro.disconnect();
    };

    loadChart();

    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [candles, signals, height]);

  if (error) {
    return (
      <div
        className="flex items-center justify-center rounded-lg bg-neutral-900 dark:bg-neutral-900 border border-neutral-800 dark:border-neutral-800"
        style={{ height }}
      >
        <span className="text-xs text-neutral-500">
          {error} — start the backend first
        </span>
      </div>
    );
  }

  if (candles.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800"
        style={{ height }}
      >
        <div className="flex flex-col items-center gap-2">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 dark:border-neutral-700 border-t-emerald-500" />
          <span className="text-xs text-neutral-400">
            Loading {symbol} data...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="rounded-lg overflow-hidden border border-neutral-200 dark:border-neutral-800"
      style={{ height }}
    />
  );
}
