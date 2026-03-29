# RL Trading System

A production-grade Reinforcement Learning trading system with a multi-agent ensemble (PPO + SAC), real-time risk management, market regime detection, sentiment analysis, and a live React dashboard.

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
  - [Pages](#pages)
- [API Reference](#api-reference)
- [RL Agents](#rl-agents)
- [Risk Management](#risk-management)
- [Market Regime Detection](#market-regime-detection)
- [Reward Function](#reward-function)
- [Tech Stack](#tech-stack)

---

## Overview

This system trains reinforcement learning agents to trade a portfolio of stocks, then exposes a real-time dashboard to monitor performance, control the agent, and inspect every decision. The backend runs a PPO + SAC ensemble agent against a multi-asset gym-style environment. The frontend streams live data via WebSocket and provides full control over the agent lifecycle.

**Key capabilities:**

- Multi-asset RL trading across AAPL, GOOGL, MSFT, NFLX, TSLA (configurable)
- Ensemble of PPO and SAC agents with optional meta-policy weighting
- 14 technical indicators computed per asset
- 4-regime Hidden Markov Model market state detection (Bull / Bear / Sideways / High Volatility)
- News sentiment generation and decision validation
- Per-trade explainability combining technical signals, sentiment, and regime
- Composite risk-aware reward function with four components
- Risk manager: Kelly criterion sizing, drawdown halt, stop-loss/take-profit, cooldown
- FastAPI server with JWT auth, REST endpoints, and WebSocket streaming
- React + TypeScript dashboard with live metrics, candlestick chart, and agent controls

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Dashboard                           │
│  LoginPage │ DashboardPage │ AnalyticsPage │ History │ Settings  │
│  ──────────────────────────────────────────────────────────────  │
│  TanStack Query (REST)          Zustand (client state)           │
│  WebSocket (real-time)          Lightweight Charts               │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP + WebSocket
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                              │
│  /auth  /profile  /agents  /portfolio  /market  /logs  /ws      │
└────────┬──────────────────────────────────────────┬─────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────┐               ┌────────────────────────┐
│   Training Pipeline  │               │   Market Data Cache    │
│  ┌────────────────┐  │               │  OHLCV per symbol      │
│  │ EnsembleAgent  │  │               │  yfinance / synthetic  │
│  │  ┌───┐  ┌───┐  │  │               └────────────────────────┘
│  │  │PPO│  │SAC│  │  │
│  │  └───┘  └───┘  │  │
│  └────────────────┘  │
│  TradingEnvironment  │
│  ┌──────────────────┐│
│  │ 14 Indicators    ││
│  │ Regime Detector  ││
│  │ Risk Manager     ││
│  │ Composite Reward ││
│  └──────────────────┘│
└──────────────────────┘
```

---

## Project Structure

```
rl_trading_system/
├── .gitignore
├── README.md
│
├── rl_trading_system_full/
│   └── rl-trading-system/          # Python backend
│       ├── main.py                 # Training entry point
│       ├── requirements.txt
│       ├── config/
│       │   └── settings.py         # All hyperparameters
│       ├── data/
│       │   ├── pipeline.py         # Data fetching & preprocessing
│       │   └── indicators.py       # RSI, MACD, Bollinger, ATR, etc.
│       ├── env/
│       │   └── trading_env.py      # Gym-style multi-asset environment
│       ├── agents/
│       │   ├── networks.py         # LSTM + MLP architectures
│       │   ├── ppo_agent.py        # Proximal Policy Optimization
│       │   ├── sac_agent.py        # Soft Actor-Critic
│       │   └── ensemble.py         # Ensemble combiner
│       ├── rewards/
│       │   └── composite_reward.py # 4-component reward function
│       ├── risk/
│       │   └── risk_manager.py     # Position sizing, stops, drawdown
│       ├── regime/
│       │   └── detector.py         # HMM regime detection
│       ├── sentiment/
│       │   └── analyzer.py         # News generation & sentiment
│       ├── evaluation/
│       │   ├── metrics.py          # Sharpe, Sortino, alpha, beta, etc.
│       │   └── walk_forward.py     # Backtesting
│       ├── training/
│       │   └── pipeline.py         # End-to-end training orchestrator
│       ├── server/
│       │   └── app.py              # FastAPI REST + WebSocket server
│       ├── models/                 # Saved agent weights (auto-created)
│       └── output/                 # Dashboard JSON output (auto-created)
│
└── rl_react_dashboard/
    └── rl-dashboard/               # React TypeScript frontend
        ├── package.json
        ├── tailwind.config.js
        ├── vite.config.ts
        └── src/
            ├── App.tsx             # Root routing & auth guard
            ├── main.tsx
            ├── index.css
            ├── types/index.ts      # TypeScript interfaces
            ├── store/index.ts      # Zustand stores
            ├── services/
            │   ├── api.ts          # Axios client + JWT interceptors
            │   └── websocket.ts    # WebSocket singleton
            ├── hooks/
            │   ├── useTradeSocket.ts
            │   └── useQueries.ts
            ├── layouts/
            │   └── DashboardLayout.tsx
            ├── pages/
            │   ├── DashboardPage.tsx
            │   ├── AnalyticsPage.tsx
            │   ├── TradeHistoryPage.tsx
            │   ├── SettingsPage.tsx
            │   ├── LoginPage.tsx
            │   └── SignupPage.tsx
            └── components/
                ├── charts/TradingChart.tsx
                └── ui/
                    ├── ThemeProvider.tsx
                    └── Toast.tsx
```

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd rl_trading_system
```

### 2. Start the backend API server

```bash
cd rl_trading_system_full/rl-trading-system
pip install -r requirements.txt

# Optional: PyTorch for GPU-accelerated training
pip install torch --index-url https://download.pytorch.org/whl/cpu

uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start the frontend

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev
# Opens at http://localhost:5173
```

### 4. Login

Use the built-in demo credentials:

```
Email:    demo@trader.com
Password: password123
```

Or register a new account at `/signup`.

### 5. Start the agent

In the dashboard, select a model (Ensemble / PPO / SAC), set the number of training episodes, and click **Start**. The agent trains in the backend while the dashboard streams live metrics, trade signals, and logs.

---

## Backend

### Backend Setup

**Python 3.9+ required.**

```bash
cd rl_trading_system_full/rl-trading-system
pip install -r requirements.txt
```

**Core dependencies:**

| Package | Purpose |
|---------|---------|
| `fastapi` | REST + WebSocket server |
| `uvicorn` | ASGI server |
| `pandas` | Data manipulation |
| `numpy` | Numerical computing |
| `yfinance` | Market data fetching |
| `scikit-learn` | HMM, preprocessing |
| `torch` (optional) | GPU-accelerated RL |

### Configuration

All system parameters live in `config/settings.py` as dataclasses. Edit this file to change tickers, capital, risk limits, or reward weights without touching any other code.

**Asset configuration:**

```python
# config/settings.py
CONFIG.data.tickers = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"]
CONFIG.data.benchmark = "^GSPC"
CONFIG.data.start_date = "2018-01-01"
CONFIG.data.end_date = "2023-12-31"
CONFIG.data.train_split = 0.80       # 80% train, 20% test
CONFIG.data.lookback_window = 60     # Days of history per observation
```

**Capital and trading rules:**

```python
CONFIG.trading.initial_capital = 1_000_000  # $1M
CONFIG.trading.transaction_cost = 0.001      # 0.1% per trade
CONFIG.trading.slippage = 0.0005             # 0.05% slippage
CONFIG.trading.max_position_pct = 0.25       # Max 25% per asset
CONFIG.trading.max_leverage = 1.0            # No leverage
CONFIG.trading.stop_loss_pct = 0.05          # 5% stop-loss
CONFIG.trading.take_profit_pct = 0.15        # 15% take-profit
CONFIG.trading.max_drawdown_threshold = 0.15 # 15% drawdown halts trading
```

**Reward weights (must sum to 1.0):**

```python
CONFIG.reward.w1 = 0.35   # Annualized return component
CONFIG.reward.w2 = 0.25   # Downside deviation penalty
CONFIG.reward.w3 = 0.20   # Differential return vs benchmark
CONFIG.reward.w4 = 0.20   # Treynor ratio component
```

**Agent hyperparameters:**

```python
# PPO
CONFIG.ppo.learning_rate = 3e-4
CONFIG.ppo.gamma = 0.99
CONFIG.ppo.gae_lambda = 0.95
CONFIG.ppo.clip_epsilon = 0.2
CONFIG.ppo.hidden_dim = 256
CONFIG.ppo.lstm_hidden = 128

# SAC
CONFIG.sac.learning_rate = 3e-4
CONFIG.sac.gamma = 0.99
CONFIG.sac.tau = 0.005            # Soft update rate
CONFIG.sac.alpha = 0.2            # Entropy regularization
CONFIG.sac.auto_alpha = True      # Automatic entropy tuning
CONFIG.sac.buffer_size = 1_000_000

# Ensemble
CONFIG.ensemble.ppo_weight = 0.5
CONFIG.ensemble.sac_weight = 0.5
CONFIG.ensemble.use_meta_policy = False
```

### Training Pipeline

Run the full training pipeline (data fetch → train → evaluate → export):

```bash
python main.py
```

This executes four phases:

**Phase 1 — Data Preparation**
- Fetches historical OHLCV from Yahoo Finance (falls back to synthetic data if unavailable)
- Computes 14 technical indicators per asset (RSI, MACD, Bollinger Bands, SMA 30/60, EMA 12/26, CCI, ADX, Turbulence, OBV, ATR, Ichimoku, Stochastic, Volume, Volatility)
- Z-score normalizes features
- Splits into 80% train / 20% test

**Phase 2 — Agent Training**
- Initializes `EnsembleAgent` wrapping PPO + SAC
- Runs N episodes on training data
- PPO: collects rollout buffer → batch update (10 epochs/batch, batch size 64)
- SAC: updates every step after 1000 learning starts
- Logs episode reward, Sharpe ratio, and max drawdown

**Phase 3 — Evaluation**
- Backtests deterministic policy on held-out test set
- Computes: total return, annualized return, Sharpe, Sortino, max drawdown, Calmar, alpha, beta, win rate, profit factor
- Optional walk-forward validation

**Phase 4 — Dashboard Export**
- Serializes trade history, metrics, equity curve to `output/dashboard_data.json`

### Running the API Server

```bash
# Development (auto-reload)
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4
```

The server runs on `http://localhost:8000`. API docs are available at `http://localhost:8000/docs` (Swagger UI).

---

## Frontend

### Frontend Setup

**Node.js 18+ required.**

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev          # http://localhost:5173 (dev server)
npm run build        # Production build → dist/
npm run preview      # Preview production build
```

The frontend expects the backend at `http://localhost:8000/api/v1`. To change this, update `API` in [DashboardPage.tsx](rl_react_dashboard/rl-dashboard/src/pages/DashboardPage.tsx#L12) and `API_BASE` in `src/services/api.ts`.

### Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | LoginPage | Email/password authentication |
| `/signup` | SignupPage | New user registration |
| `/dashboard` | DashboardPage | Main trading UI — metrics, chart, agent controls, signals, logs |
| `/analytics` | AnalyticsPage | Performance charts: equity curve, Sharpe/Sortino, drawdown, win rate |
| `/history` | TradeHistoryPage | Sortable/filterable trade log with CSV export |
| `/settings` | SettingsPage | Risk profile, asset class selection, reward weight tuning |

**DashboardPage layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  ● Connected   [Bull regime]           [AAPL] [GOOGL] [MSFT]... │
├────────────────────────────────────────┬─────────────────────────┤
│  Portfolio   Sharpe   Sortino   DD     │                         │
│  Win Rate    Alpha    Beta      Cash   │                         │
├────────────────────────────────────────┤                         │
│  Equity Curve (sparkline)              │                         │
├────────────────────────────────────────┤                         │
│                                        │  Agent Card             │
│  Candlestick Chart (Lightweight        │  ─ Paper / Live         │
│  Charts) with BUY/SELL markers         │  ─ Model selector       │
│                                        │  ─ Episodes config      │
│                                        │  ─ Start / Stop         │
│                                        ├─────────────────────────│
│                                        │  Signals │ Positions    │
│                                        │  Sentiment │ Importance │
├────────────────────────────────────────┴─────────────────────────┤
│  ● ● ●  logs (1234)      [ALL] [INFO] [WARN] [ERROR]             │
│  14:30:01  INFO  Training episode 42/500...                      │
└──────────────────────────────────────────────────────────────────┘
```

**Agent controls (top-right card):**

1. Toggle **Paper** (simulated) or **Live** mode
2. Select model: **Ensemble (PPO + SAC)**, PPO only, SAC only, PPO+LSTM, SAC+LSTM
3. Configure training episodes (50 → 2000, quick-select buttons or slider)
4. Click **Start** — agent trains in backend, dashboard updates in real time
5. Training progress bar appears while training; button becomes **Stop Agent** when running

---

## API Reference

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/auth/login` | `{email, password}` | `{token, user}` |
| POST | `/auth/signup` | `{name, email, password}` | `{token, user}` |
| GET | `/auth/me` | — | `User` |
| POST | `/auth/refresh` | — | `{token}` |

All protected endpoints require `Authorization: Bearer <token>`.

### Agent

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/agents/status` | — | `AgentState[]` |
| POST | `/agents/control` | `{action, model?, mode?, n_episodes?}` | `{message, state}` |

`action` values: `"start"` or `"stop"`

`model` values: `"ensemble"`, `"ppo"`, `"sac"`, `"ppo_lstm"`, `"sac_lstm"`

`mode` values: `"paper"`, `"live"`

### Portfolio

| Method | Endpoint | Query | Response |
|--------|----------|-------|----------|
| GET | `/portfolio/metrics` | — | `PortfolioMetrics` |
| GET | `/portfolio/positions` | — | `Position[]` |
| GET | `/portfolio/trades` | — | `TradeSignal[]` |
| GET | `/portfolio/equity` | — | `{step, value}[]` |
| GET | `/portfolio/feature_importance` | — | `{feature: weight}` |

### Market Data

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/market/symbols` | `string[]` |
| GET | `/market/history/{symbol}` | `OHLCV[]` |
| GET | `/market/regime` | `{current: string}` |

### System

| Method | Endpoint | Query | Response |
|--------|----------|-------|----------|
| GET | `/logs` | `?level=INFO&limit=100` | `LogEntry[]` |

### Profile

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/profile` | — | `TradingProfile` |
| PATCH | `/profile` | Partial `TradingProfile` | `TradingProfile` |

### WebSocket

Connect to `ws://localhost:8000/api/v1/ws`.

**Incoming messages (server → client):**

```json
{ "type": "signal",        "data": { "action": "BUY", "symbol": "AAPL", "price": 182.5, "confidence": 0.87, ... } }
{ "type": "tick",          "data": { "symbol": "AAPL", "price": 182.5, "volume": 12000 } }
{ "type": "metrics",       "data": { "portfolio_value": 1023400, "sharpe_ratio": 1.42, ... } }
{ "type": "log",           "data": { "level": "INFO", "message": "Episode 43 complete", "timestamp": 1234567890 } }
{ "type": "agent_status",  "data": { "status": "running", "training_progress": 43 } }
{ "type": "regime_change", "data": "bull" }
```

**Outgoing messages (client → server):**

```json
{ "type": "subscribe", "channels": ["signals", "metrics", "logs"] }
```

---

## RL Agents

### PPO (Proximal Policy Optimization)

Implements the clipped surrogate objective with Generalized Advantage Estimation.

```
Actor network:  input → [256] → [64] → n_actions  (tanh)
Critic network: input → [256] → [64] → 1
LSTM extractor: 2 layers × 128 hidden units (dropout 0.1)
```

Training parameters: 10 update epochs per rollout, batch size 64, GAE λ=0.95, clip ε=0.2, entropy coefficient 0.01.

### SAC (Soft Actor-Critic)

Entropy-regularized off-policy actor-critic with twin Q-networks.

```
Actor:    input → [256, 256] → μ, log_σ  (reparameterization trick)
Q1, Q2:  (input, action) → [256, 256] → scalar
Target Q: soft update τ=0.005 every step
```

Replay buffer capacity: 1,000,000 transitions. Training starts after 1,000 warmup steps. Entropy coefficient α auto-tuned if `auto_alpha=True`.

### Ensemble

Combines PPO and SAC outputs with configurable weighting:

```
action = ppo_weight × ppo_action + sac_weight × sac_action
```

With `use_meta_policy=True`, a small MLP learns to adaptively weight PPO vs SAC based on the current market state (regime features + recent performance).

### Neural Network Inputs

Each agent observes a vector containing:

| Feature Group | Dimensions |
|---------------|-----------|
| Portfolio value + cash | 2 |
| Current positions | n_assets |
| Current prices | n_assets |
| Technical indicators | n_assets × 14 |
| Market regime features | 4 |

With 5 assets and a 60-step lookback window, the LSTM processes a (60, 77) sequence and outputs a fixed 128-dim embedding passed to the actor/critic heads.

---

## Risk Management

The `RiskManager` enforces constraints at every environment step:

| Constraint | Default | Description |
|------------|---------|-------------|
| Max position | 25% | No single asset exceeds 25% of portfolio |
| Max leverage | 1.0× | No margin trading |
| Stop-loss | 5% | Auto-close if position loses 5% |
| Take-profit | 15% | Auto-close at 15% gain |
| Max drawdown | 15% | Halts all trading if portfolio drops 15% from peak |
| Trade cooldown | configurable | Minimum steps between trades per asset |

**Position sizing** uses the Kelly Criterion scaled by volatility:

```
kelly_fraction = (μ − r_f) / σ²
position_size = min(kelly_fraction × capital, max_position_pct × capital)
```

**Drawdown tracking** maintains a running peak value and computes:

```
current_drawdown = (peak − current_value) / peak
```

Trading is halted when `current_drawdown > max_drawdown_threshold`.

---

## Market Regime Detection

A Hidden Markov Model (`regime/detector.py`) classifies the market into 4 states using a 60-day rolling window of returns and volatility:

| Regime | Returns | Volatility | Dashboard Color |
|--------|---------|------------|-----------------|
| **Bull** | High (+) | Low | Emerald |
| **Bear** | Low (−) | Moderate | Red |
| **Sideways** | Near zero | Low | Amber |
| **High Volatility** | Mixed | High | Purple |

The current regime is:
- Appended to each agent observation (as 4 one-hot features)
- Streamed to the dashboard via WebSocket on every regime change
- Used by the `SentimentValidator` to scale position adjustments

---

## Reward Function

The composite reward (`rewards/composite_reward.py`) balances return and risk:

```
R = w₁ · R_ann  −  w₂ · σ_down  +  w₃ · D_ret  +  w₄ · T_ry
```

| Component | Symbol | Formula | Weight |
|-----------|--------|---------|--------|
| Annualized return | R_ann | `(1 + step_return)^252 − 1` | 0.35 |
| Downside deviation penalty | σ_down | `std(min(r, 0)) × √252` | 0.25 |
| Differential vs benchmark | D_ret | `portfolio_ret − benchmark_ret` | 0.20 |
| Treynor ratio | T_ry | `excess_return / beta` | 0.20 |

All four components are clipped to [−5, +5] before weighting to prevent gradient explosions. Running statistics (mean, std) are maintained for adaptive normalization across episodes.

---

## Tech Stack

### Backend

| Technology | Version | Role |
|-----------|---------|------|
| Python | 3.9+ | Runtime |
| FastAPI | latest | REST + WebSocket API |
| Uvicorn | latest | ASGI server |
| NumPy | latest | Tensor math, LSTM cells |
| pandas | latest | Data manipulation |
| yfinance | latest | Market data |
| scikit-learn | latest | HMM, preprocessing |
| PyTorch | optional | GPU-accelerated training |

### Frontend

| Technology | Version | Role |
|-----------|---------|------|
| React | 18.3 | UI framework |
| TypeScript | 5.5 | Type safety |
| Vite | 5.4 | Build tool |
| Tailwind CSS | 3.4 | Styling |
| Zustand | 5.0 | Client state management |
| TanStack Query | 5.56 | Server state + caching |
| React Router | 6.26 | Routing |
| Lightweight Charts | 4.2 | Candlestick charts |
| Axios | 1.7 | HTTP client with JWT interceptors |

---

## Demo Credentials

```
Email:    demo@trader.com
Password: password123
```

The demo account has a pre-configured trading profile with moderate risk tolerance, all five default assets enabled, and balanced reward weights.
