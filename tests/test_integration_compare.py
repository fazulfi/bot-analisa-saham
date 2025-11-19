import os
import csv
from scripts.compare_engine_vs_backtest import read_trades_from_csv, compare_for_ticker

TEST_DIR = "tests/tmp_compare"
os.makedirs(TEST_DIR, exist_ok=True)

def write_csv(path, rows, headers):
    with open(path, "w", newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def test_compare_basic_match(tmp_path):
    eng = tmp_path / "PGAS_engine.csv"
    bt = tmp_path / "PGAS_backtest.csv"
    headers = ["ticker","entry_time","entry_price","exit_time","exit_price","status"]
    rows_eng = [
        {"ticker":"PGAS","entry_time":"2025-01-01 09:30:00","entry_price":"100","exit_time":"2025-01-02 10:00:00","exit_price":"110","status":"TP"}
    ]
    rows_bt = [
        {"ticker":"PGAS","entry_time":"2025-01-01 09:30:00","entry_price":"100","exit_time":"2025-01-02 10:00:00","exit_price":"110","status":"TP"}
    ]
    write_csv(str(eng), rows_eng, headers)
    write_csv(str(bt), rows_bt, headers)

    eng_trades = read_trades_from_csv(str(eng))
    bt_trades = read_trades_from_csv(str(bt))
    summary, mismatches = compare_for_ticker(eng_trades, bt_trades, "PGAS")
    assert summary["mismatches"] == 0
    assert len(mismatches) == 0
