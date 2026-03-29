// ═══════════════════════════════════════════════════════════
// useTradeSocket — Custom hook for real-time trade data
// ═══════════════════════════════════════════════════════════
//
// Usage:
//   const { signals, metrics, isConnected } = useTradeSocket({
//     symbols: ["AAPL", "GOOGL"],
//     onSignal: (signal) => console.log("New signal:", signal),
//   });
//
// Handles:
//   - WebSocket connection/disconnection tied to component lifecycle
//   - Channel subscriptions per user/symbol
//   - Batched state updates (avoids re-render storms on fast data)
//   - Cleanup on unmount

import { useEffect, useRef, useState, useCallback } from "react";
import { tradeSocket } from "../services/websocket";
import { useAuthStore } from "../store";
import type {
  TradeSignal,
  PortfolioMetrics,
  TickData,
  LogEntry,
  WSMessage,
  AgentState,
  MarketRegime,
} from "../types";

interface UseTradeSocketOptions {
  symbols?: string[];
  onSignal?: (signal: TradeSignal) => void;
  onMetrics?: (metrics: PortfolioMetrics) => void;
  onLog?: (log: LogEntry) => void;
  onRegimeChange?: (regime: MarketRegime) => void;
  batchInterval?: number; // ms between state updates (default: 250)
}

interface TradeSocketState {
  signals: TradeSignal[];
  metrics: PortfolioMetrics | null;
  ticks: Map<string, TickData>;
  logs: LogEntry[];
  agentStatus: AgentState | null;
  regime: MarketRegime | null;
  isConnected: boolean;
}

const MAX_SIGNALS = 200;
const MAX_LOGS = 500;
const DEFAULT_BATCH_INTERVAL = 250;

export function useTradeSocket(options: UseTradeSocketOptions = {}) {
  const {
    symbols = [],
    onSignal,
    onMetrics,
    onLog,
    onRegimeChange,
    batchInterval = DEFAULT_BATCH_INTERVAL,
  } = options;

  const user = useAuthStore((s) => s.user);

  const [state, setState] = useState<TradeSocketState>({
    signals: [],
    metrics: null,
    ticks: new Map(),
    logs: [],
    agentStatus: null,
    regime: null,
    isConnected: false,
  });

  // Use refs for batching to avoid stale closures
  const pendingUpdates = useRef<Partial<TradeSocketState>>({});
  const batchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── Batched State Update ───────────────────────────

  const flushUpdates = useCallback(() => {
    const updates = pendingUpdates.current;
    if (Object.keys(updates).length === 0) return;

    setState((prev) => {
      const next = { ...prev };

      if (updates.signals) {
        next.signals = [...updates.signals, ...prev.signals].slice(0, MAX_SIGNALS);
      }
      if (updates.metrics) next.metrics = updates.metrics;
      if (updates.ticks) next.ticks = new Map([...prev.ticks, ...updates.ticks]);
      if (updates.logs) {
        next.logs = [...updates.logs, ...prev.logs].slice(0, MAX_LOGS);
      }
      if (updates.agentStatus) next.agentStatus = updates.agentStatus;
      if (updates.regime) next.regime = updates.regime;
      if (updates.isConnected !== undefined) next.isConnected = updates.isConnected;

      return next;
    });

    pendingUpdates.current = {};
  }, []);

  const scheduleBatch = useCallback(() => {
    if (!batchTimer.current) {
      batchTimer.current = setTimeout(() => {
        batchTimer.current = null;
        flushUpdates();
      }, batchInterval);
    }
  }, [batchInterval, flushUpdates]);

  // ─── Message Handlers ─────────────────────────────────

  useEffect(() => {
    // Connect
    tradeSocket.connect();

    // Subscribe to channels
    if (symbols.length > 0) {
      tradeSocket.subscribe({
        channel: "ticks",
        symbols,
        userId: user?.id,
      });
    }
    tradeSocket.subscribe({ channel: "signals", userId: user?.id });
    tradeSocket.subscribe({ channel: "metrics", userId: user?.id });
    tradeSocket.subscribe({ channel: "logs", userId: user?.id });
    tradeSocket.subscribe({ channel: "agent_status", userId: user?.id });

    // Register handlers
    const unsubTick = tradeSocket.on("tick", (msg: WSMessage) => {
      const tick = msg.data as TickData;
      const ticks = new Map(pendingUpdates.current.ticks || []);
      ticks.set(tick.symbol, tick);
      pendingUpdates.current.ticks = ticks;
      scheduleBatch();
    });

    const unsubSignal = tradeSocket.on("signal", (msg: WSMessage) => {
      const signal = msg.data as TradeSignal;
      pendingUpdates.current.signals = [
        signal,
        ...(pendingUpdates.current.signals || []),
      ];
      onSignal?.(signal);
      scheduleBatch();
    });

    const unsubMetrics = tradeSocket.on("metrics", (msg: WSMessage) => {
      const metrics = msg.data as PortfolioMetrics;
      pendingUpdates.current.metrics = metrics;
      onMetrics?.(metrics);
      scheduleBatch();
    });

    const unsubLog = tradeSocket.on("log", (msg: WSMessage) => {
      const log = msg.data as LogEntry;
      pendingUpdates.current.logs = [
        log,
        ...(pendingUpdates.current.logs || []),
      ];
      onLog?.(log);
      scheduleBatch();
    });

    const unsubAgent = tradeSocket.on("agent_status", (msg: WSMessage) => {
      const agentStatus = msg.data as AgentState;
      pendingUpdates.current.agentStatus = agentStatus;
      scheduleBatch();
    });

    const unsubRegime = tradeSocket.on("regime_change", (msg: WSMessage) => {
      const regime = msg.data as MarketRegime;
      pendingUpdates.current.regime = regime;
      onRegimeChange?.(regime);
      scheduleBatch();
    });

    // Connection status polling
    const statusInterval = setInterval(() => {
      const connected = tradeSocket.isConnected;
      if (connected !== pendingUpdates.current.isConnected) {
        pendingUpdates.current.isConnected = connected;
        scheduleBatch();
      }
    }, 2000);

    // Cleanup
    return () => {
      unsubTick();
      unsubSignal();
      unsubMetrics();
      unsubLog();
      unsubAgent();
      unsubRegime();
      clearInterval(statusInterval);
      if (batchTimer.current) clearTimeout(batchTimer.current);

      // Unsubscribe channels
      tradeSocket.unsubscribe("ticks");
      tradeSocket.unsubscribe("signals");
      tradeSocket.unsubscribe("metrics");
      tradeSocket.unsubscribe("logs");
      tradeSocket.unsubscribe("agent_status");
    };
  }, [symbols.join(","), user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
