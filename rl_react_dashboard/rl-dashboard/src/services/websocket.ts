// ═══════════════════════════════════════════════════════════
// WebSocket Service — Connection lifecycle, subscriptions,
// reconnection with exponential backoff
// ═══════════════════════════════════════════════════════════
//
// Event flow:
//   Client subscribes → WS sends { type: "subscribe", channel, symbols }
//   Server streams    → WS receives { type, channel, data, timestamp }
//   Client unsubs     → WS sends { type: "unsubscribe", channel }
//
// Reconnection: exponential backoff 1s → 2s → 4s → 8s → 16s → 30s max

import type { WSMessage, WSEventType, WSSubscription } from "../types";
import { getAccessToken } from "./api";

type MessageHandler = (message: WSMessage) => void;

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const MAX_RECONNECT_DELAY = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;

export class TradeWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private subscriptions: Set<string> = new Set();
  private reconnectDelay = INITIAL_RECONNECT_DELAY;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionallyClosed = false;
  private messageBuffer: Array<Record<string, unknown>> = [];

  constructor(url: string = WS_BASE) {
    this.url = url;
  }

  // ─── Connection Lifecycle ─────────────────────────────

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.intentionallyClosed = false;
    const token = getAccessToken();
    const wsUrl = token ? `${this.url}?token=${token}` : this.url;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (err) {
      console.error("[WS] Connection failed:", err);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.intentionallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
    this.subscriptions.clear();
  }

  // ─── Event Handling ───────────────────────────────────

  private handleOpen(): void {
    console.log("[WS] Connected");
    this.reconnectDelay = INITIAL_RECONNECT_DELAY;

    // Flush buffered messages
    this.messageBuffer.forEach((msg) => this.send(msg));
    this.messageBuffer = [];

    // Re-subscribe to active channels
    this.subscriptions.forEach((channel) => {
      this.send({ type: "subscribe", channel });
    });
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data);

      // Dispatch to channel-specific handlers
      const channelHandlers = this.handlers.get(message.type);
      if (channelHandlers) {
        channelHandlers.forEach((handler) => handler(message));
      }

      // Dispatch to wildcard handlers
      const wildcardHandlers = this.handlers.get("*");
      if (wildcardHandlers) {
        wildcardHandlers.forEach((handler) => handler(message));
      }
    } catch (err) {
      console.error("[WS] Failed to parse message:", err);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log(`[WS] Closed: code=${event.code} reason=${event.reason}`);
    this.ws = null;

    if (!this.intentionallyClosed) {
      this.scheduleReconnect();
    }
  }

  private handleError(event: Event): void {
    console.error("[WS] Error:", event);
  }

  // ─── Reconnection ────────────────────────────────────

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;

    const jitter = Math.random() * 1000;
    const delay = Math.min(this.reconnectDelay + jitter, MAX_RECONNECT_DELAY);

    console.log(`[WS] Reconnecting in ${Math.round(delay)}ms...`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        MAX_RECONNECT_DELAY
      );
      this.connect();
    }, delay);
  }

  // ─── Subscriptions ────────────────────────────────────

  subscribe(sub: WSSubscription): void {
    const key = sub.channel;
    this.subscriptions.add(key);

    const msg = {
      type: "subscribe" as const,
      channel: sub.channel,
      symbols: sub.symbols,
      userId: sub.userId,
    };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send(msg);
    } else {
      this.messageBuffer.push(msg);
    }
  }

  unsubscribe(channel: string): void {
    this.subscriptions.delete(channel);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({ type: "unsubscribe", channel });
    }
  }

  // ─── Handler Registration ─────────────────────────────

  on(eventType: WSEventType | "*", handler: MessageHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(eventType)?.delete(handler);
    };
  }

  off(eventType: WSEventType | "*", handler: MessageHandler): void {
    this.handlers.get(eventType)?.delete(handler);
  }

  // ─── Send ─────────────────────────────────────────────

  private send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  // ─── State ────────────────────────────────────────────

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

// Singleton instance
export const tradeSocket = new TradeWebSocket();
