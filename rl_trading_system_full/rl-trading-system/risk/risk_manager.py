"""
Risk Management Layer
=====================
Operates OUTSIDE the RL agent to enforce hard constraints.
Includes position sizing, drawdown protection, and diversification.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class RiskMetrics:
    """Current risk state of the portfolio."""
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    beta: float = 1.0
    var_95: float = 0.0
    portfolio_volatility: float = 0.0
    is_trading_halted: bool = False
    halt_reason: str = ""


class PositionSizer:
    """
    Position sizing using Kelly Criterion and volatility-based methods.
    """

    def __init__(self, max_position_pct: float = 0.25, max_leverage: float = 1.0):
        self.max_position_pct = max_position_pct
        self.max_leverage = max_leverage

    def kelly_criterion(
        self, win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """
        Kelly fraction: f* = (p * b - q) / b
        where p = win_rate, q = 1-p, b = avg_win/avg_loss
        """
        if avg_loss == 0 or avg_win == 0:
            return 0.0
        b = avg_win / abs(avg_loss)
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        # Half-Kelly for safety
        kelly = max(0, kelly * 0.5)
        return min(kelly, self.max_position_pct)

    def volatility_based_sizing(
        self, target_vol: float, asset_vol: float, capital: float
    ) -> float:
        """
        Size position to achieve target portfolio volatility.
        position_size = (target_vol / asset_vol) * capital
        """
        if asset_vol < 1e-10:
            return 0.0
        fraction = target_vol / asset_vol
        fraction = min(fraction, self.max_position_pct)
        return fraction * capital

    def apply_constraints(
        self,
        raw_positions: np.ndarray,
        capital: float,
        prices: np.ndarray
    ) -> np.ndarray:
        """
        Apply position limits and leverage constraints.

        Args:
            raw_positions: Desired position sizes (shares)
            capital: Available capital
            prices: Current asset prices

        Returns:
            Constrained position sizes
        """
        positions = raw_positions.copy()
        n_assets = len(positions)

        # Per-asset position limit
        for i in range(n_assets):
            max_shares = (self.max_position_pct * capital) / (prices[i] + 1e-10)
            positions[i] = np.clip(positions[i], -max_shares, max_shares)

        # Total leverage constraint
        total_exposure = np.sum(np.abs(positions) * prices)
        if total_exposure > self.max_leverage * capital:
            scale = (self.max_leverage * capital) / (total_exposure + 1e-10)
            positions *= scale

        return positions


class DrawdownProtection:
    """
    Monitor and enforce maximum drawdown limits.
    Halts trading if drawdown exceeds threshold.
    """

    def __init__(self, max_drawdown: float = 0.15, recovery_threshold: float = 0.05):
        self.max_drawdown = max_drawdown
        self.recovery_threshold = recovery_threshold
        self.peak_value = 0.0
        self.is_halted = False

    def update(self, portfolio_value: float) -> Tuple[bool, float]:
        """
        Update drawdown tracking.

        Returns:
            (is_halted, current_drawdown)
        """
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value

        if self.peak_value > 0:
            current_dd = max(0.0, (self.peak_value - portfolio_value) / self.peak_value)
        else:
            current_dd = 0.0
        # Clamp to [0, 1] — portfolio can't have > 100% drawdown for halt purposes
        current_dd = min(current_dd, 1.0)

        if current_dd >= self.max_drawdown:
            self.is_halted = True

        # Recovery: resume if drawdown improves significantly
        if self.is_halted and current_dd < (self.max_drawdown - self.recovery_threshold):
            self.is_halted = False

        return self.is_halted, current_dd


class StopLossTakeProfit:
    """
    Per-position stop-loss and take-profit enforcement.
    """

    def __init__(self, stop_loss_pct: float = 0.05, take_profit_pct: float = 0.15):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.entry_prices: Dict[int, float] = {}

    def record_entry(self, asset_idx: int, price: float):
        """Record entry price for a new position."""
        self.entry_prices[asset_idx] = price

    def check(self, asset_idx: int, current_price: float, position: float) -> str:
        """
        Check if stop-loss or take-profit is triggered.

        Returns:
            "hold", "stop_loss", or "take_profit"
        """
        if asset_idx not in self.entry_prices or position == 0:
            return "hold"

        entry = self.entry_prices[asset_idx]
        if entry == 0:
            return "hold"

        if position > 0:  # Long position
            pnl_pct = (current_price - entry) / entry
        else:  # Short position
            pnl_pct = (entry - current_price) / entry

        if pnl_pct <= -self.stop_loss_pct:
            return "stop_loss"
        elif pnl_pct >= self.take_profit_pct:
            return "take_profit"
        return "hold"

    def clear_position(self, asset_idx: int):
        """Clear entry price when position is closed."""
        self.entry_prices.pop(asset_idx, None)


class CooldownManager:
    """
    Enforce minimum time between trades per asset.
    Prevents over-trading / churning.
    """

    def __init__(self, cooldown_steps: int = 3):
        self.cooldown_steps = cooldown_steps
        self.last_trade_step: Dict[int, int] = {}

    def can_trade(self, asset_idx: int, current_step: int) -> bool:
        """Check if asset is past cooldown period."""
        if asset_idx not in self.last_trade_step:
            return True
        return (current_step - self.last_trade_step[asset_idx]) >= self.cooldown_steps

    def record_trade(self, asset_idx: int, current_step: int):
        """Record that a trade was executed."""
        self.last_trade_step[asset_idx] = current_step


class RiskParityAllocator:
    """
    Risk parity: allocate capital such that each asset
    contributes equally to portfolio risk.
    """

    def compute_weights(self, covariance_matrix: np.ndarray) -> np.ndarray:
        """
        Inverse-volatility weighting (simplified risk parity).
        """
        n = covariance_matrix.shape[0]
        vols = np.sqrt(np.diag(covariance_matrix))
        if np.any(vols < 1e-10):
            return np.ones(n) / n
        inv_vol = 1.0 / vols
        weights = inv_vol / np.sum(inv_vol)
        return weights


class RiskManager:
    """
    Unified risk management layer.
    Coordinates all risk components and modifies agent actions.
    """

    def __init__(
        self,
        n_assets: int,
        max_position_pct: float = 0.25,
        max_leverage: float = 1.0,
        max_drawdown: float = 0.15,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.15,
        cooldown_steps: int = 3,
        transaction_cost: float = 0.001
    ):
        self.n_assets = n_assets
        self.transaction_cost = transaction_cost

        self.position_sizer = PositionSizer(max_position_pct, max_leverage)
        self.drawdown_protection = DrawdownProtection(max_drawdown)
        self.sltp = StopLossTakeProfit(stop_loss_pct, take_profit_pct)
        self.cooldown = CooldownManager(cooldown_steps)
        self.risk_parity = RiskParityAllocator()

        # Tracking
        self.portfolio_values: List[float] = []
        self.returns_history: List[float] = []
        self.risk_metrics = RiskMetrics()

    def process_actions(
        self,
        raw_actions: np.ndarray,
        current_prices: np.ndarray,
        current_positions: np.ndarray,
        portfolio_value: float,
        step: int
    ) -> Tuple[np.ndarray, RiskMetrics]:
        """
        Process RL agent actions through risk management layer.

        Args:
            raw_actions: Actions from RL agent [-1, 1] per asset
            current_prices: Current asset prices
            current_positions: Current position sizes
            portfolio_value: Current portfolio value
            step: Current time step

        Returns:
            (modified_actions, risk_metrics)
        """
        actions = raw_actions.copy()

        # 1. Check drawdown halt
        is_halted, current_dd = self.drawdown_protection.update(portfolio_value)
        if is_halted:
            # Force close all positions
            self.risk_metrics.is_trading_halted = True
            self.risk_metrics.halt_reason = f"Max drawdown exceeded: {current_dd:.2%}"
            # Set actions to flatten positions
            for i in range(self.n_assets):
                if current_positions[i] > 0:
                    actions[i] = -1.0  # Sell
                elif current_positions[i] < 0:
                    actions[i] = 1.0  # Cover
                else:
                    actions[i] = 0.0
            return actions, self.risk_metrics

        self.risk_metrics.is_trading_halted = False

        # 2. Check stop-loss / take-profit per asset
        for i in range(self.n_assets):
            signal = self.sltp.check(i, current_prices[i], current_positions[i])
            if signal == "stop_loss":
                actions[i] = -np.sign(current_positions[i])  # Close position
                self.sltp.clear_position(i)
            elif signal == "take_profit":
                actions[i] = -np.sign(current_positions[i]) * 0.5  # Partial close

        # 3. Enforce cooldown
        for i in range(self.n_assets):
            if not self.cooldown.can_trade(i, step):
                # Reduce action magnitude during cooldown
                actions[i] *= 0.1

        # 4. Apply position constraints
        # Use abs value so a negative portfolio_value doesn't flip action signs
        effective_value = max(abs(portfolio_value), 1.0)
        target_positions = actions * (effective_value / (current_prices + 1e-10))
        constrained = self.position_sizer.apply_constraints(
            target_positions, effective_value, current_prices
        )
        # Convert back to [-1, 1] actions
        max_pos = (self.position_sizer.max_position_pct * effective_value) / (current_prices + 1e-10)
        for i in range(self.n_assets):
            if max_pos[i] > 0:
                actions[i] = np.clip(constrained[i] / max_pos[i], -1, 1)

        # 5. Update tracking
        self.portfolio_values.append(portfolio_value)
        if len(self.portfolio_values) > 1:
            ret = (portfolio_value - self.portfolio_values[-2]) / self.portfolio_values[-2]
            self.returns_history.append(ret)

        # 6. Update risk metrics
        self.risk_metrics.current_drawdown = current_dd
        self.risk_metrics.max_drawdown = max(
            self.risk_metrics.max_drawdown, current_dd
        )
        self.risk_metrics.peak_value = self.drawdown_protection.peak_value

        if len(self.returns_history) > 20:
            rets = np.array(self.returns_history[-252:])
            rf_daily = (1 + 0.04) ** (1/252) - 1
            excess = rets - rf_daily
            self.risk_metrics.sharpe_ratio = (
                np.mean(excess) / (np.std(rets) + 1e-10) * np.sqrt(252)
            )
            downside = rets[rets < 0]
            if len(downside) > 0:
                self.risk_metrics.sortino_ratio = (
                    np.mean(excess) / (np.std(downside) + 1e-10) * np.sqrt(252)
                )
            self.risk_metrics.portfolio_volatility = np.std(rets) * np.sqrt(252)

        # Record trades for cooldown
        for i in range(self.n_assets):
            if abs(actions[i]) > 0.1:
                self.cooldown.record_trade(i, step)
                if current_positions[i] == 0 and abs(actions[i]) > 0.1:
                    self.sltp.record_entry(i, current_prices[i])

        return actions, self.risk_metrics
