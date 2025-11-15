# tests/test_watcher.py
import pandas as pd
from bot_analisa.signals.watcher import simulate_backfill, process_price_tick
from bot_analisa.signals.storage import SignalStorage
import tempfile
import os

class FakeProvider:
    def __init__(self, price_map):
        self.price_map = price_map
    def get_last_price(self, ticker):
        return float(self.price_map[ticker])

def test_process_price_tick_tp_and_sl(tmp_path):
    folder = str(tmp_path / "signals")
    storage = SignalStorage(folder=folder)

    # add two signals for same ticker: one with tp low (to be hit), one with sl high (not hit)
    s1 = {"ticker":"TST", "entry":100.0, "tp":102.0, "sl":95.0, "reason":"r1"}
    s2 = {"ticker":"TST", "entry":110.0, "tp":120.0, "sl":105.0, "reason":"r2"}
    r1 = storage.save_signal_dict(s1)
    r2 = storage.save_signal_dict(s2)

    # price moves to 103 -> should hit s1 TP
    updates = process_price_tick(storage, "TST", 103.0)
    assert r1["id"] in updates

    # price moves down to 104 -> second signal still open
    updates2 = process_price_tick(storage, "TST", 104.0)
    assert r2["id"] not in updates2

def test_simulate_backfill_hits(tmp_path):
    folder = str(tmp_path / "signals")
    storage = SignalStorage(folder=folder)
    s = {"ticker":"ABC", "entry":50.0, "tp":55.0, "sl":45.0, "reason":"t"}
    storage.save_signal_dict(s)

    # create a price series that will hit TP at step 3
    idx = pd.date_range("2025-01-01", periods=5, freq="D")
    prices = pd.Series([51.0, 52.0, 56.0, 54.0, 53.0], index=idx)
    res = simulate_backfill(storage, "ABC", prices)
    assert "ABC" in res
    # ensure the storage shows the updated status
    df = storage.list_signals("ABC")
    assert any(df["status"] == "TP")
