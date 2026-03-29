"""
Additional Technical Indicators + Feature Importance
=====================================================
ADD this file as: data/indicators.py

Adds: ATR, OBV, Ichimoku Cloud, Stochastic Oscillator, VWAP proxy
Also provides permutation-based feature importance.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


# ─── Additional Indicators ─────────────────────────────────

def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — measures volatility."""
    if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame): low = low.iloc[:, 0]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume — cumulative volume flow."""
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    if isinstance(volume, pd.DataFrame): volume = volume.iloc[:, 0]
    direction = np.sign(close.diff())
    obv = (volume * direction).cumsum()
    # Normalize to prevent huge values
    return obv / (obv.abs().rolling(60).max() + 1e-10)


def compute_ichimoku(high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Ichimoku Cloud — returns (tenkan_sen, kijun_sen, cloud_thickness).
    Cloud thickness = Senkou Span A - Senkou Span B (positive = bullish cloud).
    """
    if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame): low = low.iloc[:, 0]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]

    # Tenkan-sen (conversion line): 9-period midpoint
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2

    # Kijun-sen (base line): 26-period midpoint
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2

    # Senkou Span A: midpoint of tenkan and kijun, shifted 26 periods ahead
    span_a = ((tenkan + kijun) / 2).shift(26)

    # Senkou Span B: 52-period midpoint, shifted 26 periods ahead
    span_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    # Cloud thickness (positive = bullish)
    cloud = span_a - span_b

    return tenkan, kijun, cloud.fillna(0)


def compute_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                       k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator (%K and %D)."""
    if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame): low = low.iloc[:, 0]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]

    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
    d = k.rolling(d_period).mean()
    return k, d


def add_extra_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add ATR, OBV, Ichimoku, Stochastic to an existing DataFrame."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]

    def to_s(col):
        s = df[col]
        return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s

    close = to_s("Close") if "Close" in df.columns else to_s("Adj Close")
    high = to_s("High")
    low = to_s("Low")
    volume = to_s("Volume")

    df = df.copy()
    df["atr"] = compute_atr(high, low, close)
    df["obv"] = compute_obv(close, volume)
    tenkan, kijun, cloud = compute_ichimoku(high, low, close)
    df["ichimoku_tenkan"] = tenkan
    df["ichimoku_kijun"] = kijun
    df["ichimoku_cloud"] = cloud
    stoch_k, stoch_d = compute_stochastic(high, low, close)
    df["stoch_k"] = stoch_k
    df["stoch_d"] = stoch_d

    return df


# ─── Feature Importance ───────────────────────────────────

def compute_feature_importance(
    observation: np.ndarray,
    feature_names: List[str],
    agent,
    n_perturbations: int = 20
) -> Dict[str, float]:
    """
    Permutation-based feature importance (SHAP-like).
    Measures how much each feature affects the action output.
    """
    if len(feature_names) > len(observation):
        feature_names = feature_names[:len(observation)]
    elif len(feature_names) < len(observation):
        feature_names = feature_names + [f"feat_{i}" for i in range(len(feature_names), len(observation))]

    baseline_action, _, _ = agent.select_action(observation, deterministic=True)
    baseline_mag = np.sum(np.abs(baseline_action))

    importance = {}
    for i, name in enumerate(feature_names[:min(30, len(feature_names))]):
        deltas = []
        for _ in range(n_perturbations):
            perturbed = observation.copy()
            perturbed[i] = np.random.normal(0, 1)  # Replace with random
            perturbed_action, _, _ = agent.select_action(perturbed, deterministic=True)
            delta = np.sum(np.abs(perturbed_action - baseline_action))
            deltas.append(delta)
        importance[name] = float(np.mean(deltas))

    # Normalize
    total = sum(importance.values()) + 1e-10
    importance = {k: round(v / total, 4) for k, v in importance.items()}

    # Sort by importance
    return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15])