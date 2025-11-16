# tests/test_tune_params.py
import pandas as pd
import os
from bot_analisa.backtest.backtester import Backtester

def make_synthetic_df():
    idx = pd.date_range("2024-01-01", periods=120, freq="D")
    seq = list(range(120))
    df = pd.DataFrame({
        "Open": 100 + pd.Series(seq),
        "High": 100 + pd.Series(seq) + 0.5,
        "Low":  100 + pd.Series(seq) - 0.5,
        "Close": 100 + pd.Series(seq),
        "Volume": [1000]*120,
    }, index=idx)
    df.index.name = "Datetime"
    return df

def test_tune_params_basic(tmp_path):
    df = make_synthetic_df()
    bt = Backtester()
    grid = {"atr_period": [10], "ema_fast": [5], "ema_slow": [21]}
    res = bt.tune_params("SYN", df, grid, signal_generator=None, walk_forward_days=None)
    # res should be dataframe with same number of rows as product of grid sizes
    assert len(res) == 1
    # has pf/winrate or total_trades columns
    assert any(col in res.columns for col in ["winrate", "total_trades", "avg_winrate"])
