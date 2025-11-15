# tests/test_indicators.py
import pandas as pd
import numpy as np
from bot_analisa.indicators.indicators import compute_indicators

def make_sample_ohlcv(n=100):
    # create a gentle uptrend sample for testing
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    price = np.linspace(100, 150, n) + np.random.normal(0, 0.5, size=n)
    high = price + np.random.uniform(0.1, 0.5, size=n)
    low = price - np.random.uniform(0.1, 0.5, size=n)
    open_ = price + np.random.uniform(-0.3, 0.3, size=n)
    close = price
    volume = np.random.randint(1000, 10000, size=n)
    df = pd.DataFrame({
        "Datetime": dates,
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume
    })
    return df

def test_compute_indicators_basic():
    df = make_sample_ohlcv(60)
    out = compute_indicators(df)
    # basic checks
    assert "SMA_20" in out.columns
    assert "EMA_9" in out.columns
    assert "ATR_14" in out.columns
    assert "RSI_14" in out.columns
    assert "MACD" in out.columns
    # after warmup, SMA_20 should not be all na
    assert out["SMA_20"].iloc[19:].notna().any()
    assert out["ATR_14"].iloc[13:].notna().any()
    assert out["RSI_14"].iloc[13:].notna().any()
