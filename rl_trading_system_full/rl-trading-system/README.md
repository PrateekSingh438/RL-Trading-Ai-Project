# Risk-Aware Multi-Asset RL Trading System

A production-grade reinforcement learning trading agent using an ensemble of **PPO + SAC with LSTM**, featuring market regime detection, sentiment validation, and a real-time dashboard.

## Architecture

```
R = w₁·R_ann − w₂·σ_down + w₃·D_ret + w₄·T_ry
```

## Folder Structure

```
rl-trading-system/
│
├── main.py                          # Entry point — runs full pipeline
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # All hyperparameters, asset lists, reward weights
│
├── data/
│   ├── __init__.py
│   └── pipeline.py                  # Data fetching (yfinance), 14 technical indicators,
│                                    # turbulence index, normalization, sliding windows
│
├── env/
│   ├── __init__.py
│   └── trading_env.py               # Gym-style multi-asset trading environment
│                                    # (observation space, action execution, transaction costs)
│
├── agents/
│   ├── __init__.py
│   ├── networks.py                  # LSTM cells, LSTM feature extractor, MLP,
│   │                                # Actor-Critic network, Q-Network
│   ├── ppo_agent.py                 # PPO with GAE, clipped surrogate, rollout buffer
│   ├── sac_agent.py                 # SAC with twin Q-nets, auto entropy, replay memory
│   └── ensemble.py                  # Weighted PPO+SAC ensemble, meta-policy network,
│                                    # adaptive weight updates
│
├── rewards/
│   ├── __init__.py
│   └── composite_reward.py          # Composite reward function (Eq. 6 from paper):
│                                    #   R_ann, σ_down, D_ret, T_ry
│                                    #   + normalization + reward shaping
│
├── risk/
│   ├── __init__.py
│   └── risk_manager.py              # Position sizing (Kelly, volatility-based),
│                                    # drawdown protection, stop-loss/take-profit,
│                                    # cooldown manager, risk parity, leverage limits
│
├── regime/
│   ├── __init__.py
│   └── detector.py                  # HMM-based and rule-based regime detection
│                                    # (Bull, Bear, Sideways, High Volatility)
│
├── sentiment/
│   ├── __init__.py
│   └── analyzer.py                  # News generation, sentiment analysis,
│                                    # decision validator (conflict → reduce position),
│                                    # trade explainer (human-readable reasoning)
│
├── evaluation/
│   ├── __init__.py
│   └── metrics.py                   # Sharpe, Sortino, max drawdown, alpha, beta,
│                                    # win rate, Calmar, profit factor
│                                    # + walk-forward backtester
│
├── training/
│   ├── __init__.py
│   └── pipeline.py                  # End-to-end orchestrator: data → train → eval
│                                    # → dashboard data generation
│
├── dashboard/
│   └── rl_trading_dashboard.jsx     # React dashboard (portfolio chart, trades,
│                                    # sentiment feed, regime timeline, explanations)
│
├── utils/
│   └── __init__.py
│
├── models/                          # Saved model weights (auto-created)
├── output/                          # Dashboard JSON data (auto-created)
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/rl-trading-system.git
cd rl-trading-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run training + evaluation
python main.py

# 4. View dashboard
#    Open the generated .jsx in Claude.ai or build with React
```

## Key Features

| Feature | Implementation |
|---|---|
| **RL Agents** | PPO (stable) + SAC (exploratory) ensemble with LSTM backbone |
| **Reward Function** | Composite: annualized return, downside deviation, differential return, Treynor ratio |
| **Risk Management** | Kelly sizing, volatility sizing, max drawdown halt, stop-loss, take-profit, cooldown |
| **Regime Detection** | HMM + rule-based (bull/bear/sideways/high-volatility) |
| **Sentiment** | News analysis, confidence scoring, decision validation (conflict → reduce position) |
| **Explainability** | Per-trade reasoning combining technical signals, sentiment, regime, and agent consensus |
| **Evaluation** | Sharpe, Sortino, max drawdown, alpha, beta, win rate, Calmar ratio |

## Configuration

All parameters are centralized in `config/settings.py`:

```python
from config.settings import CONFIG

# Modify assets
CONFIG.data.tickers = ["AAPL", "GOOGL", "MSFT"]

# Adjust reward weights
CONFIG.reward.w1 = 0.40  # Annualized return
CONFIG.reward.w2 = 0.30  # Downside penalty
CONFIG.reward.w3 = 0.15  # Differential return
CONFIG.reward.w4 = 0.15  # Treynor ratio

# Risk constraints
CONFIG.trading.max_drawdown_threshold = 0.10  # 10% halt
CONFIG.trading.transaction_cost = 0.001       # 0.1%
```

## License

MIT
