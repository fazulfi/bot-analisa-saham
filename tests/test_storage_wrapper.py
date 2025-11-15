import shutil, os
from bot_analisa.signals.storage import SignalStorage

def test_save_signal_dict_wrapper(tmp_path):
    folder = tmp_path / "signals"
    storage = SignalStorage(folder=str(folder))

    signal = {
        "ticker": "BBCA",
        "entry": 100.5,
        "tp": 105.0,
        "sl": 98.0,
        "reason": "ema_cross",
        "strategy_version": "v1"
    }

    row = storage.save_signal_dict(signal)

    # row harus punya id
    assert "id" in row
    assert row["ticker"] == "BBCA"

    df = storage.list_signals("BBCA")
    assert len(df) == 1
