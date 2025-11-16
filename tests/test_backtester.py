# tests/test_backtester.py
import pandas as pd
from bot_analisa.backtest.backtester import Backtester

def test_basic_backtest():
    # synthetic data: gently rising
    idx = pd.date_range("2025-01-01", periods=50, freq="D")
    # build numeric sequences as lists (not range object used in arithmetic)
    seq = list(range(50))
    df = pd.DataFrame({
        "Open": 100 + pd.Series(seq),
        "High": 100 + pd.Series(seq),
        "Low":  100 + pd.Series(seq),
        "Close": 100 + pd.Series(seq),
        "Volume": [1000]*50,
    }, index=idx)
    df.index.name = "Datetime"

    bt = Backtester()
    result = bt.run_backtest("TEST", df)

    assert "total_trades" in result
    assert "winrate" in result
    assert "equity_curve" in result
