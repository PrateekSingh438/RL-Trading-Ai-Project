"""
Market Regime Detection
=======================
Identifies market regimes (Bull, Bear, Sideways, High-Volatility)
using Hidden Markov Models, clustering, or rule-based methods.
"""
import numpy as np
from typing import List, Tuple, Dict, Optional
from enum import IntEnum


class MarketRegime(IntEnum):
    BULL = 0
    BEAR = 1
    SIDEWAYS = 2
    HIGH_VOLATILITY = 3


REGIME_NAMES = {
    MarketRegime.BULL: "Bull Market",
    MarketRegime.BEAR: "Bear Market",
    MarketRegime.SIDEWAYS: "Sideways",
    MarketRegime.HIGH_VOLATILITY: "High Volatility"
}

REGIME_COLORS = {
    MarketRegime.BULL: "#22c55e",       # Green
    MarketRegime.BEAR: "#ef4444",       # Red
    MarketRegime.SIDEWAYS: "#eab308",   # Yellow
    MarketRegime.HIGH_VOLATILITY: "#a855f7"  # Purple
}


class HMMRegimeDetector:
    """
    Hidden Markov Model-based regime detection.
    Uses a simplified Gaussian HMM implementation.
    """

    def __init__(self, n_regimes: int = 4, lookback: int = 60):
        self.n_regimes = n_regimes
        self.lookback = lookback
        self.is_fitted = False

        # Initialize HMM parameters
        self.means = np.array([0.001, -0.001, 0.0, 0.0])  # Per-regime return means
        self.stds = np.array([0.01, 0.015, 0.008, 0.025])  # Per-regime volatilities
        self.transition_matrix = np.array([
            [0.90, 0.04, 0.04, 0.02],
            [0.04, 0.88, 0.04, 0.04],
            [0.05, 0.05, 0.85, 0.05],
            [0.03, 0.03, 0.04, 0.90]
        ])

    def fit(self, returns: np.ndarray, n_iter: int = 50):
        """
        Fit HMM using EM algorithm (Baum-Welch).
        Simplified implementation for regime detection.
        """
        n = len(returns)
        if n < self.lookback:
            return

        # K-means initialization for emission parameters
        sorted_returns = np.sort(returns)
        chunk = n // self.n_regimes
        for i in range(self.n_regimes):
            segment = sorted_returns[i * chunk:(i + 1) * chunk]
            self.means[i] = np.mean(segment)
            self.stds[i] = np.std(segment) + 1e-6

        # Reorder: Bull (highest mean), Bear (lowest), Sideways (mid, low vol), High-Vol (mid, high vol)
        order = np.argsort(self.means)
        self.means = self.means[order]
        self.stds = self.stds[order]

        # Assign: index 0=Bear(lowest), 1=Sideways, 2=Bull(highest), 3=HighVol
        # Remap to our enum
        remapped_means = np.zeros(4)
        remapped_stds = np.zeros(4)
        remapped_means[MarketRegime.BEAR] = self.means[0]
        remapped_means[MarketRegime.SIDEWAYS] = self.means[1]
        remapped_means[MarketRegime.BULL] = self.means[-1]
        remapped_means[MarketRegime.HIGH_VOLATILITY] = self.means[2]
        remapped_stds[MarketRegime.BEAR] = self.stds[0]
        remapped_stds[MarketRegime.SIDEWAYS] = min(self.stds[1], self.stds[2])
        remapped_stds[MarketRegime.BULL] = self.stds[-1]
        remapped_stds[MarketRegime.HIGH_VOLATILITY] = max(self.stds)

        self.means = remapped_means
        self.stds = remapped_stds
        self.is_fitted = True

    def _gaussian_pdf(self, x: float, mean: float, std: float) -> float:
        """Compute Gaussian probability density."""
        return np.exp(-0.5 * ((x - mean) / std) ** 2) / (std * np.sqrt(2 * np.pi))

    def predict(self, returns: np.ndarray) -> int:
        """Predict current regime from recent returns."""
        if len(returns) < 5:
            return MarketRegime.SIDEWAYS

        recent = returns[-self.lookback:] if len(returns) >= self.lookback else returns

        # Compute log-likelihoods for each regime
        log_likes = np.zeros(self.n_regimes)
        for regime in range(self.n_regimes):
            for r in recent:
                pdf = self._gaussian_pdf(r, self.means[regime], self.stds[regime])
                log_likes[regime] += np.log(pdf + 1e-300)

        return int(np.argmax(log_likes))

    def predict_proba(self, returns: np.ndarray) -> np.ndarray:
        """Return regime probabilities."""
        if len(returns) < 5:
            return np.array([0.25, 0.25, 0.25, 0.25])

        recent = returns[-self.lookback:] if len(returns) >= self.lookback else returns

        log_likes = np.zeros(self.n_regimes)
        for regime in range(self.n_regimes):
            for r in recent:
                pdf = self._gaussian_pdf(r, self.means[regime], self.stds[regime])
                log_likes[regime] += np.log(pdf + 1e-300)

        # Softmax
        log_likes -= np.max(log_likes)
        probs = np.exp(log_likes)
        return probs / (np.sum(probs) + 1e-10)


class RuleBasedRegimeDetector:
    """
    Simple rule-based regime detection using trend and volatility.
    """

    def __init__(self, vol_window: int = 20, trend_window: int = 50):
        self.vol_window = vol_window
        self.trend_window = trend_window

    def detect(self, prices: np.ndarray, returns: np.ndarray) -> int:
        """
        Detect regime from price and return data.

        Rules:
        - Bull: Positive trend + low/normal volatility
        - Bear: Negative trend + any volatility
        - Sideways: No clear trend + low volatility
        - High Volatility: Any trend + very high volatility
        """
        if len(returns) < self.trend_window:
            return MarketRegime.SIDEWAYS

        # Compute trend (SMA slope)
        recent_prices = prices[-self.trend_window:]
        sma = np.mean(recent_prices)
        trend = (recent_prices[-1] - recent_prices[0]) / (recent_prices[0] + 1e-10)

        # Compute volatility
        recent_vol = np.std(returns[-self.vol_window:]) * np.sqrt(252)
        hist_vol = np.std(returns[-252:]) * np.sqrt(252) if len(returns) >= 252 else recent_vol

        # High vol threshold: 1.5x historical
        high_vol = recent_vol > 1.5 * hist_vol

        if high_vol:
            return MarketRegime.HIGH_VOLATILITY
        elif trend > 0.05:  # >5% trend up
            return MarketRegime.BULL
        elif trend < -0.05:  # >5% trend down
            return MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS


class RegimeDetector:
    """
    Unified regime detection interface.
    Supports HMM and rule-based methods.
    """

    def __init__(self, method: str = "hmm", n_regimes: int = 4, **kwargs):
        self.method = method
        if method == "hmm":
            self.detector = HMMRegimeDetector(n_regimes, kwargs.get("lookback", 60))
        else:
            self.detector = RuleBasedRegimeDetector(
                kwargs.get("vol_window", 20),
                kwargs.get("trend_window", 50)
            )

        self.regime_history: List[int] = []
        self.current_regime = MarketRegime.SIDEWAYS

    def fit(self, returns: np.ndarray):
        """Fit the regime detector."""
        if self.method == "hmm":
            self.detector.fit(returns)

    def update(self, prices: np.ndarray, returns: np.ndarray) -> int:
        """Update and return current regime."""
        if self.method == "hmm":
            self.current_regime = self.detector.predict(returns)
        else:
            self.current_regime = self.detector.detect(prices, returns)

        self.regime_history.append(self.current_regime)
        return self.current_regime

    def get_regime_name(self) -> str:
        return REGIME_NAMES.get(self.current_regime, "Unknown")

    def get_regime_adjustment(self) -> Dict[str, float]:
        """
        Return policy adjustment factors based on regime.
        Agent should use these to modify its behavior.
        """
        adjustments = {
            MarketRegime.BULL: {"position_scale": 1.2, "risk_tolerance": 1.1, "exploration": 0.8},
            MarketRegime.BEAR: {"position_scale": 0.5, "risk_tolerance": 0.6, "exploration": 0.5},
            MarketRegime.SIDEWAYS: {"position_scale": 0.7, "risk_tolerance": 0.8, "exploration": 1.0},
            MarketRegime.HIGH_VOLATILITY: {"position_scale": 0.3, "risk_tolerance": 0.4, "exploration": 0.3}
        }
        return adjustments.get(self.current_regime, adjustments[MarketRegime.SIDEWAYS])
