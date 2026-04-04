"""
Global configuration for the RL Trading System.
All hyperparameters, asset lists, and system settings live here.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os


@dataclass
class DataConfig:
    """Data pipeline configuration."""
    tickers: List[str] = field(default_factory=lambda: ["AAPL", "GOOGL", "MSFT", "NFLX", "TSLA"])
    benchmark: str = "^GSPC"  # S&P 500
    start_date: str = "2018-01-01"
    end_date: str = "2024-12-31"
    train_split: float = 0.8
    indicators: List[str] = field(default_factory=lambda: [
        "rsi", "macd", "macd_signal", "bb_upper", "bb_lower",
        "sma_30", "sma_60", "ema_12", "ema_26",
        "volume_norm", "volatility", "cci", "dmi", "turbulence"
    ])
    lookback_window: int = 20  # LSTM lookback (20 is faster than 60 with minimal accuracy loss)
    risk_free_rate: float = 0.04  # Annual risk-free rate


@dataclass
class TradingConfig:
    """Trading constraints for realism."""
    initial_capital: float = 1_000_000.0
    transaction_cost: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    max_position_pct: float = 0.25  # Max 25% of capital per asset
    max_leverage: float = 1.0  # No leverage by default
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.15  # 15% take profit
    cooldown_steps: int = 3  # Min steps between trades per asset
    max_drawdown_threshold: float = 0.15  # 15% max drawdown halt


@dataclass
class RewardConfig:
    """Composite reward function weights."""
    w1: float = 0.35  # Annualized return weight
    w2: float = 0.25  # Downside deviation penalty
    w3: float = 0.20  # Differential return weight
    w4: float = 0.20  # Treynor ratio weight


@dataclass
class PPOConfig:
    """PPO hyperparameters."""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    n_epochs: int = 4  # reduced from 10 (faster training, still converges)
    batch_size: int = 64
    n_steps: int = 2048
    hidden_dim: int = 256
    lstm_hidden_dim: int = 128
    num_lstm_layers: int = 2


@dataclass
class SACConfig:
    """SAC hyperparameters."""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005  # Soft update coefficient
    alpha: float = 0.2  # Temperature parameter
    auto_alpha: bool = True  # Automatic entropy tuning
    batch_size: int = 64  # reduced from 256 (SAC is NumPy, per-sample loop)
    buffer_size: int = 100_000  # reduced from 1M (faster sampling)
    hidden_dim: int = 256
    lstm_hidden_dim: int = 128
    num_lstm_layers: int = 2
    learning_starts: int = 200  # reduced from 1000 (start learning sooner)


@dataclass
class EnsembleConfig:
    """Ensemble configuration."""
    ppo_weight: float = 0.5
    sac_weight: float = 0.5
    use_meta_policy: bool = False  # If True, use meta-policy network
    meta_hidden_dim: int = 128


@dataclass
class RegimeConfig:
    """Market regime detection configuration."""
    method: str = "hmm"  # "hmm", "kmeans", "rules"
    n_regimes: int = 4  # Bull, Bear, Sideways, High-Vol
    lookback: int = 60
    volatility_window: int = 20
    trend_window: int = 50


@dataclass
class TrainingConfig:
    """Training pipeline configuration."""
    total_timesteps: int = 500_000
    eval_freq: int = 10_000
    save_freq: int = 50_000
    log_dir: str = "logs"
    model_dir: str = "models"
    seed: int = 42
    n_eval_episodes: int = 5
    use_optuna: bool = False
    optuna_n_trials: int = 50
    device: str = "cpu"  # "cpu" or "cuda"


@dataclass
class SystemConfig:
    """Master configuration."""
    data: DataConfig = field(default_factory=DataConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)
    sac: SACConfig = field(default_factory=SACConfig)
    ensemble: EnsembleConfig = field(default_factory=EnsembleConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)

    def to_dict(self) -> dict:
        """Serialize config to dictionary."""
        import dataclasses
        return dataclasses.asdict(self)


# Singleton
CONFIG = SystemConfig()
