"""
Evaluation Metrics
==================
Comprehensive performance evaluation and backtesting.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BacktestResult:
    """Complete backtest result container."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    alpha: float = 0.0
    beta: float = 1.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    portfolio_values: List[float] = None
    daily_returns: List[float] = None
    drawdown_series: List[float] = None
    trades: List[Dict] = None
    benchmark_return: float = 0.0
    n_trades: int = 0
    avg_trade_return: float = 0.0
    max_consecutive_losses: int = 0
    profit_factor: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_return": f"{self.total_return:.2%}",
            "annualized_return": f"{self.annualized_return:.2%}",
            "sharpe_ratio": f"{self.sharpe_ratio:.3f}",
            "sortino_ratio": f"{self.sortino_ratio:.3f}",
            "max_drawdown": f"{self.max_drawdown:.2%}",
            "win_rate": f"{self.win_rate:.2%}",
            "alpha": f"{self.alpha:.4f}",
            "beta": f"{self.beta:.3f}",
            "volatility": f"{self.volatility:.2%}",
            "calmar_ratio": f"{self.calmar_ratio:.3f}",
            "n_trades": self.n_trades,
            "profit_factor": f"{self.profit_factor:.2f}",
            "benchmark_return": f"{self.benchmark_return:.2%}"
        }


class PerformanceEvaluator:
    """Compute all performance metrics."""

    def __init__(self, risk_free_rate: float = 0.04, trading_days: int = 252):
        self.rf = risk_free_rate
        self.trading_days = trading_days
        self.daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1

    def evaluate(
        self,
        portfolio_values: np.ndarray,
        benchmark_values: np.ndarray,
        trades: List[Dict] = None,
        initial_capital: float = 1_000_000.0
    ) -> BacktestResult:
        """Run full evaluation suite."""
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        bench_returns = np.diff(benchmark_values) / benchmark_values[:-1]
        n = len(returns)

        if n < 2:
            return BacktestResult()

        # Total return
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        bench_total = (benchmark_values[-1] - benchmark_values[0]) / benchmark_values[0]

        # Annualized return
        ann_return = (1 + total_return) ** (self.trading_days / n) - 1

        # Sharpe ratio
        excess = returns - self.daily_rf
        sharpe = np.mean(excess) / (np.std(returns) + 1e-10) * np.sqrt(self.trading_days)

        # Sortino ratio
        downside = returns[returns < 0]
        sortino = (np.mean(excess) / (np.std(downside) + 1e-10) * np.sqrt(self.trading_days)
                   if len(downside) > 0 else 0)

        # Max drawdown
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (peak - cumulative) / peak
        max_dd = np.max(drawdowns)

        # Drawdown series
        dd_series = drawdowns.tolist()

        # Beta and Alpha
        min_len = min(len(returns), len(bench_returns))
        r, b = returns[:min_len], bench_returns[:min_len]
        if np.var(b) > 1e-10:
            beta = np.cov(r, b)[0, 1] / np.var(b)
        else:
            beta = 1.0
        alpha = ann_return - (self.rf + beta * (np.mean(b) * self.trading_days - self.rf))

        # Win rate
        win_rate = np.mean(returns > 0)

        # Volatility
        vol = np.std(returns) * np.sqrt(self.trading_days)

        # Calmar ratio
        calmar = ann_return / max_dd if max_dd > 0 else 0

        # Trade-level stats
        n_trades = len(trades) if trades else 0
        avg_trade_ret = 0.0
        max_consec_loss = 0
        profit_factor = 0.0

        if trades:
            trade_returns = []
            consec_losses = 0
            max_cl = 0
            total_profit = 0
            total_loss = 0

            for t in trades:
                tr = t.get("return", 0)
                trade_returns.append(tr)
                if tr < 0:
                    consec_losses += 1
                    max_cl = max(max_cl, consec_losses)
                    total_loss += abs(tr)
                else:
                    consec_losses = 0
                    total_profit += tr

            avg_trade_ret = np.mean(trade_returns) if trade_returns else 0
            max_consec_loss = max_cl
            profit_factor = total_profit / (total_loss + 1e-10)

        return BacktestResult(
            total_return=total_return,
            annualized_return=ann_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            alpha=alpha,
            beta=beta,
            volatility=vol,
            calmar_ratio=calmar,
            portfolio_values=portfolio_values.tolist(),
            daily_returns=returns.tolist(),
            drawdown_series=dd_series,
            trades=trades,
            benchmark_return=bench_total,
            n_trades=n_trades,
            avg_trade_return=avg_trade_ret,
            max_consecutive_losses=max_consec_loss,
            profit_factor=profit_factor
        )


class Backtester:
    """
    Walk-forward backtesting engine.
    Prevents look-ahead bias through strict train/test separation.
    """

    def __init__(self, evaluator: PerformanceEvaluator = None):
        self.evaluator = evaluator or PerformanceEvaluator()

    def run(
        self,
        env,
        agent,
        n_episodes: int = 1,
        deterministic: bool = True
    ) -> BacktestResult:
        """
        Run backtest over the environment.

        Args:
            env: Trading environment
            agent: Trained ensemble agent
            n_episodes: Number of evaluation episodes
            deterministic: Use deterministic policy

        Returns:
            BacktestResult
        """
        all_values = []
        all_trades = []

        for ep in range(n_episodes):
            obs = env.reset()
            done = False
            episode_values = [env.initial_capital]

            while not done:
                if hasattr(agent, 'select_action'):
                    result = agent.select_action(obs, deterministic)
                    if isinstance(result, tuple):
                        action = result[0]
                    else:
                        action = result
                else:
                    action = np.zeros(env.action_dim)

                obs, reward, done, info = env.step(action)
                episode_values.append(info["portfolio_value"])

            all_values.append(episode_values)
            all_trades.extend(env.trades_log)

        # Average across episodes
        min_len = min(len(v) for v in all_values)
        avg_values = np.mean([v[:min_len] for v in all_values], axis=0)

        # Benchmark values
        bench_returns = env.benchmark_returns[:min_len - 1]
        bench_values = env.initial_capital * np.cumprod(np.concatenate([[1], 1 + bench_returns]))

        return self.evaluator.evaluate(avg_values, bench_values[:len(avg_values)], all_trades)
