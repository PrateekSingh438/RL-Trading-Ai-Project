# RL Trading System — Setup & Run Guide

## Prerequisites

- Python 3.9+
- Node.js 18+ (for the React dashboard)
- pip

---

## Backend Setup

### Step 1: Navigate to the backend folder

```bash
cd rl-trading-system
```

### Step 2: Create a virtual environment (recommended)

```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install PyTorch for FinBERT sentiment (recommended)

```bash
# CPU (works on any machine):
pip install torch --index-url https://download.pytorch.org/whl/cpu

# GPU (if you have CUDA 12.1):
# pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Without PyTorch the system still runs — it falls back to keyword-based sentiment scoring.

### Step 5: Add your Gemini API key

Get a **free** key at [aistudio.google.com](https://aistudio.google.com), then edit `.env`:

```
GEMINI_API_KEY=AIza...
```

This enables the AI Portfolio Analyst feature in the dashboard. The rest of the system works without it.

### Step 6: Start the API server

```bash
python -m uvicorn server.app:app --reload --port 8000
```

The server will be available at `http://localhost:8000`.

---

## Frontend Setup (React Dashboard)

### Step 1: Navigate to the dashboard folder

```bash
cd rl_react_dashboard/rl-dashboard
```

### Step 2: Install dependencies

```bash
npm install
```

### Step 3: Start the dev server

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Using the Dashboard

1. **Start the backend** (`uvicorn server.app:app --reload --port 8000`)
2. **Start the frontend** (`npm run dev`)
3. Open the dashboard in your browser
4. Click **Start Agent** to begin trading simulation
5. Use the **Analyze** button in the AI Portfolio Analyst panel for a Gemini-powered report

---

## Configuration

Edit `config/settings.py` to customize:

```python
from config.settings import CONFIG

# Change tracked assets
CONFIG.data.tickers = ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"]

# Adjust reward weights
CONFIG.reward.w1 = 0.40  # Annualized return
CONFIG.reward.w2 = 0.30  # Downside penalty
CONFIG.reward.w3 = 0.15  # Differential return
CONFIG.reward.w4 = 0.15  # Treynor ratio

# Risk controls
CONFIG.trading.max_drawdown_threshold = 0.15  # halt at 15% drawdown
CONFIG.trading.stop_loss_pct           = 0.05  # 5% stop loss per position
CONFIG.trading.take_profit_pct         = 0.15  # 15% take profit
CONFIG.trading.transaction_cost        = 0.001 # 0.1% per trade
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Add key to `.env` and restart server |
| `google-generativeai not installed` | `pip install google-generativeai` |
| `python-dotenv not installed` | `pip install python-dotenv` |
| Live prices show "SIM" | Market is closed — simulated prices are used automatically |
| FinBERT not loading | Install PyTorch (Step 4 above); keyword fallback is used otherwise |
| Dashboard can't connect | Make sure backend is running on port 8000 |
