#!/usr/bin/env python3
"""
Generate a comprehensive PDF documentation for the RL Trading System.
Covers every concept from scratch in detail.
"""
from fpdf import FPDF
import os

def sanitize(text):
    """Replace Unicode chars that latin-1 can't encode."""
    return (text
        .replace("\u2014", "--")   # em dash
        .replace("\u2013", "-")    # en dash
        .replace("\u2018", "'")    # left single quote
        .replace("\u2019", "'")    # right single quote
        .replace("\u201c", '"')    # left double quote
        .replace("\u201d", '"')    # right double quote
        .replace("\u2022", "*")    # bullet
        .replace("\u2026", "...")  # ellipsis
        .replace("\u2192", "->")   # right arrow
        .replace("\u03b1", "alpha")
        .replace("\u03b2", "beta")
        .replace("\u03b3", "gamma")
        .replace("\u03bb", "lambda")
        .replace("\u03c0", "pi")
        .replace("\u03c3", "sigma")
        .replace("\u03bc", "mu")
    )


class DocPDF(FPDF):
    """Custom PDF with headers, footers and helper methods."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "RL Trading System -- Complete Technical Documentation", align="C")
        self.ln(4)
        self.set_draw_color(16, 185, 129)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def title_page(self):
        self.add_page()
        self.ln(50)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(16, 185, 129)
        self.cell(0, 20, "RL Trading System", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 16)
        self.set_text_color(80, 80, 80)
        self.cell(0, 12, "Complete Technical Documentation", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "Risk-Aware Multi-Asset Reinforcement Learning Trading System", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "PPO + SAC Ensemble | LSTM Feature Extraction | Real-Time Dashboard", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, "FinBERT Sentiment | Groq AI Analyst | GPU Acceleration", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, "Version 4.1 | April 2026", align="C", new_x="LMARGIN", new_y="NEXT")

    def chapter_title(self, num, title):
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(16, 185, 129)
        self.cell(0, 14, f"Chapter {num}", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(30, 30, 30)
        self.cell(0, 12, sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_draw_color(16, 185, 129)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(8)

    def section(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(50, 50, 50)
        self.cell(0, 9, sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def subsection(self, title):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(70, 70, 70)
        self.cell(0, 8, sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, sanitize(text))
        self.ln(2)

    def code(self, text):
        self.set_font("Courier", "", 9)
        self.set_fill_color(245, 245, 245)
        self.set_text_color(50, 50, 50)
        for line in sanitize(text).strip().split("\n"):
            self.cell(0, 5, "  " + line, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.set_x(10)
        self.multi_cell(self.w - 20, 5.5, "  - " + sanitize(text))


def build_pdf():
    pdf = DocPDF()
    pdf.alias_nb_pages()

    # ══════════════════════════════════════════════════════════════
    # TITLE PAGE
    # ══════════════════════════════════════════════════════════════
    pdf.title_page()

    # ══════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    toc = [
        ("1", "Introduction & System Overview"),
        ("2", "Reinforcement Learning Fundamentals"),
        ("3", "System Architecture"),
        ("4", "Data Pipeline & Feature Engineering"),
        ("5", "Trading Environment"),
        ("6", "RL Agents: PPO, SAC & Ensemble"),
        ("7", "Neural Network Architectures (LSTM)"),
        ("8", "Composite Reward Function"),
        ("9", "Risk Management Layer"),
        ("10", "Market Regime Detection"),
        ("11", "Sentiment Analysis & FinBERT"),
        ("12", "Training Pipeline & Walk-Forward Backtesting"),
        ("13", "FastAPI Backend Server"),
        ("14", "React Dashboard Frontend"),
        ("15", "GPU Acceleration"),
        ("16", "AI Portfolio Analyst (Groq)"),
        ("17", "WebSocket Real-Time Communication"),
        ("18", "Configuration & Hyperparameters"),
        ("19", "Deployment & Production"),
    ]
    pdf.set_font("Helvetica", "", 11)
    for num, title in toc:
        pdf.set_text_color(16, 185, 129)
        pdf.cell(12, 7, num)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, sanitize(title), new_x="LMARGIN", new_y="NEXT")

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 1: Introduction
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(1, "Introduction & System Overview")
    pdf.body(
        "This document provides a comprehensive, from-scratch explanation of the Risk-Aware "
        "Multi-Asset RL Trading System. The system uses reinforcement learning (RL) to train "
        "autonomous trading agents that manage a portfolio of US equities. It combines two "
        "state-of-the-art RL algorithms — Proximal Policy Optimization (PPO) and Soft "
        "Actor-Critic (SAC) — into an ensemble that balances stability with exploration."
    )
    pdf.body(
        "The system is designed as a full-stack application with a Python backend (FastAPI) "
        "and a React TypeScript dashboard. It fetches real market data, performs AI-powered "
        "sentiment analysis on financial news, detects market regimes, enforces risk constraints, "
        "and provides explainable trade decisions — all streamed in real-time over WebSocket."
    )

    pdf.section("Key Capabilities")
    for cap in [
        "Trains PPO + SAC ensemble agents on multi-asset historical data (5 stocks by default)",
        "Real-time market price streaming via yfinance (refreshed every 30 seconds)",
        "AI sentiment analysis using FinBERT (ProsusAI/finbert transformer model)",
        "Market regime detection (Bull/Bear/Sideways/High-Volatility) using HMM",
        "Risk management: Kelly sizing, stop-loss, take-profit, max drawdown halt",
        "WebSocket broadcasting of metrics, signals, prices, news, regime changes",
        "Explainable AI: every trade decision includes reasoning (technical + sentiment + regime)",
        "AI Portfolio Analyst powered by Groq (Llama 3.1) for natural-language reports",
        "GPU acceleration support with CPU/CUDA toggle from the dashboard",
        "Walk-forward backtesting for robust out-of-sample evaluation",
    ]:
        pdf.bullet(cap)

    pdf.section("Default Trading Universe")
    pdf.body("AAPL (Apple) | GOOGL (Alphabet) | MSFT (Microsoft) | NFLX (Netflix) | TSLA (Tesla)")
    pdf.body("Benchmark: S&P 500 (^GSPC). All tickers, date ranges, and parameters are configurable via config/settings.py.")

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 2: RL Fundamentals
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(2, "Reinforcement Learning Fundamentals")
    pdf.body(
        "Reinforcement Learning (RL) is a branch of machine learning where an agent learns to "
        "make sequential decisions by interacting with an environment. Unlike supervised learning "
        "(which requires labelled data), RL learns from trial-and-error experience. The agent "
        "receives observations of the environment state, takes actions, and receives scalar "
        "rewards that indicate how good those actions were."
    )

    pdf.section("The RL Framework (MDP)")
    pdf.body(
        "An RL problem is formalised as a Markov Decision Process (MDP) with five components:\n\n"
        "S (State space): All possible states the environment can be in. In trading, this includes "
        "portfolio value, cash, positions, prices, technical indicators, and regime features.\n\n"
        "A (Action space): All possible actions the agent can take. Here, a continuous value "
        "[-1, +1] per asset where -1 means sell all and +1 means buy maximum.\n\n"
        "P (Transition function): The probability of moving from state s to s' given action a. "
        "In trading, this is determined by the market (non-stationary and stochastic).\n\n"
        "R (Reward function): A scalar signal evaluating the quality of each action. Our composite "
        "reward combines annualised return, downside risk, Sharpe ratio, and more.\n\n"
        "gamma (Discount factor): A value in [0, 1] that determines how much the agent values "
        "future rewards vs immediate rewards. We use gamma = 0.99."
    )

    pdf.section("Policy and Value Functions")
    pdf.body(
        "The agent's behaviour is defined by its policy, pi(a|s), which maps states to a "
        "probability distribution over actions. The goal is to find the optimal policy that "
        "maximises the expected cumulative discounted reward:\n\n"
        "J(pi) = E[ sum_{t=0}^{T} gamma^t * r_t ]\n\n"
        "The value function V(s) estimates the expected return starting from state s and "
        "following policy pi. The action-value function Q(s,a) estimates the expected return "
        "after taking action a in state s. These functions are critical for both PPO and SAC."
    )

    pdf.section("On-Policy vs Off-Policy Learning")
    pdf.body(
        "On-policy methods (like PPO) learn from data generated by the current policy. After "
        "each update, old experience is discarded. This is stable but sample-inefficient.\n\n"
        "Off-policy methods (like SAC) can learn from data generated by any policy, stored in a "
        "replay buffer. This is more sample-efficient but can be less stable.\n\n"
        "Our ensemble combines both: PPO provides stable, conservative actions while SAC provides "
        "exploratory, sample-efficient learning. The weighted combination gets the best of both."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 3: System Architecture
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(3, "System Architecture")
    pdf.body(
        "The system follows a client-server architecture with clear separation between the "
        "Python backend (training, inference, data) and the React frontend (visualisation, control)."
    )

    pdf.section("Backend Components")
    for comp in [
        "FastAPI Server (v4): REST API + WebSocket + background threads for price/news refresh",
        "Training Pipeline: End-to-end data loading, environment creation, agent training, evaluation",
        "EnsembleAgent: Combines PPO and SAC sub-agents with weighted or meta-policy mixing",
        "TradingEnv: Gym-style multi-asset environment with realistic transaction costs and slippage",
        "CompositeReward: 6-component reward function with regime-adaptive weights",
        "RiskManager: Position sizing, drawdown protection, stop-loss/take-profit, cooldown",
        "RegimeDetector: HMM-based market regime classification (4 regimes)",
        "SentimentAnalyzer: FinBERT AI model for financial news sentiment scoring",
        "LiveNewsFetcher: Real headlines from yfinance with per-ticker caching",
    ]:
        pdf.bullet(comp)

    pdf.section("Frontend Components")
    for comp in [
        "React 18 + TypeScript 5 with Vite bundler",
        "Tailwind CSS for responsive, dark-mode-capable styling",
        "Zustand for client state (auth, UI, theme)",
        "TanStack Query for server state (polling, caching, optimistic updates)",
        "Lightweight Charts for candlestick visualisation",
        "WebSocket client with automatic reconnection and backoff",
        "Pages: Dashboard, Analytics, Trade History, Settings, Login/Signup",
    ]:
        pdf.bullet(comp)

    pdf.section("Communication")
    pdf.body(
        "REST API (HTTP): Used for CRUD operations — authentication, profile management, "
        "agent control, historical data queries. All endpoints under /api/v1/.\n\n"
        "WebSocket (/ws): Real-time streaming channel pushing metrics, live prices, trade "
        "signals, news, and regime changes every second. The dashboard subscribes on login "
        "and receives automatic updates without polling."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 4: Data Pipeline
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(4, "Data Pipeline & Feature Engineering")
    pdf.body(
        "The data pipeline is responsible for fetching historical market data, computing "
        "technical indicators, normalising features, and preparing train/test splits. It is "
        "implemented in data/pipeline.py."
    )

    pdf.section("Data Sources")
    pdf.body(
        "Primary: yfinance — fetches OHLCV (Open, High, Low, Close, Volume) data from Yahoo "
        "Finance. Supports any ticker symbol.\n\n"
        "Fallback: Synthetic data generator using Geometric Brownian Motion (GBM) with "
        "mean-reverting components and occasional jump diffusions. This ensures the system "
        "works even without internet access."
    )

    pdf.section("Technical Indicators (14+)")
    indicators = [
        ("RSI (Relative Strength Index)", "Momentum oscillator (0-100). Values > 70 suggest overbought, < 30 oversold. Period: 14 days."),
        ("MACD + Signal", "Moving Average Convergence Divergence. Difference between 12-day and 26-day EMAs. Signal line is 9-day EMA of MACD."),
        ("Bollinger Bands (Upper/Lower)", "Price channels at +/- 2 standard deviations from 20-day SMA. Measures volatility."),
        ("SMA 30, SMA 60", "Simple Moving Averages over 30 and 60 days. Trend-following indicators."),
        ("EMA 12, EMA 26", "Exponential Moving Averages. More responsive to recent prices than SMA."),
        ("Volume Normalized", "Current volume divided by 20-day average volume. Detects unusual activity."),
        ("Volatility", "20-day rolling standard deviation of returns, annualised (x sqrt(252))."),
        ("CCI (Commodity Channel Index)", "Measures deviation from average price. Period: 20."),
        ("DMI/ADX (Directional Movement Index)", "Trend strength indicator. High ADX = strong trend."),
        ("Turbulence Index", "Mahalanobis distance of returns from historical mean. Detects abnormal market regimes."),
    ]
    for name, desc in indicators:
        pdf.subsection(name)
        pdf.body(desc)

    pdf.section("Normalisation")
    pdf.body(
        "All features are Z-score normalised: x_norm = (x - mean) / std. Statistics are computed "
        "on the training set only and stored for consistent normalisation at inference time. "
        "This prevents look-ahead bias."
    )

    pdf.section("Train/Test Split")
    pdf.body(
        "Data is split chronologically (not randomly) at 80/20. This is critical for time-series "
        "data to prevent information leakage from future data into training."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 5: Trading Environment
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(5, "Trading Environment")
    pdf.body(
        "The trading environment (env/trading_env.py) is a custom Gym-style environment that "
        "simulates multi-asset portfolio trading with realistic constraints. It follows the "
        "standard RL interface: reset() -> obs, step(action) -> (obs, reward, done, info)."
    )

    pdf.section("Observation Space")
    pdf.body(
        "The observation vector contains:\n"
        "- Normalised cash (1 dim)\n"
        "- Normalised position values per asset (n_assets dims)\n"
        "- Normalised prices per asset (n_assets dims)\n"
        "- All technical indicator features (n_features x n_assets dims)\n"
        "- Market regime one-hot encoding (4 dims: Bull, Bear, Sideways, High-Vol)\n\n"
        "For 5 assets with 14 indicators, total observation dimension is approximately 81."
    )

    pdf.section("Action Space")
    pdf.body(
        "Continuous actions in [-1, +1] per asset:\n"
        "- +1.0: Buy maximum allowed position\n"
        "- 0.0: Hold current position\n"
        "- -1.0: Sell entire position\n\n"
        "The system is long-only: no short selling. Actions pass through the risk management "
        "layer before execution, which may modify them for safety."
    )

    pdf.section("Trade Execution Model")
    pdf.body(
        "Trades are executed with realistic friction:\n"
        "- Transaction cost: 0.1% of trade value (configurable)\n"
        "- Slippage: 0.05% adverse price movement\n"
        "- Maximum position: 25% of portfolio per asset\n"
        "- Cash cannot go negative (no margin trading by default)\n"
        "- Positions cannot go negative (no short selling)"
    )

    pdf.section("Step Cycle")
    pdf.body(
        "1. Agent outputs raw actions [-1, 1] per asset\n"
        "2. Risk manager modifies actions (drawdown halt, stop-loss, cooldown)\n"
        "3. Regime detector applies position scaling (e.g., 0.3x in high volatility)\n"
        "4. Trades are executed with slippage and transaction costs\n"
        "5. Time advances; new prices are observed\n"
        "6. Portfolio value is recomputed\n"
        "7. Reward is calculated via the composite reward function + step shaper\n"
        "8. New observation is constructed\n"
        "9. Return (obs, reward, done, info)"
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 6: RL Agents
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(6, "RL Agents: PPO, SAC & Ensemble")

    pdf.section("Proximal Policy Optimization (PPO)")
    pdf.body(
        "PPO is an on-policy actor-critic algorithm from OpenAI (Schulman et al., 2017). "
        "It is the most popular RL algorithm for continuous control due to its stability "
        "and ease of tuning.\n\n"
        "Key idea: PPO constrains policy updates to a 'trust region' using a clipped "
        "surrogate objective. This prevents catastrophically large updates that can destabilise training."
    )
    pdf.subsection("Clipped Surrogate Objective")
    pdf.body(
        "L_CLIP = E[ min( r_t * A_t,  clip(r_t, 1-eps, 1+eps) * A_t ) ]\n\n"
        "Where r_t = pi_new(a|s) / pi_old(a|s) is the probability ratio, A_t is the advantage "
        "estimate (how much better this action was vs the value baseline), and eps = 0.2 is the "
        "clipping threshold. This ensures the new policy stays within 20% of the old policy."
    )
    pdf.subsection("Generalised Advantage Estimation (GAE)")
    pdf.body(
        "GAE provides low-variance advantage estimates by combining multi-step TD errors:\n\n"
        "A_t = sum_{l=0}^{T-t} (gamma * lambda)^l * delta_{t+l}\n"
        "delta_t = r_t + gamma * V(s_{t+1}) - V(s_t)\n\n"
        "Lambda = 0.95 balances bias (low lambda) vs variance (high lambda)."
    )
    pdf.subsection("PPO Training Loop")
    pdf.body(
        "1. Collect rollout of 2048 steps using current policy\n"
        "2. Compute GAE advantages and returns\n"
        "3. Perform 10 epochs of mini-batch updates (batch size 64)\n"
        "4. For each mini-batch, compute clipped policy loss + value loss + entropy bonus\n"
        "5. Gradient descent with Adam (lr=3e-4), gradient clipping at 0.5\n"
        "6. Discard rollout data (on-policy: cannot reuse)"
    )

    pdf.section("Soft Actor-Critic (SAC)")
    pdf.body(
        "SAC is an off-policy maximum-entropy RL algorithm (Haarnoja et al., 2018). "
        "It maximises both the expected return AND the entropy (randomness) of the policy:\n\n"
        "J = E[ sum gamma^t (r_t + alpha * H(pi(.|s_t))) ]\n\n"
        "The entropy term encourages exploration, prevents premature convergence, and makes "
        "the policy more robust. Alpha is automatically tuned."
    )
    pdf.subsection("Twin Q-Networks")
    pdf.body(
        "SAC uses two Q-networks (Q1, Q2) with separate target networks to reduce "
        "overestimation bias. The minimum of the two Q-values is used for both the actor "
        "and critic updates:\n\n"
        "y = r + gamma * (min(Q1_target, Q2_target) - alpha * log pi(a'|s'))\n\n"
        "Target networks are updated via Polyak averaging: theta_target = tau * theta + "
        "(1 - tau) * theta_target, with tau = 0.005."
    )
    pdf.subsection("Replay Buffer")
    pdf.body(
        "SAC stores transitions (s, a, r, s', done) in a replay buffer of 1M capacity. "
        "Training samples random mini-batches of 256, enabling the agent to learn from past "
        "experience (off-policy). Learning starts after 1000 warmup steps."
    )

    pdf.section("Ensemble Agent")
    pdf.body(
        "The EnsembleAgent (agents/ensemble.py) combines PPO and SAC to leverage both:\n\n"
        "action = w_ppo * action_ppo + w_sac * action_sac\n\n"
        "Default weights: 50/50. Weights adapt based on recent performance — the agent with "
        "better recent returns gets higher weight. A meta-policy option uses a small MLP to "
        "learn optimal weighting from the current market state."
    )
    pdf.subsection("Decision Explainability")
    pdf.body(
        "Every ensemble decision records: PPO action, SAC action, ensemble action, weights, "
        "PPO value estimate, log probability, and agent agreement score. This information "
        "is displayed in the dashboard's Signals panel for transparency."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 7: Neural Network Architectures
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(7, "Neural Network Architectures (LSTM)")
    pdf.body(
        "Financial time series have strong temporal dependencies. We use Long Short-Term Memory "
        "(LSTM) networks as the feature extractor for all agents."
    )

    pdf.section("LSTM Feature Extractor")
    pdf.body(
        "Architecture: 2-layer LSTM with 128 hidden units per layer.\n\n"
        "Input: Observation vector (or sequence) of shape (seq_len, obs_dim)\n"
        "Output: 128-dimensional feature vector (final hidden state of top layer)\n\n"
        "The LSTM processes sequential market data and learns temporal patterns like momentum, "
        "mean reversion, and volatility clustering. Xavier weight initialization is used for "
        "stable training."
    )

    pdf.section("Actor-Critic Network (PyTorch)")
    pdf.body(
        "When PyTorch is available, the PPO agent uses a PyTorch LSTMActorCritic:\n\n"
        "LSTM: (obs_dim) -> 128-dim hidden (2 layers, batch_first)\n"
        "Actor head: Linear(128, 256) -> ReLU -> Linear(256, 256) -> ReLU -> Linear(256, n_actions) -> Tanh\n"
        "Critic head: Linear(128, 256) -> ReLU -> Linear(256, 256) -> ReLU -> Linear(256, 1)\n"
        "Log standard deviation: learnable parameter vector\n\n"
        "Weights are initialised with orthogonal initialization (gain=0.01) for stability."
    )

    pdf.section("NumPy Fallback")
    pdf.body(
        "If PyTorch is not installed, the system falls back to a pure NumPy implementation "
        "with the same architecture. Training uses random gradient perturbation instead of "
        "backpropagation. This ensures the system runs on any machine."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 8: Composite Reward Function
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(8, "Composite Reward Function")
    pdf.body(
        "The reward function (rewards/composite_reward.py) is critical — it defines what the "
        "agent optimises for. A naive reward (just P&L) leads to excessive risk-taking. Our "
        "composite reward balances return, risk, benchmark-relative performance, and diversification."
    )

    pdf.section("Formula")
    pdf.body(
        "R = w1*R_ann - w2*sigma_down + w3*D_ret + w4*T_ry + w5*R_sharpe + w6*H_entropy - DD_penalty\n\n"
        "Each component is normalised via tanh(x/scale) to prevent any single component from "
        "dominating. All components are clipped to [-5, +5]."
    )

    pdf.section("Components Explained")
    components = [
        ("R_ann (Annualised Return, w1=0.35)", "Cumulative return scaled to annual rate: (product(1+r_t))^(252/T) - 1. Rewards the agent for making money."),
        ("sigma_down (Downside Deviation, w2=0.25)", "Standard deviation of negative excess returns, annualised. Penalises large losses more than volatility in general."),
        ("D_ret (Differential Return, w3=0.20)", "Excess return vs benchmark normalised by beta: (mu_p - mu_b) / |beta|. Rewards outperformance."),
        ("T_ry (Treynor Ratio, w4=0.20)", "Risk-adjusted return per unit of systematic risk: (R_ann - R_f) / beta. Rewards efficient use of market risk."),
        ("R_sharpe (Sharpe Ratio, w5=0.20)", "Excess return per unit of total volatility: (mu - r_f) / sigma * sqrt(252). The gold standard risk-adjusted metric."),
        ("H_entropy (Portfolio Entropy, w6=0.05)", "Shannon entropy of position weights. Rewards diversification — concentrated portfolios receive lower entropy scores."),
    ]
    for name, desc in components:
        pdf.subsection(name)
        pdf.body(desc)

    pdf.section("Drawdown Penalty (Exponential)")
    pdf.body(
        "v3 introduced an exponential drawdown penalty replacing the negligible linear one:\n\n"
        "Below 3%: No penalty (ignore micro-fluctuations)\n"
        "Above 3%: penalty = (dd - 0.03)^2 * scale * 80\n\n"
        "At 10% drawdown: ~0.32 penalty\n"
        "At 20% drawdown: ~1.28 penalty\n"
        "At 30% drawdown: ~2.88 penalty (approaching clip range)\n\n"
        "This strongly discourages the agent from letting the portfolio draw down significantly."
    )

    pdf.section("Step Reward Shaper")
    pdf.body(
        "Per-step shaping terms on top of the composite reward:\n\n"
        "1. Turnover penalty: -0.05 * sum(|action - prev_action|). Discourages excessive trading.\n"
        "2. P&L signal: 0.3 * tanh(pnl_pct * 200). Immediate feedback on each step's profit/loss.\n"
        "3. Capital preservation: Quadratic penalty when portfolio drops below 90% of initial capital."
    )

    pdf.section("Regime-Adaptive Weights")
    pdf.body(
        "Reward weights are scaled based on the current market regime:\n\n"
        "Bull: Return weight x1.10, Risk weight x0.90 (allow more risk-taking)\n"
        "Bear: Return weight x0.80, Risk weight x1.30 (become defensive)\n"
        "High Volatility: Return weight x0.85, Risk weight x1.20\n"
        "Sideways: No scaling (baseline weights)"
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 9: Risk Management
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(9, "Risk Management Layer")
    pdf.body(
        "The RiskManager (risk/risk_manager.py) operates OUTSIDE the RL agent as a hard "
        "constraint layer. Regardless of what the agent wants to do, the risk manager enforces "
        "safety rules. This is critical for real-world deployment."
    )

    pdf.section("Components")
    risk_components = [
        ("PositionSizer", "Enforces per-asset maximum position (25% of portfolio) and total leverage limit (1.0x). Uses Kelly Criterion for optimal sizing: f* = (p*b - q) / b, applied at half-Kelly for safety."),
        ("DrawdownProtection", "Tracks peak portfolio value and current drawdown. If drawdown exceeds 15%, ALL trading is halted and positions are force-liquidated. Resumes when drawdown recovers below threshold - 5%."),
        ("StopLossTakeProfit", "Per-position stop-loss at -5% and take-profit at +15%. Stop-loss closes the entire position; take-profit closes 50%. Entry prices are tracked per asset."),
        ("CooldownManager", "Minimum 3 steps between trades per asset. Prevents churning/overtrading. Actions during cooldown are reduced by 90%."),
        ("RiskParityAllocator", "Inverse-volatility weighting: assets with lower volatility get higher allocation, ensuring equal risk contribution."),
    ]
    for name, desc in risk_components:
        pdf.subsection(name)
        pdf.body(desc)

    pdf.section("Processing Flow")
    pdf.body(
        "Every step, raw agent actions pass through:\n"
        "1. Drawdown halt check -> force close if triggered\n"
        "2. Per-asset stop-loss / take-profit check\n"
        "3. Cooldown enforcement (reduce action magnitude)\n"
        "4. Position constraint application (max exposure per asset, total leverage)\n"
        "5. Risk metrics update (Sharpe, Sortino, VaR)"
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 10: Market Regime Detection
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(10, "Market Regime Detection")
    pdf.body(
        "The RegimeDetector (regime/detector.py) classifies the current market into one of "
        "four regimes. This information is used to adapt reward weights, adjust position sizing, "
        "and is included in the agent's observation space."
    )

    pdf.section("Four Regimes")
    regimes = [
        ("Bull Market", "Positive trend (>5% over lookback window) with normal volatility. Position scale: 1.2x."),
        ("Bear Market", "Negative trend (<-5%). Position scale: 0.5x. Reward shifts toward risk-aversion."),
        ("Sideways", "No clear trend, low volatility. Default regime. Position scale: 0.7x."),
        ("High Volatility", "Recent volatility > 1.5x historical average. Most restrictive: position scale 0.3x."),
    ]
    for name, desc in regimes:
        pdf.subsection(name)
        pdf.body(desc)

    pdf.section("Detection Methods")
    pdf.body(
        "HMM (Hidden Markov Model): Fits a 4-state Gaussian HMM to return data using EM "
        "(Baum-Welch). Each regime has characteristic return mean and variance. Regime "
        "probabilities are computed using forward algorithm.\n\n"
        "Rule-based: Simpler alternative using trend (SMA slope over 50 days) and volatility "
        "(20-day rolling std vs 252-day historical). Used as default for faster computation."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 11: Sentiment Analysis
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(11, "Sentiment Analysis & FinBERT")
    pdf.body(
        "The sentiment module (sentiment/analyzer.py) processes financial news to extract "
        "market sentiment, which is used to validate and adjust trading decisions."
    )

    pdf.section("FinBERT AI Model")
    pdf.body(
        "FinBERT (ProsusAI/finbert) is a BERT transformer model fine-tuned on financial text. "
        "It classifies text into three categories: positive, negative, neutral.\n\n"
        "Output: Three probabilities summing to 1.0.\n"
        "Confidence: Probability of the predicted class.\n"
        "Impact score: P(positive) - P(negative), a continuous signal from -1 to +1.\n\n"
        "The model is lazy-loaded (loaded on first use) and runs as a singleton. If PyTorch "
        "or transformers are not installed, it falls back to keyword-based scoring automatically."
    )

    pdf.section("Live News Fetcher")
    pdf.body(
        "LiveNewsFetcher uses yfinance to fetch real financial headlines for all tracked tickers. "
        "Headlines are batch-scored through FinBERT in a single pass for efficiency.\n\n"
        "Caching: Per-ticker TTL of 55 seconds (server) / 300 seconds (training).\n"
        "Background thread: Refreshes every 60 seconds.\n"
        "Manual refresh: Available via POST /sentiment/news/refresh."
    )

    pdf.section("Decision Validator")
    pdf.body(
        "The DecisionValidator adjusts RL agent actions when sentiment strongly disagrees "
        "with the agent's direction. If sentiment is strongly negative but the agent wants to "
        "buy, the position size is reduced by up to 50%. This acts as an additional safety layer."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 12: Training Pipeline
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(12, "Training Pipeline & Walk-Forward Backtesting")

    pdf.section("Training Pipeline (training/pipeline.py)")
    pdf.body(
        "The TrainingPipeline class orchestrates end-to-end training:\n\n"
        "Phase 1 - Data Preparation: Fetch OHLCV data, compute 14+ indicators, normalise, "
        "create 80/20 train/test split.\n\n"
        "Phase 2 - Training: Create trading environment and ensemble agent. Run N episodes of "
        "interaction. Each episode: reset env, agent selects actions, env steps, transitions "
        "stored. After each episode, both PPO and SAC are updated.\n\n"
        "Phase 3 - Evaluation: Run deterministic policy on held-out test set. Compute Sharpe, "
        "Sortino, Calmar, alpha, beta, max drawdown, win rate.\n\n"
        "Phase 4 - Export: Generate dashboard_data.json with portfolio values, trades, regimes, "
        "sentiment, explanations, and risk metrics history."
    )

    pdf.section("Walk-Forward Backtesting")
    pdf.body(
        "Walk-forward validation (evaluation/walk_forward.py) is the gold standard for "
        "time-series model evaluation. It prevents look-ahead bias by using a sliding window:\n\n"
        "1. Train on months 1-12, test on month 13\n"
        "2. Train on months 2-13, test on month 14\n"
        "3. Repeat...\n\n"
        "Default settings: 252-day training window (~1 year), 63-day test window (~3 months), "
        "21-day step size (~1 month). Results are aggregated across all folds."
    )

    pdf.section("Performance Metrics")
    metrics = [
        ("Total Return", "Final portfolio value / initial value - 1"),
        ("Annualised Return", "(1 + total_return)^(252/n_days) - 1"),
        ("Sharpe Ratio", "(mean_excess_return / std_returns) * sqrt(252)"),
        ("Sortino Ratio", "Like Sharpe but only penalises downside volatility"),
        ("Max Drawdown", "Largest peak-to-trough decline in portfolio value"),
        ("Calmar Ratio", "Annualised return / max drawdown"),
        ("Alpha", "Excess return above what CAPM predicts (Jensen's alpha)"),
        ("Beta", "Sensitivity to benchmark (S&P 500) movements"),
        ("Win Rate", "Percentage of positive-return days"),
        ("Profit Factor", "Total profit / total loss across round-trip trades"),
    ]
    for name, desc in metrics:
        pdf.subsection(name)
        pdf.body(desc)

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 13: FastAPI Backend
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(13, "FastAPI Backend Server")
    pdf.body(
        "The server (server/app.py) is a FastAPI v4.0 application providing REST endpoints, "
        "WebSocket real-time streaming, and background threads for data refresh."
    )

    pdf.section("API Endpoints")
    endpoints = [
        ("POST /auth/login", "Authenticate with email/password, returns JWT access token"),
        ("POST /auth/signup", "Create new user account"),
        ("GET /auth/me", "Get current user profile"),
        ("GET /profile", "Get trading profile (risk tolerance, model, capital, weights)"),
        ("PATCH /profile", "Update profile — applies changes to CONFIG in real-time"),
        ("GET /agents/status", "Get agent state (training status, progress, uptime)"),
        ("POST /agents/control", "Start/stop agent, abort training, set episodes"),
        ("GET /portfolio/metrics", "Current KPIs (Sharpe, drawdown, win rate, etc.)"),
        ("GET /portfolio/positions", "Open positions with market value and weight"),
        ("GET /portfolio/trades", "Trade signals with reasoning, sentiment, regime"),
        ("GET /portfolio/equity", "Equity curve history (last 1000 points)"),
        ("GET /portfolio/risk", "Detailed risk breakdown (VaR, CVaR, leverage)"),
        ("GET /portfolio/analysis", "STREAMING Groq AI portfolio report"),
        ("GET /market/symbols", "Tracked ticker symbols"),
        ("GET /market/history/{symbol}", "OHLCV candlestick data (last 500 bars)"),
        ("GET /market/live", "Real-time quotes for all symbols"),
        ("GET /market/regime", "Current market regime classification"),
        ("GET /sentiment/news", "Live financial headlines with AI sentiment scores"),
        ("GET /device", "GPU availability and current compute device"),
        ("POST /device", "Switch between CPU and CUDA"),
    ]
    for endpoint, desc in endpoints:
        pdf.subsection(endpoint)
        pdf.body(desc)

    pdf.section("Background Threads")
    pdf.body(
        "1. Live Price Refresh: Fetches real-time quotes from yfinance every 30 seconds. "
        "Falls back to simulated random walk if API fails.\n\n"
        "2. Live News Refresh: Fetches headlines every 60 seconds. Scores with FinBERT.\n\n"
        "3. WebSocket Push Loop: Broadcasts metrics, prices, signals, and news every second."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 14: React Dashboard
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(14, "React Dashboard Frontend")
    pdf.body(
        "The frontend is a React 18 + TypeScript application built with Vite, providing "
        "a real-time trading dashboard."
    )

    pdf.section("Pages")
    pages = [
        ("Dashboard", "Main trading UI with live ticker bar, 8 KPI cards, candlestick chart, agent controls, AI analyst, trade signals, positions, sentiment, news, and features."),
        ("Analytics", "Detailed trade analytics with rolling win-rate chart, streak badges, average return metrics, buy/sell ratio."),
        ("Trade History", "Sortable, filterable, paginated table of all trade signals with CSV export. Expandable rows show reasoning and sentiment."),
        ("Settings", "Agent configuration: risk tolerance, asset classes, RL model selection, GPU/CPU toggle, training parameters (episodes, learning rate, batch size, gamma), reward weights, capital and risk parameters."),
        ("Login / Signup", "Authentication with demo credentials (demo@trader.com / password123)."),
    ]
    for name, desc in pages:
        pdf.subsection(name)
        pdf.body(desc)

    pdf.section("State Management")
    pdf.body(
        "Client state (auth, UI theme, sidebar) uses Zustand with localStorage persistence.\n"
        "Server state (portfolio, market data, agents) uses TanStack Query with configurable "
        "polling intervals (5-30 seconds) and automatic caching."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 15: GPU Acceleration
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(15, "GPU Acceleration")
    pdf.body(
        "The system supports NVIDIA CUDA GPU acceleration for PyTorch-based PPO training. "
        "GPU support can be toggled from the Settings dashboard or via the REST API."
    )

    pdf.section("How It Works")
    pdf.body(
        "1. The Settings page fetches GET /device to check GPU availability.\n"
        "2. If a CUDA-capable GPU is detected, the GPU toggle becomes active.\n"
        "3. When switched to GPU, POST /device moves the PPO neural network to CUDA.\n"
        "4. All subsequent tensor operations (forward pass, backward pass) run on GPU.\n"
        "5. Observations are automatically moved to the correct device.\n"
        "6. If GPU is not available, a descriptive error message is shown.\n\n"
        "The SAC agent uses NumPy-based networks (no GPU) while PPO uses PyTorch (GPU-capable)."
    )

    pdf.section("Device Configuration")
    pdf.body(
        "The device setting is stored in CONFIG.training.device and persists for the session. "
        "Tensor creation in PPO (_train_torch) uses the configured device. The .cpu().numpy() "
        "pattern ensures tensors can be safely converted back to NumPy for environment interaction."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 16: AI Portfolio Analyst
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(16, "AI Portfolio Analyst (Groq)")
    pdf.body(
        "The AI Portfolio Analyst provides streaming natural-language portfolio reports "
        "powered by Groq (Llama 3.1 8B, free tier)."
    )

    pdf.section("How It Works")
    pdf.body(
        "1. User clicks Analyze in the dashboard\n"
        "2. Frontend sends GET /portfolio/analysis\n"
        "3. Server constructs a detailed prompt with: portfolio metrics, risk breakdown, "
        "open positions, recent signals, market news and sentiment\n"
        "4. Prompt is sent to Groq API (Llama 3.1 8B) with streaming enabled\n"
        "5. Tokens are streamed back as text/plain via StreamingResponse\n"
        "6. Dashboard renders the response as formatted markdown in real-time\n\n"
        "The report includes: Overall Assessment, Strengths, Risks & Concerns, and "
        "one actionable Recommendation. Requires GROQ_API_KEY in .env (free at console.groq.com)."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 17: WebSocket
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(17, "WebSocket Real-Time Communication")
    pdf.body(
        "The WebSocket endpoint (/ws) provides real-time data streaming to connected dashboards."
    )

    pdf.section("Message Types")
    msgs = [
        ("metrics", "Portfolio value, Sharpe, drawdown, win rate, regime, agent status, training progress. Pushed every second."),
        ("tick", "Live prices for all tracked symbols. Contains price, change, change_pct, simulated flag."),
        ("signal", "Last 5 trade signals with action, symbol, confidence, reasoning, sentiment."),
        ("news", "Top 10 live news headlines with sentiment scores and AI/live badges."),
        ("ping", "Keepalive message sent after 30 seconds of inactivity."),
    ]
    for name, desc in msgs:
        pdf.subsection(f"type: {name}")
        pdf.body(desc)

    pdf.section("Client Implementation")
    pdf.body(
        "The frontend WebSocket client (services/websocket.ts) implements automatic "
        "reconnection with exponential backoff. On disconnect, it attempts to reconnect "
        "after 1s, 2s, 4s, etc. Message handlers update Zustand stores which trigger "
        "React re-renders through selector-based subscriptions."
    )

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 18: Configuration
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(18, "Configuration & Hyperparameters")
    pdf.body(
        "All configuration is centralised in config/settings.py using Python dataclasses. "
        "The CONFIG singleton is the single source of truth."
    )

    pdf.section("Configuration Groups")
    configs = [
        ("DataConfig", "Tickers, benchmark, date range, train/test split, indicator list, lookback window, risk-free rate"),
        ("TradingConfig", "Initial capital ($1M), transaction cost (0.1%), slippage (0.05%), max position (25%), stop-loss (5%), take-profit (15%), max drawdown (15%), cooldown (3 steps)"),
        ("RewardConfig", "Weights w1-w4 for the composite reward function"),
        ("PPOConfig", "Learning rate (3e-4), gamma (0.99), GAE lambda (0.95), clip epsilon (0.2), entropy coef (0.01), epochs (10), batch size (64), hidden dims"),
        ("SACConfig", "Learning rate (3e-4), gamma (0.99), tau (0.005), alpha (0.2), auto-alpha, batch size (256), buffer size (1M), learning starts (1000)"),
        ("EnsembleConfig", "PPO/SAC weights (0.5/0.5), meta-policy toggle"),
        ("RegimeConfig", "Detection method (HMM/rules), number of regimes (4), lookback windows"),
        ("TrainingConfig", "Total timesteps (500K), eval/save frequency, model directory, seed, device (cpu/cuda)"),
    ]
    for name, desc in configs:
        pdf.subsection(name)
        pdf.body(desc)

    # ══════════════════════════════════════════════════════════════
    # CHAPTER 19: Deployment
    # ══════════════════════════════════════════════════════════════
    pdf.chapter_title(19, "Deployment & Production")

    pdf.section("Backend Deployment")
    pdf.body(
        "Development: uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload\n"
        "Production: uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4\n\n"
        "The server uses FastAPI's lifespan events for clean startup/shutdown. Background "
        "threads are daemonic and stop automatically when the process exits."
    )

    pdf.section("Frontend Deployment")
    pdf.body(
        "Build: npm run build (outputs to dist/)\n"
        "Serve static files via nginx, Vercel, or any CDN.\n"
        "Set VITE_API_URL environment variable to point to the backend."
    )

    pdf.section("Environment Variables")
    pdf.body(
        "GROQ_API_KEY: Required for AI Portfolio Analyst. Free key from console.groq.com.\n"
        "VITE_API_URL: Frontend API base URL (default: http://localhost:8000/api/v1)."
    )

    pdf.section("Demo Credentials")
    pdf.body("Email: demo@trader.com\nPassword: password123")

    # ══════════════════════════════════════════════════════════════
    # SAVE
    # ══════════════════════════════════════════════════════════════
    out_path = os.path.join(os.path.dirname(__file__), "RL_Trading_System_Documentation.pdf")
    pdf.output(out_path)
    print(f"PDF generated: {out_path}")
    return out_path


if __name__ == "__main__":
    build_pdf()
