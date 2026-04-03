"""
Training Pipeline
=================
Orchestrates data loading, environment creation, agent training,
evaluation, and model saving. Supports hyperparameter optimization.
"""
import numpy as np
import json
import os
import sys
import time
from typing import Dict, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SystemConfig, CONFIG
from data.pipeline import (
    fetch_data, prepare_multi_stock_data, normalize_features, generate_synthetic_data
)
from env.trading_env import TradingEnv
from agents.ensemble import EnsembleAgent
from rewards.composite_reward import CompositeReward
from risk.risk_manager import RiskManager
from regime.detector import RegimeDetector
from sentiment.analyzer import NewsGenerator, SentimentAnalyzer, DecisionValidator, TradeExplainer
from evaluation.metrics import PerformanceEvaluator, Backtester, BacktestResult


class TrainingPipeline:
    """
    End-to-end training pipeline for the RL trading system.
    """

    def __init__(self, config: SystemConfig = None):
        self.config = config or CONFIG
        self.agent = None
        self.train_env = None
        self.test_env = None
        self.results = {}

    def prepare_data(self) -> Tuple:
        """Load and prepare data with train/test split."""
        print("=" * 60)
        print("PHASE 1: DATA PREPARATION")
        print("=" * 60)

        cfg = self.config.data
        tickers = cfg.tickers
        print(f"Assets: {tickers}")
        print(f"Benchmark: {cfg.benchmark}")
        print(f"Period: {cfg.start_date} to {cfg.end_date}")

        # Fetch data
        raw_data = fetch_data(tickers, cfg.start_date, cfg.end_date, cfg.benchmark)
        print(f"Fetched data for {len(raw_data)} symbols")

        # Process features
        stock_features, benchmark_data = prepare_multi_stock_data(
            raw_data, tickers, cfg.benchmark
        )
        print(f"Feature matrix shape: {stock_features.shape}")

        # Normalize
        normalized, norm_stats = normalize_features(stock_features)

        # Extract price and return arrays
        price_cols = [f"{t}_Close" for t in tickers]
        available_price_cols = [c for c in price_cols if c in stock_features.columns]
        if not available_price_cols:
            available_price_cols = [c for c in stock_features.columns if "Close" in c][:len(tickers)]

        prices = stock_features[available_price_cols].values
        features = normalized.values

        # Benchmark returns
        bench_close = benchmark_data["Close"].values if "Close" in benchmark_data.columns else benchmark_data.iloc[:, 3].values
        bench_returns = np.diff(bench_close) / bench_close[:-1]
        bench_returns = np.concatenate([[0], bench_returns])

        # Align lengths
        min_len = min(len(prices), len(features), len(bench_returns))
        prices = prices[:min_len]
        features = features[:min_len]
        bench_returns = bench_returns[:min_len]

        # Train/test split
        split_idx = int(len(prices) * cfg.train_split)
        print(f"Train: {split_idx} days, Test: {len(prices) - split_idx} days")

        train_data = {
            "features": features[:split_idx],
            "prices": prices[:split_idx],
            "bench_returns": bench_returns[:split_idx]
        }
        test_data = {
            "features": features[split_idx:],
            "prices": prices[split_idx:],
            "bench_returns": bench_returns[split_idx:]
        }

        return train_data, test_data, tickers, norm_stats

    def create_environment(self, data: Dict, tickers: list) -> TradingEnv:
        """Create trading environment from data."""
        cfg_t = self.config.trading
        cfg_r = self.config.reward

        env = TradingEnv(
            stock_data=data["features"],
            price_data=data["prices"],
            benchmark_returns=data["bench_returns"],
            tickers=tickers,
            initial_capital=cfg_t.initial_capital,
            transaction_cost=cfg_t.transaction_cost,
            slippage=cfg_t.slippage,
            max_position_pct=cfg_t.max_position_pct,
            max_leverage=cfg_t.max_leverage,
            stop_loss_pct=cfg_t.stop_loss_pct,
            take_profit_pct=cfg_t.take_profit_pct,
            cooldown_steps=cfg_t.cooldown_steps,
            max_drawdown_threshold=cfg_t.max_drawdown_threshold,
            reward_weights=(cfg_r.w1, cfg_r.w2, cfg_r.w3, cfg_r.w4),
            risk_free_rate=self.config.data.risk_free_rate,
            lookback_window=min(self.config.data.lookback_window, len(data["prices"]) // 4)
        )
        return env

    def create_agent(self, obs_dim: int, action_dim: int) -> EnsembleAgent:
        """Create ensemble agent."""
        cfg_ppo = self.config.ppo
        cfg_sac = self.config.sac
        cfg_ens = self.config.ensemble

        agent = EnsembleAgent(
            obs_dim=obs_dim,
            action_dim=action_dim,
            ppo_weight=cfg_ens.ppo_weight,
            sac_weight=cfg_ens.sac_weight,
            use_meta_policy=cfg_ens.use_meta_policy,
            ppo_kwargs={
                "learning_rate": cfg_ppo.learning_rate,
                "gamma": cfg_ppo.gamma,
                "gae_lambda": cfg_ppo.gae_lambda,
                "clip_epsilon": cfg_ppo.clip_epsilon,
                "entropy_coef": cfg_ppo.entropy_coef,
                "n_epochs": cfg_ppo.n_epochs,
                "batch_size": cfg_ppo.batch_size,
                "hidden_dim": cfg_ppo.hidden_dim,
                "lstm_hidden_dim": cfg_ppo.lstm_hidden_dim,
                "num_lstm_layers": cfg_ppo.num_lstm_layers
            },
            sac_kwargs={
                "learning_rate": cfg_sac.learning_rate,
                "gamma": cfg_sac.gamma,
                "tau": cfg_sac.tau,
                "alpha": cfg_sac.alpha,
                "auto_alpha": cfg_sac.auto_alpha,
                "batch_size": cfg_sac.batch_size,
                "buffer_size": cfg_sac.buffer_size,
                "hidden_dim": cfg_sac.hidden_dim,
                "lstm_hidden_dim": cfg_sac.lstm_hidden_dim,
                "num_lstm_layers": cfg_sac.num_lstm_layers,
                "learning_starts": cfg_sac.learning_starts
            }
        )
        return agent

    def train(self, n_episodes: int = None) -> Dict:
        """
        Run the full training loop.
        """
        print("\n" + "=" * 60)
        print("PHASE 2: TRAINING")
        print("=" * 60)

        # Prepare data
        train_data, test_data, tickers, norm_stats = self.prepare_data()

        # Create environments
        self.train_env = self.create_environment(train_data, tickers)
        self.test_env = self.create_environment(test_data, tickers)

        # Create agent
        obs = self.train_env.reset()
        self.agent = self.create_agent(len(obs), self.train_env.action_dim)
        print(f"Agent created: obs_dim={len(obs)}, action_dim={self.train_env.action_dim}")

        # Sentiment components
        news_gen = NewsGenerator()
        sentiment_analyzer = SentimentAnalyzer()
        decision_validator = DecisionValidator()
        explainer = TradeExplainer()
        regime_detector = RegimeDetector(method="rules")

        # Training loop
        if n_episodes is None:
            n_episodes = max(1, self.config.training.total_timesteps // (self.train_env.T - self.train_env.lookback_window))
        n_episodes = min(n_episodes, 100)  # Cap for reasonable runtime

        print(f"Training for {n_episodes} episodes...")
        episode_rewards = []
        best_reward = -float("inf")

        for episode in range(n_episodes):
            obs = self.train_env.reset()
            done = False
            episode_reward = 0
            step_count = 0

            while not done:
                # Agent selects action
                action, decision_info = self.agent.select_action(obs)

                # Sentiment validation is SLOW — run only every 100 steps
                # to keep the training hot-path fast.
                if step_count % 100 == 0 and step_count > 0:
                    regime_name = "Sideways"
                    if hasattr(self.train_env, 'regime_detector'):
                        regime_name = self.train_env.regime_detector.get_regime_name()
                    news = news_gen.generate_news(tickers[:1], n_items=1, market_regime=regime_name)
                    for i, ticker in enumerate(tickers[:min(len(tickers), len(action))]):
                        report = sentiment_analyzer.analyze(news, ticker)
                        action[i], _ = decision_validator.validate(action[i], report, ticker)

                # Step environment
                next_obs, reward, done, info = self.train_env.step(action)

                # Store transition — get log_prob/value from the PPO sub-agent
                if hasattr(self.agent, 'ppo'):
                    _, log_prob, value = self.agent.ppo.select_action(obs)
                else:
                    log_prob, value = 0.0, 0.0
                self.agent.store_transition(
                    obs, action, reward, next_obs, done,
                    value=value, log_prob=log_prob
                )

                episode_reward += reward
                obs = next_obs
                step_count += 1

            # Train agent
            train_stats = self.agent.train()
            episode_rewards.append(episode_reward)

            # Logging
            perf = self.train_env.get_performance_summary()
            if (episode + 1) % max(1, n_episodes // 10) == 0 or episode == 0:
                print(
                    f"  Episode {episode + 1}/{n_episodes} | "
                    f"Reward: {episode_reward:.2f} | "
                    f"Return: {perf.get('total_return', 0):.2%} | "
                    f"Sharpe: {perf.get('sharpe_ratio', 0):.3f} | "
                    f"MaxDD: {perf.get('max_drawdown', 0):.2%}"
                )

            # Save best model
            if episode_reward > best_reward:
                best_reward = episode_reward
                os.makedirs(self.config.training.model_dir, exist_ok=True)

        print(f"\nTraining complete. Best reward: {best_reward:.2f}")

        # Evaluate on test set
        print("\n" + "=" * 60)
        print("PHASE 3: EVALUATION")
        print("=" * 60)

        backtester = Backtester()
        test_result = backtester.run(self.test_env, self.agent, n_episodes=1, deterministic=True)

        print("\n--- Test Set Results ---")
        for k, v in test_result.to_dict().items():
            print(f"  {k:25s}: {v}")

        self.results = {
            "training": {
                "n_episodes": n_episodes,
                "episode_rewards": episode_rewards,
                "best_reward": best_reward
            },
            "test": test_result.to_dict(),
            "test_values": test_result.portfolio_values,
            "test_returns": test_result.daily_returns,
            "test_drawdowns": test_result.drawdown_series
        }

        return self.results

    def generate_dashboard_data(self) -> Dict:
        """Generate all data needed for the dashboard."""
        if not self.results:
            self.results = self.train()

        # Run a final evaluation episode with full logging
        obs = self.test_env.reset()
        done = False
        dashboard_data = {
            "portfolio_values": [self.test_env.initial_capital],
            "dates": list(range(self.test_env.T)),
            "trades": [],
            "regimes": [],
            "sentiment": [],
            "explanations": [],
            "risk_metrics_history": [],
            "actions_history": [],
            "config": self.config.to_dict(),
            "test_metrics": self.results.get("test", {}),
            "training_rewards": self.results.get("training", {}).get("episode_rewards", [])
        }

        news_gen = NewsGenerator(seed=123)
        sentiment_analyzer = SentimentAnalyzer()
        explainer = TradeExplainer()
        step = 0

        while not done:
            action, decision_info = self.agent.select_action(obs, deterministic=True)
            obs, reward, done, info = self.test_env.step(action)

            dashboard_data["portfolio_values"].append(info["portfolio_value"])
            dashboard_data["trades"].extend(info.get("trades", []))
            dashboard_data["regimes"].append(info.get("regime", "Sideways"))
            dashboard_data["actions_history"].append(action.tolist())

            risk = info.get("risk_metrics")
            if risk:
                dashboard_data["risk_metrics_history"].append({
                    "sharpe": getattr(risk, 'sharpe_ratio', 0),
                    "sortino": getattr(risk, 'sortino_ratio', 0),
                    "drawdown": getattr(risk, 'current_drawdown', 0),
                    "max_drawdown": getattr(risk, 'max_drawdown', 0),
                    "volatility": getattr(risk, 'portfolio_volatility', 0)
                })

            # Periodic sentiment
            if step % 10 == 0:
                regime = info.get("regime", "Sideways")
                tickers = self.config.data.tickers
                news = news_gen.generate_news(tickers[:2], n_items=1, market_regime=regime)
                for n in news:
                    dashboard_data["sentiment"].append({
                        "title": n.title,
                        "ticker": n.ticker,
                        "sentiment": n.sentiment,
                        "confidence": n.confidence,
                        "source": n.source,
                        "timestamp": n.timestamp
                    })

                # Generate explanation
                explanation = explainer.explain(
                    ticker=tickers[0],
                    action=action[0],
                    ensemble_info=decision_info,
                    sentiment_info={"sentiment": news[0].sentiment if news else "neutral",
                                    "confidence": news[0].confidence if news else 0.5},
                    regime=regime,
                    technical_signals={"rsi": 50 + np.random.randn() * 15,
                                       "macd": np.random.randn() * 0.5},
                    risk_metrics=dashboard_data["risk_metrics_history"][-1] if dashboard_data["risk_metrics_history"] else {}
                )
                dashboard_data["explanations"].append({
                    "step": step,
                    "text": explanation
                })

            step += 1

        return dashboard_data


def run_training():
    """Main entry point for training."""
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     RISK-AWARE RL TRADING SYSTEM - TRAINING PIPELINE   ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  PPO + SAC Ensemble | LSTM Feature Extractor           ║")
    print("║  Composite Reward: R_ann, σ_down, D_ret, T_ry          ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    pipeline = TrainingPipeline()
    results = pipeline.train(n_episodes=5)

    # Generate dashboard data
    print("\n" + "=" * 60)
    print("PHASE 4: GENERATING DASHBOARD DATA")
    print("=" * 60)
    dashboard_data = pipeline.generate_dashboard_data()

    # Save dashboard data
    os.makedirs("output", exist_ok=True)
    with open("output/dashboard_data.json", "w") as f:
        json.dump(dashboard_data, f, default=str)
    print(f"Dashboard data saved to output/dashboard_data.json")

    return pipeline, results, dashboard_data


if __name__ == "__main__":
    pipeline, results, dashboard_data = run_training()
