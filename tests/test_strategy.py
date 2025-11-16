# tests/test_strategy.py

import pandas as pd
import numpy as np
from bot_analisa.strategy import generate_signals

def make_synthetic():
    # Generate synthetic OHLCV that forces EMA cross
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    price = np.linspace(100, 120, 50)
    df = pd.DataFrame({
        "Datetime": dates,
        "Open": price - 0.3,
        "High": price + 0.5,
        "Low": price - 0.6,
        "Close": price,
        "Volume": np.random.randint(100, 1000, 50)
    })

    df = df.set_index("Datetime")
    return df

def test_strategy_buy_signal():
    df = make_synthetic()
    signals = generate_signals(df)

    # At least 1 signal
    assert len(signals) >= 1

    s = signals[0]
    assert s["signal"] == "BUY"
    assert "tp" in s and "sl" in s
    assert s["entry"] > 0
