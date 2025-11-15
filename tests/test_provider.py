import pytest
from bot_analisa.data.provider import DataProvider

def test_get_historical_daily_recent():
    dp = DataProvider(data_folder="data_test")
    df = dp.get_historical("BBCA.JK", period="1mo", interval="1d")
    assert df is not None
    assert not df.empty
    # columns
    for c in ["Datetime", "Open", "High", "Low", "Close", "Volume"]:
        assert c in df.columns, f"Missing {c}"
