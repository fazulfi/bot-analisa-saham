#!/usr/bin/env python3
"""
watch_signals.py (enhanced)
Backward-compatible upgrade dari watcher batch kamu:
- opsi CLI: --data-folder, --signals-folder, --tickers, --loop, --interval
- loop mode untuk run terus-menerus (cron alternative)
- tetap pakai logic: High -> TP, Low -> SL, prioritas TP
- tidak mengubah call ke storage.update_signal_status (keamanan kompatibilitas)
"""
import argparse
import time
from bot_analisa.signals.storage import SignalStorage
import pandas as pd
from pathlib import Path
from typing import List

def check_signals(data_folder="data", signals_folder="signals", tickers: List[str]|None=None):
    storage = SignalStorage(folder=signals_folder)
    # list open signals
    df_all = storage.list_signals(status="OPEN")
    if df_all is None or df_all.empty:
        print("No OPEN signals.")
        return {}

    # optionally filter by tickers
    if tickers:
        df_all = df_all[df_all["ticker"].isin(tickers)]

    summary = {"updated": []}
    for _, row in df_all.iterrows():
        ticker = row["ticker"]
        sid = row["id"]
        try:
            tp = float(row["tp"])
            sl = float(row["sl"])
        except Exception:
            print(f"Malformed TP/SL for {sid}, skipping")
            continue

        # load latest data
        data_file = Path(data_folder) / f"{ticker}.csv"
        if not data_file.exists():
            print("No price data for", ticker)
            continue
        df = pd.read_csv(data_file, parse_dates=["Datetime"])
        if df.empty:
            continue
        # get last high and low (fallback to Close)
        last_row = df.iloc[-1]
        last_high = float(last_row.get("High", last_row.get("Close")))
        last_low = float(last_row.get("Low", last_row.get("Close")))

        # check TP first (if both hit in same bar prioritise TP)
        if last_high >= tp:
            # preserve existing signature calling style (your storage expects this)
            ok = storage.update_signal_status(ticker=ticker, signal_id=sid,
                                             new_status="TP",
                                             status_info=f"hit_tp_at_high={last_high}")
            if ok:
                print(f"{sid} -> TP (high {last_high} >= tp {tp})")
                summary["updated"].append({"id": sid, "ticker": ticker, "status": "TP", "price": last_high})
            continue
        if last_low <= sl:
            ok = storage.update_signal_status(ticker=ticker, signal_id=sid,
                                             new_status="SL",
                                             status_info=f"hit_sl_at_low={last_low}")
            if ok:
                print(f"{sid} -> SL (low {last_low} <= sl {sl})")
                summary["updated"].append({"id": sid, "ticker": ticker, "status": "SL", "price": last_low})
            continue
        print(f"{sid} remains OPEN")
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", help="Optionally specify tickers to check")
    parser.add_argument("--data-folder", default="data", help="Folder with price CSVs (default ./data)")
    parser.add_argument("--signals-folder", default="signals", help="Folder with signals (default ./signals)")
    parser.add_argument("--loop", action="store_true", help="Run in loop")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval seconds (default 60s)")
    args = parser.parse_args()

    tickers = args.tickers

    if not args.loop:
        summary = check_signals(data_folder=args.data_folder, signals_folder=args.signals_folder, tickers=tickers)
        print("Summary:", summary)
        return

    # loop mode
    print("Starting watcher loop. Data folder:", args.data_folder, "Signals:", args.signals_folder)
    while True:
        try:
            summary = check_signals(data_folder=args.data_folder, signals_folder=args.signals_folder, tickers=tickers)
            if summary.get("updated"):
                print("Updates this run:", summary["updated"])
        except Exception as e:
            print("Error during watcher loop:", e)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
