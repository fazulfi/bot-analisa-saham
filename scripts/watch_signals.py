#!/usr/bin/env python3
"""
Simple watcher: reads signals/*.csv, for each OPEN signal checks latest price (from data/<TICKER>.csv)
and updates status if TP/SL hit.

This is a simple batch checker (not real-time). For live, integrate with websocket/stream price feed.
"""
import argparse
from bot_analisa.signals.storage import SignalStorage
import pandas as pd
from pathlib import Path

def check_signals(data_folder="data", signals_folder="signals", tickers=None):
    storage = SignalStorage(folder=signals_folder)
    # list open signals
    df_all = storage.list_signals(status="OPEN")
    if df_all.empty:
        print("No OPEN signals.")
        return

    # optionally filter by tickers
    if tickers:
        df_all = df_all[df_all["ticker"].isin(tickers)]

    for _, row in df_all.iterrows():
        ticker = row["ticker"]
        sid = row["id"]
        tp = float(row["tp"])
        sl = float(row["sl"])
        # load latest data
        data_file = Path(data_folder) / f"{ticker}.csv"
        if not data_file.exists():
            print("No price data for", ticker)
            continue
        df = pd.read_csv(data_file, parse_dates=["Datetime"])
        if df.empty:
            continue
        # get last high and low
        last_row = df.iloc[-1]
        last_high = float(last_row.get("High", last_row.get("Close")))
        last_low = float(last_row.get("Low", last_row.get("Close")))

        # check TP first (if both hit in same bar prioritise TP)
        if last_high >= tp:
            ok = storage.update_signal_status(ticker=ticker, signal_id=sid, new_status="TP", status_info=f"hit_tp_at_high={last_high}")
            if ok:
                print(f"{sid} -> TP (high {last_high} >= tp {tp})")
            continue
        if last_low <= sl:
            ok = storage.update_signal_status(ticker=ticker, signal_id=sid, new_status="SL", status_info=f"hit_sl_at_low={last_low}")
            if ok:
                print(f"{sid} -> SL (low {last_low} <= sl {sl})")
            continue
        print(f"{sid} remains OPEN")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", help="Optionally specify tickers to check")
    args = parser.parse_args()
    check_signals(tickers=args.tickers)
