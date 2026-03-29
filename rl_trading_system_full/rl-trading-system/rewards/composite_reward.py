"""
Composite Reward Function
=========================
Implements the risk-aware reward:
    R = w1 * R_ann - w2 * sigma_down + w3 * D_ret + w4 * Try

Each component is normalized for comparable magnitudes.
All components are differentiable (a.e.) for RL training.
"""
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RewardComponents:
    """Container for individual reward components."""
    annualized_return: float = 0.0
    downside_deviation: float = 0.0
    differential_return: float = 0.0
    treynor_ratio: float = 0.0
    composite_reward: float = 0.0
    raw_components: Dict = None

    def to_dict(self) -> Dict:
        return {
            "R_ann": self.annualized_return,
            "sigma_down": self.downside_deviation,
            "D_ret": self.differential_return,
            "T_ry": self.treynor_ratio,
            "R_composite": self.composite_reward
        }


class CompositeReward:
    """
    Composite reward function for RL trading agents.

    R = w1 * R_ann - w2 * sigma_down + w3 * D_ret + w4 * T_ry

    All components are normalized to [-1, 1] range for stable training.
    """

    def __init__(
        self,
        w1: float = 0.35,
        w2: float = 0.25,
        w3: float = 0.20,
        w4: float = 0.20,
        risk_free_rate: float = 0.04,
        trading_days: int = 252,
        clip_range: float = 5.0
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        self.clip_range = clip_range
        self.daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1

        # Running statistics for normalization
        self._running_mean = 0.0
        self._running_var = 1.0
        self._count = 0

    def compute_annualized_return(
        self, portfolio_returns: np.ndarray
    ) -> float:
        """
        R_ann = (prod(1 + R_p,t))^(252/T) - 1
        Eq. (2) from the paper.
        """
        T = len(portfolio_returns)
        if T == 0:
            return 0.0
        cumulative = np.prod(1 + portfolio_returns)
        if cumulative <= 0:
            return -1.0
        r_ann = cumulative ** (self.trading_days / T) - 1
        return np.clip(r_ann, -3.0, 3.0)  # Bound per paper Section 4.2

    def compute_downside_deviation(
        self, portfolio_returns: np.ndarray
    ) -> float:
        """
        sigma_down = sqrt(1/T * sum(max(0, -R_p,t)^2))
        Eq. (3) from the paper.
        """
        T = len(portfolio_returns)
        if T == 0:
            return 0.0
        negative_returns = np.minimum(portfolio_returns, 0)
        sigma_down = np.sqrt(np.mean(negative_returns ** 2))
        return sigma_down

    def compute_portfolio_beta(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> float:
        """
        beta_p = Cov(R_p, R_m) / Var(R_m)
        """
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0
        cov = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        var_m = np.var(benchmark_returns)
        if var_m < 1e-10:
            return 1.0
        beta = cov / var_m
        return np.clip(beta, 0.3, 3.0)  # Bound per paper Section 4.2

    def compute_differential_return(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        beta: float
    ) -> float:
        """
        D_ret = (1/beta) * (mu_p - mu_b)
        Eq. (4) from the paper (Simplified Differential Return).
        """
        mu_p = np.mean(portfolio_returns)
        mu_b = np.mean(benchmark_returns)
        if abs(beta) < 1e-10:
            beta = 1.0
        d_ret = (mu_p - mu_b) / beta
        return d_ret

    def compute_treynor_ratio(
        self,
        annualized_return: float,
        beta: float
    ) -> float:
        """
        T_ry = (R_ann - R_f) / beta
        Eq. (5) from the paper.
        """
        if abs(beta) < 1e-10:
            beta = 1.0
        t_ry = (annualized_return - self.risk_free_rate) / beta
        return t_ry

    def normalize_component(self, value: float, scale: float = 1.0) -> float:
        """Normalize a component using tanh for bounded output."""
        return np.tanh(value / (scale + 1e-10))

    def compute(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        normalize: bool = True
    ) -> RewardComponents:
        """
        Compute the full composite reward.

        R = w1 * R_ann - w2 * sigma_down + w3 * D_ret + w4 * T_ry

        Args:
            portfolio_returns: Array of portfolio returns
            benchmark_returns: Array of benchmark returns
            normalize: Whether to normalize components

        Returns:
            RewardComponents with all values
        """
        # Compute raw components
        r_ann = self.compute_annualized_return(portfolio_returns)
        sigma_down = self.compute_downside_deviation(portfolio_returns)
        beta = self.compute_portfolio_beta(portfolio_returns, benchmark_returns)
        d_ret = self.compute_differential_return(portfolio_returns, benchmark_returns, beta)
        t_ry = self.compute_treynor_ratio(r_ann, beta)

        raw = {
            "R_ann": r_ann, "sigma_down": sigma_down,
            "D_ret": d_ret, "T_ry": t_ry, "beta": beta
        }

        if normalize:
            # Normalize to comparable magnitudes using tanh
            r_ann_n = self.normalize_component(r_ann, scale=0.5)
            sigma_down_n = self.normalize_component(sigma_down, scale=0.05)
            d_ret_n = self.normalize_component(d_ret, scale=0.01)
            t_ry_n = self.normalize_component(t_ry, scale=1.0)
        else:
            r_ann_n, sigma_down_n, d_ret_n, t_ry_n = r_ann, sigma_down, d_ret, t_ry

        # Composite reward (Eq. 6)
        reward = (
            self.w1 * r_ann_n
            - self.w2 * sigma_down_n
            + self.w3 * d_ret_n
            + self.w4 * t_ry_n
        )

        # Clip for stability
        reward = np.clip(reward, -self.clip_range, self.clip_range)

        # Update running statistics
        self._count += 1
        delta = reward - self._running_mean
        self._running_mean += delta / self._count
        self._running_var += delta * (reward - self._running_mean)

        return RewardComponents(
            annualized_return=r_ann_n,
            downside_deviation=sigma_down_n,
            differential_return=d_ret_n,
            treynor_ratio=t_ry_n,
            composite_reward=reward,
            raw_components=raw
        )

    def step_reward(
        self,
        portfolio_return: float,
        benchmark_return: float,
        portfolio_history: np.ndarray,
        benchmark_history: np.ndarray
    ) -> float:
        """
        Compute step-level reward using rolling window of returns.
        Designed for use inside the Gym environment's step().
        """
        if len(portfolio_history) < 5:
            # Not enough data for meaningful metrics; use simple return
            return portfolio_return * 100

        components = self.compute(portfolio_history, benchmark_history)
        return components.composite_reward

    def update_weights(self, w1: float, w2: float, w3: float, w4: float):
        """Dynamically update reward weights (for hyperparameter tuning)."""
        self.w1, self.w2, self.w3, self.w4 = w1, w2, w3, w4


class StepRewardShaper:
    """
    Additional reward shaping for stable training.
    Provides immediate feedback signals alongside the composite reward.
    """

    def __init__(self, transaction_cost: float = 0.001):
        self.transaction_cost = transaction_cost

    def shape(
        self,
        composite_reward: float,
        action: np.ndarray,
        prev_action: np.ndarray,
        portfolio_value: float,
        prev_portfolio_value: float
    ) -> float:
        """
        Add shaping terms:
        - Transaction cost penalty for excessive trading
        - Small bonus for profitable trades
        - Penalty for drawdowns
        """
        shaped = composite_reward

        # Turnover penalty (encourages less frequent trading)
        turnover = np.sum(np.abs(action - prev_action))
        shaped -= 0.01 * turnover * self.transaction_cost

        # Value change bonus/penalty
        if prev_portfolio_value > 0:
            pnl_pct = (portfolio_value - prev_portfolio_value) / prev_portfolio_value
            shaped += 0.1 * np.tanh(pnl_pct * 100)

        return shaped
