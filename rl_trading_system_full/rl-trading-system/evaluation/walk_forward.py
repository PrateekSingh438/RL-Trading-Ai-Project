"""
Walk-Forward Backtester
========================
ADD as: evaluation/walk_forward.py

Rolling-window backtesting that prevents look-ahead bias.
Train on window [t-N, t], test on [t, t+K], slide forward.
"""
import numpy as np
from typing import Dict, List
from evaluation.metrics import PerformanceEvaluator


class WalkForwardBacktester:
    """
    Walk-forward validation:
      1. Train on months 1-12, test month 13
      2. Train on months 2-13, test month 14
      3. ... repeat

    This is the gold standard for time-series model evaluation.
    """

    def __init__(
        self,
        train_window: int = 252,   # ~1 year of trading days
        test_window: int = 63,     # ~3 months
        step_size: int = 21,       # ~1 month slide
        min_train_size: int = 126, # ~6 months minimum
    ):
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.min_train_size = min_train_size
        self.evaluator = PerformanceEvaluator()
        self.fold_results: List[Dict] = []

    def generate_splits(self, total_length: int) -> List[Dict]:
        """Generate train/test index splits."""
        splits = []
        start = 0
        while start + self.train_window + self.test_window <= total_length:
            splits.append({
                "train_start": start,
                "train_end": start + self.train_window,
                "test_start": start + self.train_window,
                "test_end": min(start + self.train_window + self.test_window, total_length),
                "fold": len(splits),
            })
            start += self.step_size

        return splits

    def run(self, features, prices, bench_returns, tickers, env_class, agent_class,
            env_kwargs=None, agent_kwargs=None, train_episodes=10):
        """
        Run walk-forward backtest.

        Returns aggregated metrics across all folds.
        """
        env_kwargs = env_kwargs or {}
        agent_kwargs = agent_kwargs or {}

        splits = self.generate_splits(len(prices))
        print(f"Walk-forward: {len(splits)} folds, train={self.train_window}d, test={self.test_window}d")

        all_test_values = []
        all_test_returns = []
        self.fold_results = []

        for split in splits:
            fold = split["fold"]
            ts, te = split["train_start"], split["train_end"]
            vs, ve = split["test_start"], split["test_end"]

            # Train data
            train_data = {
                "features": features[ts:te],
                "prices": prices[ts:te],
                "bench_returns": bench_returns[ts:te],
            }

            # Test data
            test_data = {
                "features": features[vs:ve],
                "prices": prices[vs:ve],
                "bench_returns": bench_returns[vs:ve],
            }

            if len(train_data["prices"]) < self.min_train_size:
                continue
            if len(test_data["prices"]) < 10:
                continue

            # Create train env and agent
            train_env = env_class(
                stock_data=train_data["features"],
                price_data=train_data["prices"],
                benchmark_returns=train_data["bench_returns"],
                tickers=tickers,
                lookback_window=min(30, len(train_data["prices"]) // 4),
                **env_kwargs
            )

            obs = train_env.reset()
            agent = agent_class(obs_dim=len(obs), action_dim=train_env.action_dim, **agent_kwargs)

            # Train
            for ep in range(train_episodes):
                obs = train_env.reset()
                done = False
                while not done:
                    # Support both EnsembleAgent (action, info) and PPOAgent (action, log_prob, value)
                    result = agent.select_action(obs)
                    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
                        # EnsembleAgent: reuse PPO values from decision_info
                        action = result[0]
                        dec = result[1]
                        log_prob = dec.get("ppo_log_prob", 0.0)
                        value = dec.get("ppo_value", 0.0)
                    elif isinstance(result, tuple) and len(result) == 3:
                        action, log_prob, value = result
                    else:
                        action = result if not isinstance(result, tuple) else result[0]
                        log_prob, value = 0.0, 0.0
                    next_obs, reward, done, info = train_env.step(action)
                    agent.store_transition(obs, action, reward, next_obs, done,
                                           value=value, log_prob=log_prob)
                    obs = next_obs
                agent.train()

            # Test
            test_env = env_class(
                stock_data=test_data["features"],
                price_data=test_data["prices"],
                benchmark_returns=test_data["bench_returns"],
                tickers=tickers,
                lookback_window=min(30, len(test_data["prices"]) // 4),
                **env_kwargs
            )

            obs = test_env.reset()
            done = False
            fold_values = [test_env.initial_capital]

            while not done:
                result = agent.select_action(obs, deterministic=True) if 'deterministic' in agent.select_action.__code__.co_varnames else agent.select_action(obs)
                action = result[0] if isinstance(result, tuple) else result
                obs, reward, done, info = test_env.step(action)
                fold_values.append(info["portfolio_value"])

            # Evaluate fold
            fold_values = np.array(fold_values)
            bench_vals = test_env.initial_capital * np.cumprod(
                np.concatenate([[1], 1 + test_data["bench_returns"][:len(fold_values) - 1]])
            )

            fold_result = self.evaluator.evaluate(
                fold_values, bench_vals[:len(fold_values)]
            )

            self.fold_results.append({
                "fold": fold,
                "train_days": te - ts,
                "test_days": ve - vs,
                "return": fold_result.total_return,
                "sharpe": fold_result.sharpe_ratio,
                "max_dd": fold_result.max_drawdown,
                "win_rate": fold_result.win_rate,
            })

            all_test_values.extend(fold_values[1:].tolist())
            all_test_returns.extend(fold_result.daily_returns or [])

            print(f"  Fold {fold}: Return={fold_result.total_return:.2%}, Sharpe={fold_result.sharpe_ratio:.3f}, MaxDD={fold_result.max_drawdown:.2%}")

        # Aggregate
        if not self.fold_results:
            return {"error": "No valid folds"}

        avg_return = np.mean([f["return"] for f in self.fold_results])
        avg_sharpe = np.mean([f["sharpe"] for f in self.fold_results])
        avg_dd = np.mean([f["max_dd"] for f in self.fold_results])
        avg_wr = np.mean([f["win_rate"] for f in self.fold_results])

        print(f"\n  Avg Return: {avg_return:.2%}, Avg Sharpe: {avg_sharpe:.3f}, Avg MaxDD: {avg_dd:.2%}")

        return {
            "n_folds": len(self.fold_results),
            "avg_return": avg_return,
            "avg_sharpe": avg_sharpe,
            "avg_max_drawdown": avg_dd,
            "avg_win_rate": avg_wr,
            "folds": self.fold_results,
        }