# RL Trading System

A production-grade Reinforcement Learning trading system with a PPO + SAC ensemble, live market data, real-time news sentiment, market regime detection, and an interactive React dashboard.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Backend](#backend)
  - [Setup](#backend-setup)
  - [Configuration](#configuration)
  - [Training Pipeline](#training-pipeline)
  - [Running the API Server](#running-the-api-server)
- [Frontend](#frontend)
  - [Setup](#frontend-setup)
  - [Dashboard Layout](#dashboard-layout)
- [API Reference](#api-reference)
- [RL Agents](#rl-agents)
- [Reward Function](#reward-function)
- [Risk Management](#risk-management)
- [Market Regime Detection](#market-regime-detection)
- [Sentiment Analysis](#sentiment-analysis)
- [Tech Stack](#tech-stack)

---

## Overview

This system trains RL agents to trade a portfolio of stocks, then runs them live with a real-time dashboard for monitoring, control, and decision inspection.

**What it does:**

- Trains a PPO + SAC ensemble agent on multi-asset historical data
- Streams real market prices (via yfinance, refreshed every 30 s) to the dashboard
- Fetches real financial news headlines and scores sentiment using a keyword analyser — no API key required
- Detects market regime (Bull / Bear / Sideways / High Volatility) using an HMM and adapts reward weights accordingly
- Enforces risk constraints at every step (Kelly sizing, stop-loss, drawdown halt)
- Broadcasts metrics, trade signals, prices, news, and regime changes over WebSocket
- Explains every trade decision: technical signals + sentiment + regime + agent consensus

**Default universe:** AAPL · GOOGL · MSFT · NFLX · TSLA (configurable)

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        React Dashboard                             │
│  Status bar · Live price tickers · Regime badge                    │
│  ── 8 KPI cards (Portfolio, Sharpe, Drawdown, Win Rate, …) ──────  │
│  ── Candlestick chart  ──  Agent controls  ──────────────────────  │
│  ── Risk meter  ·  Daily P&L  ·  Volatility  ────────────────────  │
│  ── Signals │ Positions │ Sentiment │ News │ Features  ──────────  │
│  ── System logs (collapsible, smart auto-scroll)  ───────────────  │
└───────────────────────────┬────────────────────────────────────────┘
                            │  HTTP REST  +  WebSocket
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                       FastAPI Server  (v4)                         │
│  /auth  /profile  /agents  /portfolio  /market  /sentiment  /ws    │
│  ── Background: live price refresh (30 s)  ──────────────────────  │
│  ── Background: live news refresh  (5 min) ──────────────────────  │
│  ── WebSocket broadcast loop (1 s)  ─────────────────────────────  │
└───────────┬──────────────────────────────────────┬─────────────────┘
            │                                      │
            ▼                                      ▼
┌────────────────────────┐            ┌─────────────────────────────┐
│   Training / Engine    │            │   Live Market Data          │
│  ┌──────────────────┐  │            │  yfinance  (prices, news)   │
│  │  EnsembleAgent   │  │            │  OHLCV cache  per symbol    │
│  │  ┌─────┐ ┌─────┐ │  │            └─────────────────────────────┘
│  │  │ PPO │ │ SAC │ │  │
│  │  └─────┘ └─────┘ │  │
│  └──────────────────┘  │
│  TradingEnvironment    │
│  ├ 14+ Indicators      │
│  ├ RegimeDetector      │
│  ├ RiskManager         │
│  └ CompositeReward v2  │
└────────────────────────┘
```

---

## Project Structure

```
rl_trading_system/
├── README.md
├── .gitignore
│
├── rl_trading_system_full/
│   └── rl-trading-system/            # Python backend
│       ├── main.py                   # Standalone training entry point
│       ├── requirements.txt
│       ├── config/
│       │   └── settings.py           # All hyperparameters (single source of truth)
│       ├── data/
│       │   ├── pipeline.py           # Data fetching, indicators, normalisation
│       │   └── indicators.py         # ATR, OBV, Ichimoku, Stochastic, VWAP
│       ├── env/
│       │   └── trading_env.py        # Gym-style multi-asset environment
│       ├── agents/
│       │   ├── networks.py           # LSTM + MLP architectures (PyTorch + NumPy)
│       │   ├── ppo_agent.py          # Proximal Policy Optimisation
│       │   ├── sac_agent.py          # Soft Actor-Critic
│       │   └── ensemble.py           # PPO + SAC combiner with optional meta-policy
│       ├── rewards/
│       │   └── composite_reward.py   # 6-component reward (v2) with regime-adaptive weights
│       ├── risk/
│       │   └── risk_manager.py       # Kelly sizing, stops, drawdown halting
│       ├── regime/
│       │   └── detector.py           # HMM-based 4-regime detector
│       ├── sentiment/
│       │   └── analyzer.py           # Live news (yfinance) + keyword VADER scorer
│       ├── evaluation/
│       │   ├── metrics.py            # Sharpe, Sortino, Calmar, alpha, beta, …
│       │   └── walk_forward.py       # Walk-forward backtesting
│       ├── training/
│       │   └── pipeline.py           # End-to-end training orchestrator
│       ├── server/
│       │   └── app.py                # FastAPI REST + WebSocket + background threads
│       ├── models/                   # Saved agent weights (auto-created)
│       └── output/                   # Dashboard JSON export (auto-created)
│
└── rl_react_dashboard/
    └── rl-dashboard/                 # React TypeScript frontend
        ├── package.json
        ├── tailwind.config.js        # Includes scrollbar-none / scrollbar-thin plugins
        ├── vite.config.ts
        └── src/
            ├── App.tsx               # Root routing + auth guard
            ├── main.tsx
            ├── types/index.ts        # TypeScript interfaces
            ├── store/index.ts        # Zustand stores
            ├── services/
            │   ├── api.ts            # Axios + JWT interceptors
            │   └── websocket.ts      # WebSocket singleton with backoff reconnect
            ├── hooks/
            │   ├── useTradeSocket.ts
            │   └── useQueries.ts
            ├── layouts/
            │   └── DashboardLayout.tsx   # Sidebar + main scroll container
            ├── pages/
            │   ├── DashboardPage.tsx     # Main trading UI (see below)
            │   ├── AnalyticsPage.tsx     # Equity curve, drawdown, win rate charts
            │   ├── TradeHistoryPage.tsx  # Sortable trade log with CSV export
            │   ├── SettingsPage.tsx      # Risk profile + reward weight tuning
            │   ├── LoginPage.tsx
            │   └── SignupPage.tsx
            └── components/
                ├── charts/TradingChart.tsx   # Lightweight Charts candlestick
                └── ui/
                    ├── ThemeProvider.tsx
                    └── Toast.tsx
```

---

## Quick Start

### 1. Backend

```bash
cd rl_trading_system_full/rl-trading-system
pip install -r requirements.txt

# Optional — PyTorch for faster training (CPU build)
pip install torch --index-url https://download.pytorch.org/whl/cpu

uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Swagger docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev
# Opens at http://localhost:5173
```

### 3. Log in

```
Email:    demo@trader.com
Password: password123
```

Or register at `/signup`.

### 4. Start the agent

In the dashboard: pick a model → set episodes (10–200 for a quick test) → click **Start**. The agent trains in the background while the dashboard streams live metrics, prices, news, and trade signals.

---

## Backend

### Backend Setup

**Python 3.9+**

```bash
pip install -r requirements.txt
```

Key dependencies:

| Package | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | REST + WebSocket server |
| `numpy` + `pandas` | Numerical computing, data frames |
| `yfinance` | Historical + live market data and news |
| `scikit-learn` | HMM, preprocessing |
| `torch` *(optional)* | GPU-accelerated RL training |

### Configuration

Everything lives in `config/settings.py`. No other file needs editing for basic customisation.

**Assets and data window:**

```python
CONFIG.data.tickers        = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"]
CONFIG.data.benchmark      = "^GSPC"           # S&P 500
CONFIG.data.start_date     = "2018-01-01"
CONFIG.data.end_date       = "2024-12-31"
CONFIG.data.train_split    = 0.80              # 80 % train / 20 % test
CONFIG.data.lookback_window = 20               # LSTM input window (days)
```

**Capital and trading rules:**

```python
CONFIG.trading.initial_capital         = 1_000_000   # $1 M
CONFIG.trading.transaction_cost        = 0.001        # 0.1 % per trade
CONFIG.trading.slippage                = 0.0005       # 0.05 %
CONFIG.trading.max_position_pct        = 0.25         # 25 % per asset
CONFIG.trading.max_leverage            = 1.0          # no margin
CONFIG.trading.stop_loss_pct           = 0.05         # 5 % stop-loss
CONFIG.trading.take_profit_pct         = 0.15         # 15 % take-profit
CONFIG.trading.max_drawdown_threshold  = 0.15         # 15 % → halt trading
```

**Reward weights:**

```python
CONFIG.reward.w1 = 0.30   # Annualised return
CONFIG.reward.w2 = 0.20   # Downside deviation penalty
CONFIG.reward.w3 = 0.15   # Differential return vs benchmark
CONFIG.reward.w4 = 0.15   # Treynor ratio
CONFIG.reward.w5 = 0.15   # Sharpe ratio          ← new in v2
CONFIG.reward.w6 = 0.05   # Portfolio entropy      ← new in v2
```

**Agent hyperparameters:**

```python
# PPO
CONFIG.ppo.learning_rate   = 3e-4
CONFIG.ppo.gamma           = 0.99
CONFIG.ppo.gae_lambda      = 0.95
CONFIG.ppo.clip_epsilon    = 0.2
CONFIG.ppo.hidden_dim      = 256
CONFIG.ppo.lstm_hidden_dim = 128

# SAC
CONFIG.sac.learning_rate   = 3e-4
CONFIG.sac.tau             = 0.005    # soft update
CONFIG.sac.alpha           = 0.2      # entropy temp
CONFIG.sac.auto_alpha      = True
CONFIG.sac.buffer_size     = 1_000_000

# Ensemble
CONFIG.ensemble.ppo_weight      = 0.5
CONFIG.ensemble.sac_weight      = 0.5
CONFIG.ensemble.use_meta_policy = False   # set True for adaptive weighting
```

### Training Pipeline

```bash
python main.py
```

Four phases run automatically:

| Phase | What happens |
|-------|-------------|
| **1 · Data** | Fetch OHLCV from Yahoo Finance (synthetic fallback); compute 14+ indicators per asset; Z-score normalise; 80/20 split |
| **2 · Train** | Run N episodes on training env; PPO batches rollout every 2048 steps; SAC updates every step after 1 000 warmup |
| **3 · Evaluate** | Deterministic policy on held-out test set; compute Sharpe, Sortino, Calmar, alpha, beta, win rate, profit factor |
| **4 · Export** | Write `output/dashboard_data.json` for the React frontend |

Sentiment validation runs every 100 steps during training (not every step) for performance.

### Running the API Server

```bash
# Development
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4
```

On startup the server spawns two background threads:

- **Live price thread** — fetches current quotes via `yfinance.download` every 30 s
- **Live news thread** — fetches real headlines via `yfinance.Ticker.news` every 5 min and scores them with a keyword sentiment analyser

---

## Frontend

### Frontend Setup

**Node.js 18+**

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev      # dev server → http://localhost:5173
npm run build    # production build → dist/
```

The frontend polls the backend every 2 s and simultaneously listens on WebSocket for push events.

To point at a different backend, edit the `API` constant at the top of [DashboardPage.tsx](rl_react_dashboard/rl-dashboard/src/pages/DashboardPage.tsx).

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ● Connected  [Bull]  ● LIVE  [AAPL $189.42 ▲0.31%]  [GOOGL …]    │
├──────────────────────────────────────┬──────────────────────────────┤
│  Portfolio  Sharpe   Drawdown  WinRate│                             │
│  Alpha      Beta     Cash      Trades│                             │
├──────────────────────────────────────┤  Agent                      │
│         Equity sparkline             │  ─ Paper / ⚠ Live           │
├──────────────────────────────────────┤  ─ Model selector           │
│  [AAPL][GOOGL][MSFT][NFLX][TSLA]    │  ─ Episodes (5–500)         │
│                                      │  ─ Start / Stop             │
│  Candlestick chart                   │  ─ Training progress bar    │
│  (BUY ▲ / SELL ▼ markers)           ├─────────────────────────────┤
│                                      │  Signals │ Positions        │
│                                      │  Sentiment│ News │ Features │
├───────────┬──────────────────────────┴─────────────────────────────┤
│ Risk meter│  Daily P&L   │  Volatility / β / α                     │
├───────────┴──────────────────────────────────────────────────────── ┤
│  System Logs   [ALL][INFO][WARN][ERROR]  [↓ jump to latest]  [▲ ▼] │
│  14:32:01  INFO  Step 42 | $1,023,400 (+$23,400) | bull | 2 trades │
└─────────────────────────────────────────────────────────────────────┘
```

**Panels:**

| Panel | Description |
|-------|-------------|
| **Live ticker** | Real-time prices with flash animation on change; global `● LIVE` badge |
| **KPI cards** | Portfolio value, Sharpe, max drawdown gauge, win rate, alpha, beta, cash, total trades |
| **Equity sparkline** | Embedded inside the Portfolio card |
| **Candlestick chart** | Lightweight Charts; symbol switcher; BUY/SELL markers; live price in header |
| **Risk meter** | Semicircle gauge mapping Sharpe → 0–100 health score |
| **Signals tab** | Latest trade signals with expandable reasoning, sentiment arrow, regime tag |
| **Positions tab** | Open positions with long/short badge, weight bar |
| **Sentiment tab** | Dominant sentiment over last 50 signals; per-symbol breakdown bar |
| **News tab** | Real headlines (`● LIVE`) or simulated (`SIM`); coloured left border by sentiment; clickable links |
| **Features tab** | Top-10 feature importance bars |
| **System logs** | Level filter; collapsible; smart auto-scroll (stays put when scrolled up; `↓` button to jump back) |

---

## API Reference

All endpoints: `/api/v1/…`

### Authentication

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/auth/login` | `{email, password}` | `{accessToken, user}` |
| POST | `/auth/signup` | `{name, email, password}` | `{accessToken, user}` |
| GET | `/auth/me` | — | `User` |
| POST | `/auth/refresh` | — | `{accessToken}` |

### Agent

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/agents/status` | — | `AgentState[]` |
| POST | `/agents/control` | `{action, model?, mode?, n_episodes?}` | `{message, state}` |

`action`: `"start"` · `"stop"`
`model`: `"ensemble"` · `"ppo"` · `"sac"` · `"ppo_lstm"` · `"sac_lstm"`
`mode`: `"paper"` · `"live"`

### Portfolio

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/portfolio/metrics` | `PortfolioMetrics` |
| GET | `/portfolio/positions` | `Position[]` |
| GET | `/portfolio/trades` | `TradeSignal[]` (last 200) |
| GET | `/portfolio/equity` | `{step, value, timestamp}[]` |
| GET | `/portfolio/feature_importance` | `{feature: weight}` |
| GET | `/portfolio/risk` | Sharpe, Sortino, VaR, drawdown, beta, alpha |

### Market Data

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/market/symbols` | `string[]` |
| GET | `/market/history/{symbol}` | `OHLCV[]` (last 500 bars) |
| GET | `/market/live` | `{symbol: {price, change, change_pct, prev_close}}` |
| GET | `/market/live/{symbol}` | Single symbol live quote |
| GET | `/market/regime` | `{current: string, timestamp: number}` |

### Sentiment

| Method | Endpoint | Query | Response |
|--------|----------|-------|----------|
| GET | `/sentiment/news` | `?ticker=AAPL&limit=30` | `NewsItem[]` |

Each `NewsItem` includes `is_live: true` when the headline was fetched from Yahoo Finance in real time (vs. `false` for simulated fallback).

### Profile

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/profile` | — | `TradingProfile` |
| PATCH | `/profile` | Partial `TradingProfile` | `TradingProfile` |

### System

| Method | Endpoint | Query | Response |
|--------|----------|-------|----------|
| GET | `/logs` | `?level=INFO&limit=100` | `LogEntry[]` |

### WebSocket

Connect to `ws://localhost:8000/ws`.

The server pushes a batch every second containing:

```jsonc
// Live metrics + agent state
{ "type": "metrics", "data": { "portfolio_value": 1023400, "sharpe_ratio": 1.42, "regime": "bull", ... } }

// Real-time price ticks
{ "type": "tick", "data": { "AAPL": { "price": 189.42, "change": 0.58, "change_pct": 0.307 }, ... } }

// Recent trade signals
{ "type": "signal", "data": [ { "action": "BUY", "symbol": "AAPL", "price": 189.42, "confidence": 0.87, ... } ] }

// Latest news headlines
{ "type": "news", "data": [ { "title": "...", "ticker": "AAPL", "sentiment": "positive", "is_live": true, ... } ] }
```

---

## RL Agents

### PPO (Proximal Policy Optimization)

Clipped surrogate objective with Generalized Advantage Estimation.

```
LSTM extractor : (lookback, obs_dim) → 128-dim embedding  (2 layers × 128 hidden)
Actor          : [256] → [64] → n_actions  (tanh output)
Critic         : [256] → [64] → 1
```

10 update epochs per rollout · batch 64 · GAE λ=0.95 · clip ε=0.2 · entropy coef 0.01

### SAC (Soft Actor-Critic)

Maximum-entropy off-policy with twin Q-networks to reduce overestimation.

```
Actor  : LSTM → [256, 256] → (μ, log σ)  ← reparameterization trick
Q1, Q2 : (obs, action) → [256, 256] → scalar
Target Q: soft update  τ = 0.005  per step
```

Replay buffer 1 M · warm-up 1 000 steps · auto-tuned entropy α

### Ensemble

```
action = ppo_weight × ppo_action + sac_weight × sac_action
```

With `use_meta_policy=True` a small MLP learns adaptive weighting from regime + recent performance.

### Observation space

| Group | Dims |
|-------|------|
| Portfolio value + cash | 2 |
| Positions | n_assets |
| Prices | n_assets |
| Technical indicators (14 per asset) | n_assets × 14 |
| Regime one-hot | 4 |
| **Total (5 assets)** | **81** |

---

## Reward Function

Composite reward v2 with six components and regime-adaptive scaling:

```
R = w₁·R_ann  −  w₂·σ_down  +  w₃·D_ret  +  w₄·T_ry  +  w₅·R_sharpe  +  w₆·H_entropy
    − drawdown_penalty
```

| Component | Symbol | Description | Default weight |
|-----------|--------|-------------|---------------|
| Annualised return | R_ann | `(∏(1+rₜ))^(252/T) − 1` | 0.30 |
| Downside deviation | σ_down | `std(min(r−rₓ, 0)) × √252` | 0.20 |
| Differential return | D_ret | `(μ_p − μ_b) / \|β\|` | 0.15 |
| Treynor ratio | T_ry | `(R_ann − Rₓ) / β` | 0.15 |
| Sharpe ratio | R_sharpe | `(μ − rₓ) / σ × √252` | 0.15 |
| Portfolio entropy | H_entropy | Shannon entropy of position weights (diversification bonus) | 0.05 |

**Regime-adaptive scaling** (automatic — no manual tuning needed):

| Regime | Return weight | Risk weight | Sharpe weight |
|--------|--------------|-------------|---------------|
| Bull | ×1.10 | ×0.90 | ×1.00 |
| Bear | ×0.80 | ×1.30 | ×1.20 |
| High Volatility | ×0.85 | ×1.20 | ×1.15 |
| Sideways | ×1.00 | ×1.00 | ×1.00 |

A **drawdown cliff penalty** kicks in above 7.5% drawdown and scales linearly to the threshold.

All components are tanh-normalised before weighting. Running statistics are maintained with Welford's online algorithm.

---

## Risk Management

Hard constraints enforced at every environment step:

| Constraint | Default | Notes |
|------------|---------|-------|
| Max position | 25% | Per asset, of total portfolio |
| Max leverage | 1.0× | No margin |
| Stop-loss | 5% | Auto-close losing positions |
| Take-profit | 15% | Auto-close winning positions |
| Max drawdown | 15% | Halts all trading until reset |
| Trade cooldown | 3 steps | Minimum gap between trades per asset |

**Position sizing** uses Kelly Criterion scaled by volatility:

```
kelly = (μ − r_f) / σ²
size  = min(kelly × capital × 0.5,  max_position_pct × capital)
```

---

## Market Regime Detection

An HMM in `regime/detector.py` classifies the market into four states using a rolling 20-day window of returns and volatility:

| Regime | Returns | Volatility | Colour |
|--------|---------|------------|--------|
| Bull | High (+) | Low | Emerald |
| Bear | Low (−) | Moderate | Red |
| Sideways | ≈ 0 | Low | Amber |
| High Volatility | Mixed | High | Purple |

The regime is:
- Included in every agent observation (4 one-hot features)
- Used to scale reward weights at each step
- Streamed to the dashboard via WebSocket on change
- Shown as an animated badge in the dashboard header

---

## Sentiment Analysis

`sentiment/analyzer.py` provides two layers:

**Live news (production)** — `LiveNewsFetcher`
- Calls `yfinance.Ticker(ticker).news` to fetch real headlines
- Scores each headline with a 50+ keyword VADER-style scorer (no API key needed)
- Caches results per-ticker for 3 minutes to avoid hammering the API
- Tags results `is_live=True`; displayed with `● LIVE` badge in the dashboard

**Simulated news (fallback)** — `NewsGenerator`
- Template-based headlines used when yfinance fetch fails or during testing
- Probability distribution skewed by current market regime (more negative headlines in Bear markets)
- Tagged `is_live=False`; displayed with `SIM` badge

**DecisionValidator** adjusts the agent's action based on sentiment confidence. Live news gets a 10% confidence boost over simulated. Strong conflicts (agent wants to buy but sentiment is strongly negative) reduce position size by up to 50%.

---

## Tech Stack

### Backend

| | Package | Role |
|-|---------|------|
| Runtime | Python 3.9+ | |
| API | FastAPI + Uvicorn | REST + WebSocket |
| Data | pandas + NumPy | Frames, maths |
| Market data | yfinance | Prices, OHLCV, news |
| ML | scikit-learn | HMM, preprocessing |
| RL (opt.) | PyTorch | Accelerated training |

### Frontend

| | Package | Role |
|-|---------|------|
| UI | React 18 + TypeScript 5 | |
| Build | Vite 5 | Dev server + bundler |
| Styling | Tailwind CSS 3 | Utility-first CSS |
| State | Zustand 5 | Client state |
| Server state | TanStack Query 5 | Caching + polling |
| Routing | React Router 6 | |
| Charts | Lightweight Charts 4 | Candlestick |
| HTTP | Axios 1.7 | JWT interceptors |

---

## Demo Credentials

```
Email:    demo@trader.com
Password: password123
```
