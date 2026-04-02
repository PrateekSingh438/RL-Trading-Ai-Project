"""
Multi-Asset Trading Environment
================================
Gym-compatible environment for RL-based multi-stock trading.
Integrates reward function, risk management, and regime detection.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import json


class TradingEnv:
    """
    OpenAI Gym-style multi-asset trading environment.

    Observation Space:
        [portfolio_value, cash, positions..., prices..., indicators..., regime_features...]

    Action Space:
        Continuous [-1, 1] per asset: -1 = full short, 0 = neutral, 1 = full long
    """

    def __init__(
        self,
        stock_data: np.ndarray,       # Shape: (T, n_assets, n_features)
        price_data: np.ndarray,        # Shape: (T, n_assets) - close prices
        benchmark_returns: np.ndarray,  # Shape: (T,)
        tickers: List[str],
        initial_capital: float = 1_000_000.0,
        transaction_cost: float = 0.001,
        slippage: float = 0.0005,
        max_position_pct: float = 0.25,
        max_leverage: float = 1.0,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.15,
        cooldown_steps: int = 3,
        max_drawdown_threshold: float = 0.15,
        reward_weights: Tuple[float, ...] = (0.35, 0.25, 0.20, 0.20),
        risk_free_rate: float = 0.04,
        lookback_window: int = 60
    ):
        self.stock_data = stock_data
        self.price_data = price_data
        self.benchmark_returns = benchmark_returns
        self.tickers = tickers
        self.n_assets = len(tickers)
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.lookback_window = lookback_window
        self.risk_free_rate = risk_free_rate

        self.T = len(price_data)

        # Import components
        from rewards.composite_reward import CompositeReward, StepRewardShaper
        from risk.risk_manager import RiskManager
        from regime.detector import RegimeDetector

        # Reward function
        self.reward_fn = CompositeReward(
            w1=reward_weights[0], w2=reward_weights[1],
            w3=reward_weights[2], w4=reward_weights[3],
            risk_free_rate=risk_free_rate
        )
        self.reward_shaper = StepRewardShaper(transaction_cost)

        # Risk manager
        self.risk_manager = RiskManager(
            n_assets=self.n_assets,
            max_position_pct=max_position_pct,
            max_leverage=max_leverage,
            max_drawdown=max_drawdown_threshold,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            cooldown_steps=cooldown_steps,
            transaction_cost=transaction_cost
        )

        # Regime detector
        self.regime_detector = RegimeDetector(method="rules")

        # Spaces
        n_features = stock_data.shape[2] if len(stock_data.shape) == 3 else stock_data.shape[1]
        # obs: cash + positions + prices + features + regime_one_hot
        self.obs_dim = 1 + self.n_assets + self.n_assets + (n_features * self.n_assets) + 4
        self.action_dim = self.n_assets

        # State
        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.current_step = self.lookback_window
        self.cash = self.initial_capital
        self.positions = np.zeros(self.n_assets)  # Shares held
        self.portfolio_value = self.initial_capital
        self.prev_portfolio_value = self.initial_capital
        self.prev_actions = np.zeros(self.n_assets)

        # History tracking
        self.portfolio_history = [self.initial_capital]
        self.returns_history = []
        self.actions_history = []
        self.trades_log = []
        self.regime_history = []

        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """Construct observation vector."""
        prices = self.price_data[self.current_step]

        # Normalize relative to initial_capital (stable anchor), not current portfolio value.
        # Using max(portfolio_value, 1.0) caused observations to blow up 1000× when
        # the portfolio shrank, destabilising the neural network.
        norm_factor = max(self.portfolio_value, self.initial_capital * 0.1)
        obs_parts = [
            np.array([self.cash / norm_factor]),           # Normalized cash
            self.positions * prices / norm_factor,          # Normalized position values
            prices / (prices.mean() + 1e-10),               # Normalized prices
        ]

        # Add features for each asset
        if len(self.stock_data.shape) == 3:
            features = self.stock_data[self.current_step].flatten()
        else:
            features = self.stock_data[self.current_step]
        obs_parts.append(features)

        # Add regime one-hot
        if len(self.returns_history) > 20:
            returns_arr = np.array(self.returns_history)
            prices_arr = np.array(self.portfolio_history)
            regime = self.regime_detector.update(prices_arr, returns_arr)
        else:
            regime = 2  # Sideways default
        regime_onehot = np.zeros(4)
        regime_onehot[regime] = 1.0
        obs_parts.append(regime_onehot)

        obs = np.concatenate(obs_parts).astype(np.float32)
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        return obs

    def step(self, actions: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one trading step.

        Args:
            actions: Array of actions [-1, 1] per asset

        Returns:
            (observation, reward, done, info)
        """
        actions = np.clip(actions, -1, 1)
        prices = self.price_data[self.current_step]

        # 1. Pass through risk management
        modified_actions, risk_metrics = self.risk_manager.process_actions(
            raw_actions=actions,
            current_prices=prices,
            current_positions=self.positions,
            portfolio_value=self.portfolio_value,
            step=self.current_step
        )

        # 2. Apply regime-based adjustment
        adjustment = self.regime_detector.get_regime_adjustment()
        modified_actions *= adjustment["position_scale"]

        # 3. Execute trades
        trade_info = self._execute_trades(modified_actions, prices)

        # 4. Advance time
        self.current_step += 1
        done = self.current_step >= self.T - 1

        # 5. Compute new portfolio value
        if not done:
            new_prices = self.price_data[self.current_step]
        else:
            new_prices = prices
        self.portfolio_value = self.cash + np.sum(np.maximum(self.positions, 0) * new_prices)
        self.portfolio_value = max(self.portfolio_value, 0.0)  # hard floor
        self.portfolio_history.append(self.portfolio_value)

        # 6. Compute return
        if self.prev_portfolio_value > 1.0:
            step_return = (self.portfolio_value - self.prev_portfolio_value) / self.prev_portfolio_value
        else:
            step_return = 0.0
        self.returns_history.append(step_return)

        # 7. Compute reward
        portfolio_returns = np.array(self.returns_history)
        benchmark_rets = self.benchmark_returns[
            max(0, self.current_step - len(portfolio_returns)):self.current_step
        ]
        if len(benchmark_rets) < len(portfolio_returns):
            benchmark_rets = np.zeros(len(portfolio_returns))

        # Compute running peak and current drawdown for reward function.
        # BUG FIX: current_drawdown was never passed before → drawdown penalty was always 0.
        peak_pv = max(self.portfolio_history) if self.portfolio_history else self.initial_capital
        current_drawdown = max(0.0, (peak_pv - self.portfolio_value) / max(peak_pv, 1.0))

        reward = self.reward_fn.step_reward(
            portfolio_return=step_return,
            benchmark_return=self.benchmark_returns[min(self.current_step, len(self.benchmark_returns) - 1)],
            portfolio_history=portfolio_returns,
            benchmark_history=benchmark_rets,
            current_drawdown=current_drawdown,          # was always 0.0 before
            positions=self.positions,                    # enables entropy bonus
            regime=str(self.regime_detector.get_regime_name()),
        )

        # Shape reward
        reward = self.reward_shaper.shape(
            composite_reward=reward,
            action=modified_actions,
            prev_action=self.prev_actions,
            portfolio_value=self.portfolio_value,
            prev_portfolio_value=self.prev_portfolio_value,
            initial_capital=self.initial_capital,        # enables capital preservation signal
        )

        # 8. Update state
        self.prev_portfolio_value = self.portfolio_value
        self.prev_actions = modified_actions.copy()
        self.actions_history.append(modified_actions.copy())

        # 9. Info dict
        info = {
            "portfolio_value": self.portfolio_value,
            "cash": self.cash,
            "positions": self.positions.copy(),
            "step_return": step_return,
            "risk_metrics": risk_metrics,
            "regime": self.regime_detector.get_regime_name(),
            "trades": trade_info,
            "total_return": (self.portfolio_value - self.initial_capital) / self.initial_capital
        }

        obs = self._get_observation() if not done else np.zeros(self.obs_dim)
        return obs, reward, done, info

    def _execute_trades(self, actions: np.ndarray, prices: np.ndarray) -> List[Dict]:
        """
        Execute trades with transaction costs and slippage.
        Long-only mode: no short positions, cash never goes negative.

        Returns list of executed trades.
        """
        trades = []
        effective_value = max(self.portfolio_value, self.initial_capital * 0.01)
        for i in range(self.n_assets):
            action = actions[i]
            price = prices[i]

            # Long-only: positive action = buy, negative = reduce/sell existing position
            max_shares = (0.25 * effective_value) / (price + 1e-10)
            if action >= 0:
                target_shares = action * max_shares
            else:
                # Scale down to zero: action -1 = sell all, action 0 = hold
                target_shares = max(0.0, self.positions[i] + action * self.positions[i])

            delta_shares = target_shares - self.positions[i]

            # Can never sell more shares than we own (no shorting)
            if delta_shares < 0:
                delta_shares = max(delta_shares, -self.positions[i])

            if abs(delta_shares) < 0.01:
                continue

            # Apply slippage
            if delta_shares > 0:
                exec_price = price * (1 + self.slippage)
            else:
                exec_price = price * (1 - self.slippage)

            if delta_shares > 0:
                cost = abs(delta_shares * exec_price) * self.transaction_cost
                total_cost = delta_shares * exec_price + cost
                available_cash = max(self.cash, 0.0)
                if total_cost > available_cash:
                    delta_shares = available_cash / (exec_price * (1 + self.transaction_cost) + 1e-10)
                    delta_shares = max(0.0, delta_shares)
                    cost = delta_shares * exec_price * self.transaction_cost
            else:
                cost = abs(delta_shares * exec_price) * self.transaction_cost

            if abs(delta_shares) < 0.001:
                continue

            self.cash -= delta_shares * exec_price + cost
            self.cash = max(self.cash, 0.0)  # cash never goes negative in long-only mode
            self.positions[i] += delta_shares
            self.positions[i] = max(self.positions[i], 0.0)  # safety clamp

            trade = {
                "ticker": self.tickers[i] if i < len(self.tickers) else f"Asset_{i}",
                "action": "BUY" if delta_shares > 0 else "SELL",
                "shares": abs(delta_shares),
                "price": exec_price,
                "cost": cost,
                "step": self.current_step
            }
            trades.append(trade)
            self.trades_log.append(trade)

        return trades

    def get_performance_summary(self) -> Dict:
        """Compute comprehensive performance metrics."""
        if len(self.returns_history) < 2:
            return {}

        returns = np.array(self.returns_history)
        rf_daily = (1 + self.risk_free_rate) ** (1/252) - 1

        # Annualized return
        cum_return = self.portfolio_value / self.initial_capital
        n_days = len(returns)
        ann_return = cum_return ** (252 / n_days) - 1

        # Sharpe
        excess = returns - rf_daily
        sharpe = np.mean(excess) / (np.std(returns) + 1e-10) * np.sqrt(252)

        # Sortino
        downside = returns[returns < 0]
        sortino = np.mean(excess) / (np.std(downside) + 1e-10) * np.sqrt(252) if len(downside) > 0 else 0

        # Max drawdown
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (peak - cumulative) / peak
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0

        # Win rate
        win_rate = np.mean(returns > 0) if len(returns) > 0 else 0

        # Beta
        bench = self.benchmark_returns[:len(returns)]
        if len(bench) == len(returns) and np.var(bench) > 1e-10:
            beta = np.cov(returns, bench)[0, 1] / np.var(bench)
        else:
            beta = 1.0

        # Alpha
        alpha = ann_return - (rf_daily * 252 + beta * (np.mean(bench) * 252 - rf_daily * 252))

        return {
            "total_return": (self.portfolio_value - self.initial_capital) / self.initial_capital,
            "annualized_return": ann_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "beta": beta,
            "alpha": alpha,
            "portfolio_value": self.portfolio_value,
            "n_trades": len(self.trades_log),
            "volatility": np.std(returns) * np.sqrt(252)
        }
