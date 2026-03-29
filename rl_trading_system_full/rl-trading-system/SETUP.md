# RL Trading System — Setup & Run Guide

## Prerequisites

- Python 3.9+ installed
- pip (comes with Python)
- Git (optional, for cloning)

## Step 1: Extract the project

```bash
# If you downloaded the tar.gz from Claude:
tar xzf rl_trading_system.tar.gz
cd rl-trading-system
```

## Step 2: Create a virtual environment (recommended)

```bash
# Create venv
python -m venv venv

# Activate it:
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

## Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run the system

```bash
python main.py
```

This will:
1. Generate synthetic market data (or use yfinance if available)
2. Train the PPO + SAC ensemble agent for 5 episodes
3. Run backtesting evaluation on the test set
4. Print performance metrics (Sharpe, Sortino, max drawdown, etc.)
5. Save dashboard data to output/dashboard_data.json

## Optional: Use real market data

```bash
pip install yfinance
python main.py
```

If yfinance is installed and has internet access, it will automatically
fetch real historical data from Yahoo Finance instead of synthetic data.

## Optional: Change configuration

Edit config/settings.py before running:

```python
# Change assets
CONFIG.data.tickers = ["AAPL", "AMZN", "META"]

# Change training duration
CONFIG.training.total_timesteps = 1_000_000

# Adjust reward weights
CONFIG.reward.w1 = 0.40  # More weight on returns
CONFIG.reward.w2 = 0.30  # More weight on downside protection

# Stricter risk management
CONFIG.trading.max_drawdown_threshold = 0.10  # 10% halt
CONFIG.trading.stop_loss_pct = 0.03           # 3% stop loss
```
