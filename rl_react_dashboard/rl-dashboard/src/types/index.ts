// ═══════════════════════════════════════════════════════════
// Core Types for RL Trading Dashboard
// ═══════════════════════════════════════════════════════════

// ─── Authentication ───────────────────────────────────────

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  createdAt: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest extends LoginRequest {
  name: string;
}

// ─── Trading Profile ──────────────────────────────────────

export type RiskTolerance = "low" | "medium" | "high";
export type AssetClass = "stocks" | "crypto" | "forex" | "commodities";
export type AgentModel = "ppo" | "sac" | "ensemble" | "ppo_lstm" | "sac_lstm";
export type TradingMode = "paper" | "live";

export interface TradingProfile {
  id: string;
  userId: string;
  riskTolerance: RiskTolerance;
  assetClasses: AssetClass[];
  selectedModel: AgentModel;
  capitalAllocation: number;
  maxDrawdown: number;
  stopLossPct: number;
  takeProfitPct: number;
  rewardWeights: {
    w1: number; // R_ann
    w2: number; // σ_down
    w3: number; // D_ret
    w4: number; // T_ry
  };
  createdAt: string;
  updatedAt: string;
}

// ─── Market Data ──────────────────────────────────────────

export interface OHLCV {
  time: number;      // Unix timestamp
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickData {
  symbol: string;
  price: number;
  volume: number;
  timestamp: number;
}

// ─── RL Agent Signals ─────────────────────────────────────

export type TradeAction = "BUY" | "SELL" | "HOLD";

export interface TradeSignal {
  id: string;
  symbol: string;
  action: TradeAction;
  confidence: number;    // 0-1
  price: number;
  quantity: number;
  timestamp: number;
  reasoning: string;     // LLM-generated explanation
  regime: MarketRegime;
  sentiment: SentimentScore;
}

export type MarketRegime = "bull" | "bear" | "sideways" | "high_volatility";

export interface SentimentScore {
  overall: "positive" | "negative" | "neutral";
  confidence: number;
  sources: number;
}

// ─── Portfolio Metrics ────────────────────────────────────

export interface PortfolioMetrics {
  portfolioValue: number;
  cash: number;
  pnlDaily: number;
  pnlCumulative: number;
  pnlPct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  currentDrawdown: number;
  winRate: number;
  totalTrades: number;
  beta: number;
  alpha: number;
  volatility: number;
  timestamp: number;
}

export interface Position {
  symbol: string;
  shares: number;
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  weight: number;  // % of portfolio
}

// ─── Agent Control ────────────────────────────────────────

export type AgentStatus = "running" | "stopped" | "paused" | "error";

export interface AgentState {
  id: string;
  model: AgentModel;
  status: AgentStatus;
  mode: TradingMode;
  uptime: number;       // seconds
  totalSignals: number;
  lastSignal?: TradeSignal;
  metrics?: PortfolioMetrics;
}

export interface AgentCommand {
  action: "start" | "stop" | "pause" | "resume" | "switch_mode";
  model?: AgentModel;
  mode?: TradingMode;
  params?: Record<string, unknown>;
}

// ─── Logs ─────────────────────────────────────────────────

export type LogLevel = "INFO" | "WARN" | "ERROR" | "DEBUG";

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  source: string;       // "agent" | "risk" | "data" | "system"
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// ─── WebSocket Events ─────────────────────────────────────

export type WSEventType =
  | "tick"
  | "signal"
  | "metrics"
  | "log"
  | "agent_status"
  | "regime_change"
  | "error";

export interface WSMessage<T = unknown> {
  type: WSEventType;
  channel: string;
  data: T;
  timestamp: number;
}

export interface WSSubscription {
  channel: string;
  symbols?: string[];
  userId?: string;
}

// ─── API Responses ────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  status: "success" | "error";
  message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  pageSize: number;
}
