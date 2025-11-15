# tests/test_signals.py
import tempfile
import shutil
from bot_analisa.signals.storage import SignalStorage
import pandas as pd
import os

def make_price_csv(folder, ticker):
    # create simple OHLC for 5 bars
    df = pd.DataFrame({
        "Datetime": pd.date_range("2025-01-01", periods=5, freq="D"),
        "Open": [10,11,12,13,14],
        "High": [11,12,13,14,50],  # last high hits TP=... (simulate)
        "Low": [9,10,11,12,13],
        "Close": [10.5,11.5,12.5,13.5,14.5],
        "Volume": [100,100,100,100,100]
    })
    path = os.path.join(folder, f"{ticker}.csv")
    df.to_csv(path, index=False)
    return path

def test_add_and_update_signal(tmp_path):
    sig_folder = tmp_path / "signals"
    data_folder = tmp_path / "data"
    sig_folder.mkdir()
    data_folder.mkdir()
    storage = SignalStorage(folder=str(sig_folder))

    # add a signal
    sig = storage.add_signal("TEST.JK", entry_price=14.5, tp=40.0, sl=12.0, strategy_version="test")
    assert sig["status"] == "OPEN"

    # check file exists and contains the row
    df = storage.list_signals("TEST.JK")
    assert not df.empty
    assert df.iloc[-1]["id"] == sig["id"]

    # create price file that hits TP (last high=50)
    make_price_csv(str(data_folder), "TEST.JK")

    # run watcher logic inline (simplified)
    df_all = storage.list_signals(status="OPEN")
    assert not df_all.empty

    # simulate watcher: read last high
    import pandas as pd
    dff = pd.read_csv(str(data_folder / "TEST.JK.csv"), parse_dates=["Datetime"])
    last_high = dff.iloc[-1]["High"]
    assert last_high >= sig["tp"]

    ok = storage.update_signal_status("TEST.JK", sig["id"], "TP", "unit test hit")
    assert ok
    df2 = storage.list_signals("TEST.JK")
    assert df2.iloc[-1]["status"] == "TP"
