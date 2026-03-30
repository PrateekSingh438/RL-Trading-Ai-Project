# Risk-Aware Multi-Asset RL Trading System

A production-grade reinforcement learning trading system using a **PPO + SAC ensemble with LSTM**, featuring real-time market data, FinBERT AI sentiment analysis, Gemini-powered portfolio analysis, regime detection, and a live React dashboard.

## Architecture

```
R = w₁·R_ann − w₂·σ_down + w₃·D_ret + w₄·T_ry
```

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Dashboard                       │
│  Live Prices · KPI Cards · Charts · AI Analyst · Logs   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────┐
│              FastAPI Backend  (server/app.py)            │
│  /portfolio  /market  /sentiment  /agents  /analysis     │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
  RL Agent   yfinance   FinBERT     Gemini
  PPO+SAC    Live Px    Sentiment   AI Analysis
  Ensemble   + Sim      Analysis    (free tier)
```

## Folder Structure

```
rl-trading-system/
│
├── main.py                      # Entry point — runs full pipeline
├── .env                         # API keys (never commit this)
│
├── config/
│   └── settings.py              # All hyperparameters, asset lists, reward weights
│
├── data/
│   └── pipeline.py              # yfinance fetching, 14 technical indicators,
│                                #   turbulence index, normalization, sliding windows
│
├── env/
│   └── trading_env.py           # Gym-style multi-asset trading environment
│                                #   (observation space, action execution, transaction costs)
│
├── agents/
│   ├── networks.py              # LSTM cells, Actor-Critic, Q-Network
│   ├── ppo_agent.py             # PPO with GAE, clipped surrogate, rollout buffer
│   ├── sac_agent.py             # SAC with twin Q-nets, auto entropy, replay memory
│   └── ensemble.py              # Weighted PPO+SAC ensemble, meta-policy, adaptive weights
│
├── rewards/
│   └── composite_reward.py      # Composite reward: R_ann, σ_down, D_ret, T_ry
│
├── risk/
│   └── risk_manager.py          # Kelly/volatility sizing, drawdown halt,
│                                #   stop-loss/take-profit, cooldown, risk parity
│
├── regime/
│   └── detector.py              # HMM + rule-based regime detection
│                                #   (Bull, Bear, Sideways, High Volatility)
│
├── sentiment/
│   └── analyzer.py              # FinBERT AI sentiment (ProsusAI/finbert),
│                                #   live news fetcher, trade explainer
│                                #   falls back to keyword scoring if FinBERT absent
│
├── evaluation/
│   └── metrics.py               # Sharpe, Sortino, max drawdown, alpha, beta,
│                                #   win rate, Calmar, profit factor, walk-forward backtest
│
├── training/
│   └── pipeline.py              # End-to-end orchestrator: data → train → eval
│
├── server/
│   └── app.py                   # FastAPI server — all REST endpoints + WebSocket
│
├── models/                      # Saved model weights (auto-created)
├── output/                      # Dashboard JSON data (auto-created)
│
├── requirements.txt
├── SETUP.md
├── .gitignore
└── README.md
```

## Quick Start

### Backend

```bash
cd rl-trading-system

# 1. Install dependencies
pip install -r requirements.txt

# 2. Install PyTorch (CPU) for FinBERT sentiment
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 3. Add your free Gemini API key (get one at aistudio.google.com)
#    Edit .env and set:
#    GEMINI_API_KEY=AIza...

# 4. Start the API server
python -m uvicorn server.app:app --reload --port 8000
```

### Frontend (React Dashboard)

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev
# Open http://localhost:5173
```

## Key Features

| Feature | Details |
|---|---|
| **RL Agents** | PPO (stable) + SAC (exploratory) ensemble with LSTM backbone |
| **Reward Function** | Composite: annualized return, downside deviation, differential return, Treynor ratio |
| **Risk Management** | Kelly sizing, volatility sizing, max drawdown halt, stop-loss, take-profit, cooldown |
| **Regime Detection** | HMM + rule-based: bull / bear / sideways / high-volatility |
| **AI Sentiment** | FinBERT (`ProsusAI/finbert`) — real probability scores, falls back to keyword scoring |
| **Live Prices** | yfinance per-ticker fast_info, simulated seed while market is closed |
| **AI Portfolio Analyst** | Gemini 2.0 Flash (free tier) — streaming natural language portfolio report |
| **Dashboard** | React + Vite + Tailwind — live KPIs, candlestick chart, signals, news, logs |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/portfolio/metrics` | Portfolio KPIs (value, Sharpe, drawdown, …) |
| GET | `/api/v1/portfolio/equity` | Equity curve history |
| GET | `/api/v1/portfolio/positions` | Open positions |
| GET | `/api/v1/portfolio/trades` | Trade signals |
| GET | `/api/v1/portfolio/analysis` | Streaming Gemini AI portfolio report |
| GET | `/api/v1/market/live` | Live prices (yfinance) |
| GET | `/api/v1/market/regime` | Current market regime |
| GET | `/api/v1/market/symbols` | Tracked tickers |
| GET | `/api/v1/sentiment/news` | Live news with FinBERT sentiment |
| GET | `/api/v1/sentiment/status` | FinBERT model status |
| POST | `/api/v1/agents/control` | Start / stop the RL agent |
| GET | `/api/v1/agents/status` | Agent running status + training progress |
| WS | `/ws` | Real-time WebSocket stream |

## Configuration

All parameters are in `config/settings.py`:

```python
from config.settings import CONFIG

# Assets
CONFIG.data.tickers = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"]

# Reward weights
CONFIG.reward.w1 = 0.40  # Annualized return
CONFIG.reward.w2 = 0.30  # Downside penalty
CONFIG.reward.w3 = 0.15  # Differential return
CONFIG.reward.w4 = 0.15  # Treynor ratio

# Risk constraints
CONFIG.trading.max_drawdown_threshold = 0.15  # 15% halt
CONFIG.trading.stop_loss_pct           = 0.05  # 5% stop loss
CONFIG.trading.take_profit_pct         = 0.15  # 15% take profit
CONFIG.trading.transaction_cost        = 0.001 # 0.1%
```

## Environment Variables (.env)

```
GEMINI_API_KEY=AIza...   # Free key from aistudio.google.com
```

## License

MIT
