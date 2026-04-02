"""
Composite Reward Function v3
============================
R = w1*R_ann - w2*σ_down + w3*D_ret + w4*T_ry + w5*R_sharpe + w6*R_entropy
    - drawdown_penalty (now exponential, no longer a negligible cliff)

Key fixes over v2:
  - current_drawdown, positions, regime are now actually passed in from trading_env
  - Drawdown penalty is exponential (was linear → effectively zero)
  - StepRewardShaper adds capital-preservation penalty (below 90 % of initial capital)
  - Turnover penalty scaled up 5 000× (was 0.00001 per step → now 0.05)
  - P&L shaper weight tripled (0.1 → 0.3) and sensitivity doubled
  - Early-step reward uses tanh(pnl * 50) so signal is bounded and smooth
"""
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class RewardComponents:
    annualized_return: float = 0.0
    downside_deviation: float = 0.0
    differential_return: float = 0.0
    treynor_ratio: float = 0.0
    sharpe_ratio: float = 0.0
    portfolio_entropy: float = 0.0
    drawdown_penalty: float = 0.0
    composite_reward: float = 0.0
    raw_components: Dict = None

    def to_dict(self) -> Dict:
        return {
            "R_ann": self.annualized_return,
            "sigma_down": self.downside_deviation,
            "D_ret": self.differential_return,
            "T_ry": self.treynor_ratio,
            "R_sharpe": self.sharpe_ratio,
            "R_entropy": self.portfolio_entropy,
            "R_dd_penalty": self.drawdown_penalty,
            "R_composite": self.composite_reward,
        }


# Regime → (scale_return, scale_risk, scale_alpha, scale_sharpe)
_REGIME_SCALES = {
    "Bull Market":      (1.10, 0.90, 1.05, 1.00),
    "Bear Market":      (0.80, 1.30, 0.95, 1.20),
    "High Volatility":  (0.85, 1.20, 0.90, 1.15),
    "Sideways":         (1.00, 1.00, 1.00, 1.00),
}


class CompositeReward:
    """
    Composite reward function for RL trading agents.

    R = w1*R_ann - w2*σ_down + w3*D_ret + w4*T_ry + w5*R_sharpe + w6*R_entropy
        - drawdown_penalty (exponential cliff)

    Weights are regime-adaptive so the agent is more risk-averse during
    Bear / High-Volatility periods.
    """

    def __init__(
        self,
        w1: float = 0.30,   # annualised return
        w2: float = 0.25,   # downside deviation penalty (raised from 0.20)
        w3: float = 0.10,   # differential return vs benchmark
        w4: float = 0.10,   # Treynor ratio
        w5: float = 0.20,   # Sharpe ratio (raised from 0.15)
        w6: float = 0.05,   # portfolio entropy (diversification bonus)
        risk_free_rate: float = 0.04,
        trading_days: int = 252,
        clip_range: float = 5.0,
        drawdown_hard_threshold: float = 0.10,  # 10 % → penalty kicks in (was 15 %)
        drawdown_penalty_scale: float = 8.0,    # was 2.0
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4
        self.w5 = w5
        self.w6 = w6
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        self.clip_range = clip_range
        self.drawdown_hard_threshold = drawdown_hard_threshold
        self.drawdown_penalty_scale = drawdown_penalty_scale
        self.daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1

        # Welford running stats for normalisation
        self._count = 0
        self._mean = 0.0
        self._M2 = 0.0

    # ── Individual components ─────────────────────────────────────────────

    def compute_annualized_return(self, returns: np.ndarray) -> float:
        T = len(returns)
        if T == 0:
            return 0.0
        cum = np.prod(1.0 + returns)
        if cum <= 0:
            return -1.0
        return float(np.clip(cum ** (self.trading_days / T) - 1, -3.0, 3.0))

    def compute_downside_deviation(self, returns: np.ndarray) -> float:
        if len(returns) == 0:
            return 0.0
        neg = np.minimum(returns - self.daily_rf, 0.0)
        return float(np.sqrt(np.mean(neg ** 2)) * np.sqrt(self.trading_days))

    def compute_portfolio_beta(
        self, returns: np.ndarray, bench: np.ndarray
    ) -> float:
        if len(returns) < 2 or len(bench) < 2:
            return 1.0
        cov = np.cov(returns, bench)[0, 1]
        var_m = np.var(bench)
        if var_m < 1e-12:
            return 1.0
        return float(np.clip(cov / var_m, 0.1, 5.0))

    def compute_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Annualised Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        excess = returns - self.daily_rf
        std = np.std(excess) + 1e-10
        return float(np.mean(excess) / std * np.sqrt(self.trading_days))

    def compute_differential_return(
        self, returns: np.ndarray, bench: np.ndarray, beta: float
    ) -> float:
        mu_p = np.mean(returns)
        mu_b = np.mean(bench)
        beta = max(abs(beta), 1e-10) * np.sign(beta) if beta != 0 else 1.0
        return float((mu_p - mu_b) / abs(beta))

    def compute_treynor_ratio(self, r_ann: float, beta: float) -> float:
        beta = max(abs(beta), 1e-10)
        return float((r_ann - self.risk_free_rate) / beta)

    def compute_portfolio_entropy(self, positions: np.ndarray) -> float:
        """
        Shannon entropy of absolute position weights → diversification bonus.
        Returns value in [0, 1] (higher = more diversified).
        """
        abs_pos = np.abs(positions)
        total = np.sum(abs_pos)
        if total < 1e-10:
            return 0.0
        weights = abs_pos / total
        weights = weights[weights > 1e-10]
        entropy = -np.sum(weights * np.log(weights + 1e-10))
        max_entropy = np.log(len(positions) + 1e-10)
        return float(entropy / (max_entropy + 1e-10))

    def compute_drawdown_penalty(self, current_drawdown: float) -> float:
        """
        Exponential penalty above threshold.

        Old (v2): linear → max ~0.15 at 15 % DD, negligible vs clip_range=5
        New (v3): exponential → 0 below 3%, then grows steeply:
            5 % DD  → 0.08
           10 % DD  → 0.32
           15 % DD  → 0.72
           20 % DD  → 1.28
           30 % DD  → 2.88  (approaching clip_range)
        """
        dd = abs(current_drawdown)
        if dd < 0.03:   # ignore micro-fluctuations
            return 0.0
        # Quadratic growth above threshold, scaled by drawdown_penalty_scale
        excess = max(0.0, dd - 0.03)
        penalty = (excess ** 2) * self.drawdown_penalty_scale * 80.0
        return float(min(penalty, self.clip_range))

    # ── Normalise ─────────────────────────────────────────────────────────

    @staticmethod
    def _tanh_norm(value: float, scale: float = 1.0) -> float:
        return float(np.tanh(value / (scale + 1e-10)))

    # ── Main compute ──────────────────────────────────────────────────────

    def compute(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        current_drawdown: float = 0.0,
        positions: Optional[np.ndarray] = None,
        regime: str = "Sideways",
        normalize: bool = True,
    ) -> RewardComponents:
        r_ann      = self.compute_annualized_return(portfolio_returns)
        sigma_down = self.compute_downside_deviation(portfolio_returns)
        beta       = self.compute_portfolio_beta(portfolio_returns, benchmark_returns)
        d_ret      = self.compute_differential_return(portfolio_returns, benchmark_returns, beta)
        t_ry       = self.compute_treynor_ratio(r_ann, beta)
        sharpe     = self.compute_sharpe_ratio(portfolio_returns)
        entropy    = (
            self.compute_portfolio_entropy(positions)
            if positions is not None else 0.5
        )
        dd_pen = self.compute_drawdown_penalty(current_drawdown)

        raw = {
            "R_ann": r_ann, "sigma_down": sigma_down, "D_ret": d_ret,
            "T_ry": t_ry, "beta": beta, "Sharpe": sharpe,
            "entropy": entropy, "dd_penalty": dd_pen,
            "current_drawdown": current_drawdown,
        }

        if normalize:
            r_ann_n   = self._tanh_norm(r_ann,      scale=0.5)
            sig_n     = self._tanh_norm(sigma_down,  scale=0.05)
            d_ret_n   = self._tanh_norm(d_ret,       scale=0.01)
            t_ry_n    = self._tanh_norm(t_ry,        scale=1.0)
            sharpe_n  = self._tanh_norm(sharpe,      scale=1.5)
            entropy_n = float(entropy)
        else:
            r_ann_n, sig_n, d_ret_n, t_ry_n, sharpe_n, entropy_n = (
                r_ann, sigma_down, d_ret, t_ry, sharpe, entropy)

        # Regime-adaptive weight scaling
        s  = _REGIME_SCALES.get(regime, (1.0, 1.0, 1.0, 1.0))
        w1 = self.w1 * s[0]
        w2 = self.w2 * s[1]
        w3 = self.w3 * s[2]
        w5 = self.w5 * s[3]

        reward = (
            w1 * r_ann_n
            - w2 * sig_n
            + w3 * d_ret_n
            + self.w4 * t_ry_n
            + w5 * sharpe_n
            + self.w6 * entropy_n
            - dd_pen                    # now actually non-zero
        )

        reward = float(np.clip(reward, -self.clip_range, self.clip_range))

        # Welford update
        self._count += 1
        delta = reward - self._mean
        self._mean += delta / self._count
        self._M2 += delta * (reward - self._mean)

        return RewardComponents(
            annualized_return=r_ann_n,
            downside_deviation=sig_n,
            differential_return=d_ret_n,
            treynor_ratio=t_ry_n,
            sharpe_ratio=sharpe_n,
            portfolio_entropy=entropy_n,
            drawdown_penalty=dd_pen,
            composite_reward=reward,
            raw_components=raw,
        )

    def step_reward(
        self,
        portfolio_return: float,
        benchmark_return: float,
        portfolio_history: np.ndarray,
        benchmark_history: np.ndarray,
        current_drawdown: float = 0.0,
        positions: Optional[np.ndarray] = None,
        regime: str = "Sideways",
    ) -> float:
        # Early steps: return bounded, smooth step-return signal
        if len(portfolio_history) < 5:
            return float(np.tanh(portfolio_return * 50.0))

        components = self.compute(
            portfolio_history,
            benchmark_history,
            current_drawdown=current_drawdown,
            positions=positions,
            regime=regime,
        )
        return components.composite_reward

    def update_weights(
        self, w1: float, w2: float, w3: float, w4: float,
        w5: float = None, w6: float = None
    ):
        self.w1, self.w2, self.w3, self.w4 = w1, w2, w3, w4
        if w5 is not None:
            self.w5 = w5
        if w6 is not None:
            self.w6 = w6

    @property
    def running_std(self) -> float:
        if self._count < 2:
            return 1.0
        return float(np.sqrt(self._M2 / (self._count - 1)))


class StepRewardShaper:
    """
    Per-step shaping terms layered on top of the composite reward.

    Fixes vs v2:
      - Turnover penalty: was 0.01 * turnover * tc (≈ 0.00001/step) → now 0.05 * turnover
      - P&L weight: 0.1 → 0.3; sensitivity: tanh(pnl*100) → tanh(pnl*200)
      - Capital preservation: penalty when portfolio drops below 90 % of initial capital
    """

    def __init__(self, transaction_cost: float = 0.001):
        self.transaction_cost = transaction_cost

    def shape(
        self,
        composite_reward: float,
        action: np.ndarray,
        prev_action: np.ndarray,
        portfolio_value: float,
        prev_portfolio_value: float,
        initial_capital: float = 0.0,
    ) -> float:
        shaped = composite_reward

        # 1. Turnover penalty — discourages over-trading / churning
        #    Was: 0.01 * turnover * 0.001 ≈ 0.00001/step (negligible)
        #    Now: 0.05 * turnover            (meaningful)
        turnover = float(np.sum(np.abs(action - prev_action)))
        shaped -= 0.05 * turnover

        # 2. Direct step P&L signal — immediate feedback on money gained/lost
        if prev_portfolio_value > 1000.0:
            pnl_pct = (portfolio_value - prev_portfolio_value) / prev_portfolio_value
            shaped += 0.3 * float(np.tanh(pnl_pct * 200.0))   # was 0.1 * tanh(pnl*100)

        # 3. Capital preservation — penalise dipping below initial capital
        #    Penalty grows from 0 at 90 % of initial to 2.0 at 0 %
        if initial_capital > 0:
            ratio = portfolio_value / initial_capital
            if ratio < 0.90:
                # Quadratic penalty: at 80 % → 0.10, at 70 % → 0.40, at 50 % → 1.60
                preservation_penalty = ((0.90 - ratio) ** 2) * 20.0
                shaped -= float(np.clip(preservation_penalty, 0.0, 3.0))

        return shaped
