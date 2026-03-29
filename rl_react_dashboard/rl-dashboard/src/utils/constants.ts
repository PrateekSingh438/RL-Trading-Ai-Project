export const TICKERS = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"] as const;

export const MODELS = [
  { value: "ensemble", label: "Ensemble (PPO + SAC)" },
  { value: "ppo", label: "PPO" },
  { value: "sac", label: "SAC" },
  { value: "ppo_lstm", label: "PPO + LSTM" },
  { value: "sac_lstm", label: "SAC + LSTM" },
] as const;

export const RISK_LEVELS = [
  { value: "low", label: "Conservative", maxDD: 0.05 },
  { value: "medium", label: "Moderate", maxDD: 0.15 },
  { value: "high", label: "Aggressive", maxDD: 0.25 },
] as const;

export const DEFAULT_REWARD_WEIGHTS = {
  w1: 0.35, // Annualized return
  w2: 0.25, // Downside deviation
  w3: 0.20, // Differential return
  w4: 0.20, // Treynor ratio
} as const;
