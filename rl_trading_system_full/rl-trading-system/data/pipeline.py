"""
Data Pipeline Module
====================
Fetches historical price data, computes technical indicators,
and prepares feature matrices for the RL environment.
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────
# Technical Indicator Computations
# ──────────────────────────────────────────────

def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def compute_macd(prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """MACD and Signal line."""
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def compute_bollinger_bands(prices: pd.Series, period: int = 20, k: float = 2.0) -> Tuple[pd.Series, pd.Series]:
    """Bollinger Bands (upper, lower)."""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    return sma + k * std, sma - k * std


def compute_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    if isinstance(high, pd.DataFrame):
        high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame):
        low = low.iloc[:, 0]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad + 1e-10)


def compute_dmi(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Directional Movement Index (ADX)."""
    # Ensure inputs are Series, not DataFrames
    if isinstance(high, pd.DataFrame):
        high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame):
        low = low.iloc[:, 0]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / (atr + 1e-10))
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / (atr + 1e-10))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    adx = dx.rolling(window=period).mean()
    return adx


def compute_turbulence(returns: pd.DataFrame, window: int = 60) -> pd.Series:
    """
    Turbulence index: Mahalanobis distance of returns from historical mean.
    Detects abnormal market movements.
    """
    turb = pd.Series(index=returns.index, dtype=float)
    for i in range(window, len(returns)):
        hist = returns.iloc[i - window:i]
        mu = hist.mean().values
        cov = hist.cov().values
        curr = returns.iloc[i].values
        diff = curr - mu
        try:
            cov_inv = np.linalg.pinv(cov)
            t = diff @ cov_inv @ diff
            turb.iloc[i] = t
        except Exception:
            turb.iloc[i] = 0.0
    return turb.fillna(0)


# ──────────────────────────────────────────────
# Data Fetcher (offline-capable with sample data)
# ──────────────────────────────────────────────

def generate_synthetic_data(
    tickers: List[str],
    start_date: str = "2018-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42
) -> Dict[str, pd.DataFrame]:
    """
    Generate realistic synthetic stock data for development/testing.
    In production, replace with yfinance / Polygon / Alpha Vantage calls.
    """
    np.random.seed(seed)
    dates = pd.bdate_range(start=start_date, end=end_date)
    data = {}

    base_prices = {"AAPL": 170, "GOOGL": 140, "MSFT": 330, "NFLX": 450, "TSLA": 250}
    base_vols = {"AAPL": 0.015, "GOOGL": 0.016, "MSFT": 0.014, "NFLX": 0.022, "TSLA": 0.028}

    for ticker in tickers:
        n = len(dates)
        base = base_prices.get(ticker, 100)
        vol = base_vols.get(ticker, 0.018)

        # GBM with mean-reverting component and regime shifts
        returns = np.random.normal(0.0003, vol, n)
        # Add occasional jumps
        jumps = np.random.binomial(1, 0.02, n) * np.random.normal(0, vol * 3, n)
        returns += jumps
        # Add momentum
        for i in range(1, n):
            returns[i] += 0.05 * returns[i - 1]

        prices = base * np.cumprod(1 + returns)
        high = prices * (1 + np.abs(np.random.normal(0, 0.005, n)))
        low = prices * (1 - np.abs(np.random.normal(0, 0.005, n)))
        volume = np.random.lognormal(17, 0.5, n).astype(int)

        df = pd.DataFrame({
            "Date": dates, "Open": prices * (1 + np.random.normal(0, 0.002, n)),
            "High": high, "Low": low, "Close": prices,
            "Adj Close": prices, "Volume": volume
        })
        df.set_index("Date", inplace=True)
        data[ticker] = df

    return data


def fetch_data(tickers: List[str], start: str, end: str, benchmark: str = "^GSPC") -> Dict[str, pd.DataFrame]:
    """
    Fetch historical data. Tries yfinance first, falls back to synthetic.
    """
    try:
        import yfinance as yf
        data = {}
        all_tickers = tickers + [benchmark]
        for t in all_tickers:
            df = yf.download(t, start=start, end=end, progress=False)
            # Flatten multi-level columns from newer yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Remove duplicate column names if any
            df = df.loc[:, ~df.columns.duplicated()]
            if len(df) > 100:
                data[t] = df
        if len(data) == len(all_tickers):
            return data
    except Exception:
        pass

    # Fallback to synthetic
    print("[DataPipeline] Using synthetic data (yfinance unavailable)")
    data = generate_synthetic_data(tickers, start, end)
    # Generate benchmark
    bench_data = generate_synthetic_data([benchmark.replace("^", "BENCH")], start, end, seed=99)
    data[benchmark] = list(bench_data.values())[0]
    return data


# ──────────────────────────────────────────────
# Feature Engineering
# ──────────────────────────────────────────────

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to a price DataFrame."""
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]

    # Extract as Series (handle both Series and single-col DataFrame)
    def to_series(col):
        s = df[col]
        return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s

    close = to_series("Close") if "Close" in df.columns else to_series("Adj Close")
    high = to_series("High")
    low = to_series("Low")
    volume = to_series("Volume")

    df = df.copy()
    df["rsi"] = compute_rsi(close)
    df["macd"], df["macd_signal"] = compute_macd(close)
    df["bb_upper"], df["bb_lower"] = compute_bollinger_bands(close)
    df["sma_30"] = close.rolling(30).mean()
    df["sma_60"] = close.rolling(60).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["volume_norm"] = volume / volume.rolling(20).mean()
    df["volatility"] = close.pct_change().rolling(20).std() * np.sqrt(252)
    df["cci"] = compute_cci(high, low, close)
    df["dmi"] = compute_dmi(high, low, close)
    df["returns"] = close.pct_change()

    return df


def prepare_multi_stock_data(
    raw_data: Dict[str, pd.DataFrame],
    tickers: List[str],
    benchmark: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process raw data into a unified multi-stock feature DataFrame.
    Returns (stock_features, benchmark_data).
    """
    processed = {}
    for ticker in tickers:
        df = raw_data[ticker].copy()
        df = add_technical_indicators(df)
        df = df.dropna()
        # Prefix columns with ticker
        rename_cols = {}
        for col in df.columns:
            if col not in ["Date"]:
                rename_cols[col] = f"{ticker}_{col}"
        df = df.rename(columns=rename_cols)
        processed[ticker] = df

    # Align dates
    common_idx = processed[tickers[0]].index
    for t in tickers[1:]:
        common_idx = common_idx.intersection(processed[t].index)

    aligned = pd.concat([processed[t].loc[common_idx] for t in tickers], axis=1)

    # Benchmark
    bench = raw_data[benchmark].copy()
    bench = add_technical_indicators(bench)
    bench = bench.loc[bench.index.intersection(common_idx)]

    # Compute turbulence across all stocks
    returns_df = pd.DataFrame({
        t: raw_data[t]["Close"].pct_change() for t in tickers
    }).dropna()
    returns_df = returns_df.loc[returns_df.index.intersection(common_idx)]
    turb = compute_turbulence(returns_df)
    aligned["turbulence"] = turb.loc[common_idx].values[:len(aligned)]

    return aligned.dropna(), bench.dropna()


def create_sliding_windows(
    features: np.ndarray,
    window_size: int
) -> np.ndarray:
    """Create sliding window sequences for LSTM input."""
    n = len(features)
    if n <= window_size:
        # Pad with zeros
        padded = np.zeros((window_size, features.shape[1]))
        padded[-n:] = features
        return padded[np.newaxis, ...]

    windows = []
    for i in range(window_size, n + 1):
        windows.append(features[i - window_size:i])
    return np.array(windows)


def normalize_features(df: pd.DataFrame, method: str = "zscore") -> Tuple[pd.DataFrame, Dict]:
    """Normalize features with stored statistics for inference."""
    stats = {}
    normalized = df.copy()
    for col in df.columns:
        if method == "zscore":
            mu, sigma = df[col].mean(), df[col].std() + 1e-10
            normalized[col] = (df[col] - mu) / sigma
            stats[col] = {"mean": mu, "std": sigma}
        elif method == "minmax":
            mn, mx = df[col].min(), df[col].max() + 1e-10
            normalized[col] = (df[col] - mn) / (mx - mn)
            stats[col] = {"min": mn, "max": mx}
    return normalized, stats
