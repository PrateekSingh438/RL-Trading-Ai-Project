# Risk-Aware Multi-Asset RL Trading System

A production-grade Reinforcement Learning trading system using a **PPO + SAC ensemble with LSTM**, featuring real-time market data, FinBERT AI sentiment analysis, Groq-powered portfolio analysis, regime detection, and a live React dashboard.

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
- [AI Portfolio Analyst](#ai-portfolio-analyst)
- [Tech Stack](#tech-stack)

---

## Overview

This system trains RL agents to trade a portfolio of stocks, then runs them live with a real-time dashboard for monitoring, control, and decision inspection.

**What it does:**

- Trains a PPO + SAC ensemble agent on multi-asset historical data
- Streams real market prices (via yfinance, refreshed every 30 s) to the dashboard
- Fetches real financial news headlines and scores sentiment using **FinBERT** (`ProsusAI/finbert`) — a transformer model fine-tuned on financial text
- Detects market regime (Bull / Bear / Sideways / High Volatility) using an HMM and adapts reward weights accordingly
- Enforces risk constraints at every step (Kelly sizing, stop-loss, drawdown halt)
- Broadcasts metrics, trade signals, prices, news, and regime changes over WebSocket
- Explains every trade decision: technical signals + sentiment + regime + agent consensus
- Provides an **AI Portfolio Analyst** panel powered by Groq (Llama 3.1, free tier) for streaming natural-language portfolio reports

**Default universe:** AAPL · GOOGL · MSFT · NFLX · TSLA (configurable)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React Dashboard                             │
│  Sticky ticker bar · Regime badge · Live/Sim price badges           │
│  ── 8 KPI cards (Portfolio, Sharpe, Drawdown, Win Rate, …) ──────   │
│  ── Candlestick chart  ──  Agent controls  ──────────────────────   │
│  ── Risk meter  ·  Daily P&L  ·  Volatility  ────────────────────   │
│  ── AI Portfolio Analyst (Groq streaming)  ───────────────────────  │
│  ── Trade Analytics (win rate bars, streak, avg return)  ─────────  │
│  ── Signals │ Positions │ Sentiment │ News │ Features  ──────────   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │  HTTP REST  +  WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI Server  (v4)                          │
│  /auth  /agents  /portfolio  /market  /sentiment  /ws               │
│  ── Background: live price refresh (30 s, per-ticker fast_info) ──  │
│  ── Background: live news + FinBERT scoring (60 s)  ─────────────   │
│  ── WebSocket broadcast loop (1 s)  ─────────────────────────────   │
└──────────┬───────────────────────────────────┬──────────────────────┘
           │                                   │
           ▼                                   ▼
┌─────────────────────┐          ┌─────────────────────────────────┐
│  Training / Engine  │          │  External Services               │
│  EnsembleAgent      │          │  yfinance  — prices + news       │
│  ├ PPO (stable)     │          │  FinBERT   — AI sentiment        │
│  ├ SAC (exploratory)│          │  Groq      — portfolio analysis  │
│  TradingEnvironment │          └─────────────────────────────────┘
│  ├ 14+ Indicators   │
│  ├ RegimeDetector   │
│  ├ RiskManager      │
│  └ CompositeReward  │
└─────────────────────┘
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
│       ├── SETUP.md                  # Step-by-step setup guide
│       ├── .env                      # API keys (gitignored)
│       ├── config/
│       │   └── settings.py           # All hyperparameters (single source of truth)
│       ├── data/
│       │   ├── pipeline.py           # Data fetching, indicators, normalisation
│       │   └── indicators.py         # ATR, OBV, Ichimoku, Stochastic, VWAP
│       ├── env/
│       │   └── trading_env.py        # Gym-style multi-asset environment
│       ├── agents/
│       │   ├── networks.py           # LSTM + MLP architectures
│       │   ├── ppo_agent.py          # Proximal Policy Optimisation
│       │   ├── sac_agent.py          # Soft Actor-Critic
│       │   └── ensemble.py           # PPO + SAC combiner with meta-policy
│       ├── rewards/
│       │   └── composite_reward.py   # 6-component reward with regime-adaptive weights
│       ├── risk/
│       │   └── risk_manager.py       # Kelly sizing, stops, drawdown halting
│       ├── regime/
│       │   └── detector.py           # HMM-based 4-regime detector
│       ├── sentiment/
│       │   └── analyzer.py           # FinBERT AI sentiment + live news fetcher
│       ├── evaluation/
│       │   └── metrics.py            # Sharpe, Sortino, Calmar, alpha, beta, …
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
        ├── tailwind.config.js
        ├── vite.config.ts
        └── src/
            ├── App.tsx               # Root routing + auth guard
            ├── store/index.ts        # Zustand stores
            ├── services/
            │   ├── api.ts            # Axios + JWT interceptors
            │   └── websocket.ts      # WebSocket singleton with backoff reconnect
            ├── pages/
            │   ├── DashboardPage.tsx # Main trading UI (all panels + AI analyst)
            │   ├── AnalyticsPage.tsx
            │   ├── TradeHistoryPage.tsx
            │   ├── SettingsPage.tsx
            │   ├── LoginPage.tsx
            │   └── SignupPage.tsx
            └── components/
                └── charts/TradingChart.tsx   # Lightweight Charts candlestick
```

---

## Quick Start

### 1. Backend

```bash
cd rl_trading_system_full/rl-trading-system

# Install dependencies
pip install -r requirements.txt

# PyTorch for FinBERT sentiment (CPU build)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Add your free Groq API key (get one at console.groq.com)
# Edit .env:  GROQ_API_KEY=gsk_...

# Start the server
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

### 4. Start the agent

Pick a model → set episodes → click **Start**. The agent trains in the background while the dashboard streams live metrics, prices, news, and signals.

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
| `numpy` + `pandas` | Numerical computing |
| `yfinance` | Historical + live market data and news |
| `transformers` | FinBERT AI sentiment model |
| `torch` *(recommended)* | FinBERT inference + GPU-accelerated training |
| `groq` | Groq AI portfolio analyst (free tier) |
| `python-dotenv` | Load API keys from `.env` |

### Environment Variables

Create `rl_trading_system_full/rl-trading-system/.env`:

```
GROQ_API_KEY=gsk_...   # Free key from console.groq.com
```

### Configuration

Everything lives in `config/settings.py`.

**Assets and data window:**

```python
CONFIG.data.tickers         = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"]
CONFIG.data.benchmark       = "^GSPC"
CONFIG.data.start_date      = "2018-01-01"
CONFIG.data.end_date        = "2024-12-31"
CONFIG.data.train_split     = 0.80
CONFIG.data.lookback_window = 20
```

**Capital and trading rules:**

```python
CONFIG.trading.initial_capital         = 1_000_000
CONFIG.trading.transaction_cost        = 0.001       # 0.1%
CONFIG.trading.slippage                = 0.0005
CONFIG.trading.max_position_pct        = 0.25        # 25% per asset
CONFIG.trading.max_leverage            = 1.0
CONFIG.trading.stop_loss_pct           = 0.05        # 5%
CONFIG.trading.take_profit_pct         = 0.15        # 15%
CONFIG.trading.max_drawdown_threshold  = 0.15        # 15% → halt
```

**Reward weights:**

```python
CONFIG.reward.w1 = 0.30   # Annualised return
CONFIG.reward.w2 = 0.20   # Downside deviation penalty
CONFIG.reward.w3 = 0.15   # Differential return vs benchmark
CONFIG.reward.w4 = 0.15   # Treynor ratio
CONFIG.reward.w5 = 0.15   # Sharpe ratio
CONFIG.reward.w6 = 0.05   # Portfolio entropy (diversification bonus)
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
CONFIG.sac.tau             = 0.005
CONFIG.sac.alpha           = 0.2
CONFIG.sac.auto_alpha      = True
CONFIG.sac.buffer_size     = 1_000_000
```

### Training Pipeline

```bash
python main.py
```

| Phase | What happens |
|-------|-------------|
| **1 · Data** | Fetch OHLCV from Yahoo Finance; compute 14+ indicators; Z-score normalise; 80/20 split |
| **2 · Train** | Run N episodes; PPO batches rollout every 2048 steps; SAC updates every step after 1000 warmup |
| **3 · Evaluate** | Deterministic policy on held-out test set; compute Sharpe, Sortino, Calmar, alpha, beta, win rate |
| **4 · Export** | Write `output/dashboard_data.json` |

### Running the API Server

```bash
# Development
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Frontend

### Frontend Setup

**Node.js 18+**

```bash
cd rl_react_dashboard/rl-dashboard
npm install
npm run dev      # → http://localhost:5173
npm run build    # → dist/
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ● Connected  [Bull]  ● LIVE  AAPL $189 ▲0.31%  GOOGL …  [SIM]    │  ← sticky
├──────────────────────────────────────┬──────────────────────────────┤
│  Portfolio  Sharpe   Drawdown  WinRate│                             │
│  Alpha      Beta     Cash      Trades│  Agent Controls             │
├──────────────────────────────────────┤  ─ Paper / ⚠ Live           │
│         Equity sparkline embedded    │  ─ Model selector           │
├──────────────────────────────────────┤  ─ Episodes (5–500)         │
│  Candlestick chart  [Reset Zoom]     │  ─ Start / Stop             │
│  (BUY ▲ / SELL ▼ markers)           ├─────────────────────────────┤
│                                      │  Signals │ Positions        │
├───────────┬──────────────────────────┤  Sentiment│ News │ Features │
│ Risk meter│  Daily P&L │  Volatility │                             │
├───────────┴────────────────────────────────────────────────────────┤
│  AI Portfolio Analyst  [Analyze]  ← Groq streaming, md rendering  │
├────────────────────────────────────────────────────────────────────┤
│  Trade Analytics  ← rolling win-rate bars · streak · avg return   │
└────────────────────────────────────────────────────────────────────┘
```

| Panel | Description |
|-------|-------------|
| **Live ticker** | Sticky header; real-time prices with flash on change; `● LIVE` or `SIM` badge |
| **KPI cards** | Portfolio value, Sharpe, max drawdown gauge, win rate, alpha, beta, cash, trades |
| **Candlestick chart** | Lightweight Charts; symbol switcher; BUY/SELL markers; Reset Zoom button; zoom state preserved across live refreshes |
| **Risk meter** | Semicircle gauge mapping Sharpe → 0–100 health score |
| **AI Analyst** | Groq Llama 3.1 streaming report; full markdown rendering (headings, bold, bullets); re-analyze anytime |
| **Trade Analytics** | Rolling win-rate bar chart (last 20 trades); win/loss streak badge; avg return, avg win/loss, best/worst trade, buy/sell counts |
| **Signals tab** | Trade signals with expandable reasoning, sentiment arrow, regime tag |
| **Positions tab** | Open positions with long/short badge, weight bar |
| **Sentiment tab** | Dominant sentiment over last 50 signals; per-symbol breakdown |
| **News tab** | Real headlines (`● LIVE`) or simulated (`SIM`); `AI` badge for FinBERT-scored items; manual refresh button |
| **Features tab** | Top-10 feature importance bars |

---

## API Reference

All endpoints: `/api/v1/…`

### Authentication

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/auth/login` | `{email, password}` | `{accessToken, user}` |
| POST | `/auth/signup` | `{name, email, password}` | `{accessToken, user}` |
| GET | `/auth/me` | — | `User` |

### Agent

| Method | Endpoint | Body / Query | Response |
|--------|----------|------|----------|
| GET | `/agents/status` | — | `AgentState[]` |
| POST | `/agents/control` | `{action, model?, mode?, n_episodes?}` | `{message}` |

`action`: `"start"` · `"stop"` · `model`: `"ensemble"` · `"ppo"` · `"sac"` · `"ppo_lstm"` · `"sac_lstm"`

### Portfolio

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/portfolio/metrics` | KPIs: value, Sharpe, drawdown, win rate, … |
| GET | `/portfolio/positions` | Open positions |
| GET | `/portfolio/trades` | Trade signals (last 200) |
| GET | `/portfolio/equity` | Equity curve history |
| GET | `/portfolio/feature_importance` | `{feature: weight}` |
| GET | `/portfolio/risk` | Detailed risk breakdown |
| GET | `/portfolio/analysis` | **Streaming** Groq AI portfolio report (`text/plain`) |

### Market Data

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/market/symbols` | Tracked tickers |
| GET | `/market/history/{symbol}` | OHLCV (last 500 bars) |
| GET | `/market/live` | Live prices `{symbol: {price, change, change_pct, simulated}}` |
| GET | `/market/regime` | `{current: string, timestamp}` |

### Sentiment

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/sentiment/news?limit=20` | `NewsItem[]` with `is_live`, `ai_scored`, `sentiment`, `impact_score` |
| POST | `/sentiment/news/refresh` | Force-refresh live news cache immediately |
| GET | `/sentiment/status` | FinBERT model load status |

### WebSocket

Connect to `ws://localhost:8000/ws`. Pushes every second:

```jsonc
{ "type": "metrics", "data": { "portfolio_value": 1023400, "sharpe_ratio": 1.42, ... } }
{ "type": "tick",    "data": { "AAPL": { "price": 189.42, "change_pct": 0.31 }, ... } }
{ "type": "signal",  "data": [ { "action": "BUY", "symbol": "AAPL", "confidence": 0.87 } ] }
{ "type": "news",    "data": [ { "title": "...", "sentiment": "positive", "ai_scored": true } ] }
```

---

## RL Agents

### PPO (Proximal Policy Optimization)

```
LSTM extractor : (lookback, obs_dim) → 128-dim  (2 layers × 128 hidden)
Actor          : [256] → [64] → n_actions  (tanh)
Critic         : [256] → [64] → 1
```

10 update epochs · batch 64 · GAE λ=0.95 · clip ε=0.2

### SAC (Soft Actor-Critic)

```
Actor  : LSTM → [256, 256] → (μ, log σ)
Q1, Q2 : (obs, action) → [256, 256] → scalar
Target : soft update τ=0.005
```

Replay buffer 1M · warmup 1000 steps · auto-tuned entropy α

### Ensemble

```
action = ppo_weight × ppo_action + sac_weight × sac_action
```

With `use_meta_policy=True` a small MLP learns adaptive weighting from regime + recent performance.

### Observation Space

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

```
R = w₁·R_ann  −  w₂·σ_down  +  w₃·D_ret  +  w₄·T_ry  +  w₅·R_sharpe  +  w₆·H_entropy
    − drawdown_penalty
```

| Component | Symbol | Description | Weight (v3) |
|-----------|--------|-------------|-------------|
| Annualised return | R_ann | `(∏(1+rₜ))^(252/T) − 1` | 0.30 |
| Downside deviation | σ_down | `std(min(r−rₓ, 0)) × √252` | **0.25** |
| Differential return | D_ret | `(μ_p − μ_b) / |β|` | **0.10** |
| Treynor ratio | T_ry | `(R_ann − Rₓ) / β` | **0.10** |
| Sharpe ratio | R_sharpe | `(μ − rₓ) / σ × √252` | **0.20** |
| Portfolio entropy | H_entropy | Shannon entropy of position weights | 0.05 |

**Drawdown penalty (v3 — exponential):**

| Drawdown | Penalty |
|----------|---------|
| < 3% | 0 (ignored) |
| 5% | ~0.08 |
| 10% | ~0.32 |
| 20% | ~1.28 |
| 30% | 2.88 (approaching clip) |

**Per-step shaping** (`StepRewardShaper`): turnover penalty `0.05 × Δaction`, direct P&L signal `0.3 × tanh(pnl × 200)`, capital-preservation penalty when portfolio drops below 90% of initial capital.

**Regime-adaptive scaling:**

| Regime | Return weight | Risk weight | Sharpe weight |
|--------|--------------|-------------|---------------|
| Bull | ×1.10 | ×0.90 | ×1.00 |
| Bear | ×0.80 | ×1.30 | ×1.20 |
| High Volatility | ×0.85 | ×1.20 | ×1.15 |
| Sideways | ×1.00 | ×1.00 | ×1.00 |

---

## Risk Management

| Constraint | Default |
|------------|---------|
| Max position | 25% per asset |
| Max leverage | 1.0× (no margin) |
| Stop-loss | 5% |
| Take-profit | 15% |
| Max drawdown | 15% → halts trading |
| Trade cooldown | 3 steps between trades |

Position sizing uses Kelly Criterion scaled by volatility:

```
kelly = (μ − r_f) / σ²
size  = min(kelly × capital × 0.5,  max_position_pct × capital)
```

---

## Market Regime Detection

HMM in `regime/detector.py` classifies the market using a rolling 20-day window:

| Regime | Signal | Dashboard colour |
|--------|--------|-----------------|
| Bull | High returns, low vol | Emerald |
| Bear | Negative returns | Red |
| Sideways | Returns ≈ 0, low vol | Amber |
| High Volatility | Mixed returns, high vol | Purple |

The regime is included in every agent observation, used to scale reward weights, streamed via WebSocket, and shown as an animated badge in the sticky header.

---

## Sentiment Analysis

`sentiment/analyzer.py` uses **FinBERT** (`ProsusAI/finbert`) — a BERT model fine-tuned on financial text:

- Returns three probabilities: `positive`, `negative`, `neutral`
- `confidence` = probability of predicted class
- `impact_score` = P(positive) − P(negative) — a continuous signal for the trading engine
- Results tagged `ai_scored=True`; shown with `AI` badge in the news panel
- Falls back to keyword-based scoring automatically if PyTorch/transformers are not installed

**Live news** — `LiveNewsFetcher`
- Fetches real headlines via `yfinance.Ticker.news` every 60 s (all configured tickers)
- Batch-scored through FinBERT in one pass
- Tagged `is_live=True`; shown with `● LIVE` badge
- Manual force-refresh via dashboard button or `POST /sentiment/news/refresh`

**DecisionValidator** adjusts actions on sentiment conflict: strong disagreement reduces position size by up to 50%.

---

## AI Portfolio Analyst

A streaming natural-language portfolio report powered by **Groq** (Llama 3.1 8B, free tier).

- Click **Analyze** in the dashboard to stream a report
- Includes: portfolio health, P&L, risk metrics, open positions, recent signals, news sentiment
- Renders formatted markdown in the dashboard (headings, bold, bullet points)
- Endpoint: `GET /api/v1/portfolio/analysis` (streams `text/plain`)
- Requires `GROQ_API_KEY` in `.env` — free key at [console.groq.com](https://console.groq.com)

---

## Tech Stack

### Backend

| Package | Role |
|---------|------|
| FastAPI + Uvicorn | REST + WebSocket server |
| pandas + NumPy | Data frames, maths |
| yfinance | Prices, OHLCV, news headlines |
| transformers + torch | FinBERT AI sentiment |
| groq | Groq AI portfolio analyst |
| python-dotenv | API key management |
| scikit-learn | HMM regime detection |

### Frontend

| Package | Role |
|---------|------|
| React 18 + TypeScript 5 | UI framework |
| Vite 5 | Dev server + bundler |
| Tailwind CSS 3 | Styling |
| Zustand 5 | Client state |
| TanStack Query 5 | Server state + polling |
| React Router 6 | Routing |
| Lightweight Charts 4 | Candlestick chart |
| Axios 1.7 | HTTP + JWT interceptors |

---

## Demo Credentials

```
Email:    demo@trader.com
Password: password123
```

---

## License

MIT
