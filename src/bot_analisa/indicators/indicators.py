"""
indicators.py
Fungsi-fungsi indikator teknikal:
- SMA, EMA
- True Range (TR), ATR (Welles Wilder smoothing)
- RSI (Wilder)
- MACD (12,26,9)
Semua fungsi menggunakan pandas vectorized operations.
"""

from typing import Optional
import pandas as pd
import numpy as np

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average"""
    return series.rolling(window=period, min_periods=period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average using pandas' ewm (adjust=False to match trading semantics)"""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()

def true_range(df: pd.DataFrame) -> pd.Series:
    """
    True Range:
    TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
    Expects df contains columns: 'High','Low','Close'
    """
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    ATR using Welles Wilder smoothing (exponential-like but with alpha = 1/period).
    Implementation:
      TR = true_range(df)
      ATR[period] = TR[0:period].mean()
      ATR[t] = (ATR[t-1] * (period-1) + TR[t]) / period
    Returns series aligned to df index (float), first valid at index (period).
    """
    tr = true_range(df)
    # first ATR value = simple average of first 'period' TRs
    atr_series = pd.Series(index=tr.index, dtype="float64")
    # compute first value
    first_idx = period - 1
    if len(tr) >= period:
        first_atr = tr.iloc[:period].mean()
        atr_series.iloc[first_idx] = first_atr
        # Wilder smoothing
        for i in range(first_idx + 1, len(tr)):
            prev = atr_series.iloc[i - 1]
            atr_series.iloc[i] = (prev * (period - 1) + tr.iloc[i]) / period
    return atr_series

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI using Welles Wilder (RMA) implemented via EWM with alpha = 1/period.
    This implementation matches common libraries like `ta` (RSIIndicator).
    Steps:
      - compute delta
      - gain = positive deltas, loss = -negative deltas
      - apply RMA = ewm(alpha=1/period, adjust=False).mean() with min_periods=period
      - RSI = 100 - 100 / (1 + RS)
    """
    # ensure float series
    s = series.astype("float64", copy=False)

    delta = s.diff()

    gain = delta.clip(lower=0.0).fillna(0.0)
    loss = -delta.clip(upper=0.0).fillna(0.0)

    # Wilder's smoothing via ewm with alpha = 1/period; min_periods=period to require warmup
    avg_gain = gain.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()

    # RS and RSI
    rs = avg_gain / avg_loss
    # avoid division by zero
    rs_safe = rs.replace([np.inf, -np.inf], np.nan)
    rsi = 100 - (100 / (1 + rs_safe))

    return rsi

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD line = EMA(fast) - EMA(slow)
    Signal line = EMA(MACD line, signal)
    Histogram = MACD - Signal
    Returns (macd_line, signal_line, hist)
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def compute_indicators(df: pd.DataFrame,
                       sma_periods: Optional[list] = None,
                       ema_periods: Optional[list] = None,
                       atr_period: int = 14,
                       rsi_period: int = 14) -> pd.DataFrame:
    """
    Compute several indicators and append columns to a copy of df.
    Default: SMA periods [20,50], EMA [9,21], ATR 14, RSI 14, MACD (12,26,9)
    """
    sma_periods = sma_periods or [20, 50]
    ema_periods = ema_periods or [9, 21]

    out = df.copy().reset_index(drop=True)
    # assume columns: Datetime, Open, High, Low, Close, Volume
    if "Close" not in out.columns:
        raise ValueError("DataFrame must contain 'Close' column")
    # SMA
    for p in sma_periods:
        out[f"SMA_{p}"] = sma(out["Close"], p)
    # EMA
    for p in ema_periods:
        out[f"EMA_{p}"] = ema(out["Close"], p)
    # ATR
    out[f"ATR_{atr_period}"] = atr(out, period=atr_period)
    # RSI
    out[f"RSI_{rsi_period}"] = rsi(out["Close"], period=rsi_period)
    # MACD
    macd_line, signal_line, hist = macd(out["Close"])
    out["MACD"] = macd_line
    out["MACD_signal"] = signal_line
    out["MACD_hist"] = hist
    return out
