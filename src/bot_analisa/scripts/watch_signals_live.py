#!/usr/bin/env python3
"""
scripts/watch_signals.py

CLI to run the watcher.

Modes:
- simulate: --simulate PATH/TO/<TICKER>.csv  (CSV with Datetime,Close)
- once (live): uses DataProvider if available to fetch last price
- loop: run continuously (sleep interval)

Examples:
  # simulate backfill for BBCA.csv
  python scripts/watch_signals.py --simulate data/BBCA.csv --ticker BBCA

  # live once using DataProvider (if implemented)
  python scripts/watch_signals.py --once --ticker BBCA

  # loop every 30s
  python scripts/watch_signals.py --loop --interval 30 --tickers BBCA,TLKM
"""
import argparse
import time
import os
import pandas as pd
from bot_analisa.signals.watcher import watch_once, simulate_backfill, process_price_tick
from bot_analisa.signals.storage import SignalStorage

# try import a DataProvider from project (optional)
DataProvider = None
try:
    from bot_analisa.data.provider import DataProvider as _DP
    DataProvider = _DP
except Exception:
    DataProvider = None

def load_csv_price_series(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Datetime"], index_col="Datetime")
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", "--tickers", dest="tickers", help="Comma separated tickers", default=None)
    parser.add_argument("--simulate", dest="simulate", help="CSV path to simulate (one ticker)", default=None)
    parser.add_argument("--once", action="store_true", help="Do one pass (live)")
    parser.add_argument("--loop", action="store_true", help="Run loop")
    parser.add_argument("--interval", type=int, default=30, help="Loop interval seconds")
    parser.add_argument("--storage", default="signals", help="Signals folder (default ./signals)")
    args = parser.parse_args()

    tickers = None
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]

    storage = SignalStorage(folder=args.storage)

    # simulate mode (single ticker)
    if args.simulate:
        df = load_csv_price_series(args.simulate)
        # if no ticker provided, infer from filename
        t = tickers[0] if tickers else os.path.splitext(os.path.basename(args.simulate))[0]
        print(f"Simulating backfill for {t}, {len(df)} rows")
        res = simulate_backfill(storage, t, df)
        print("Simulation result:", res)
        return

    # live provider mode
    provider = None
    if DataProvider is not None:
        provider = DataProvider()
    else:
        print("Warning: DataProvider not available in project. Provide provider or use --simulate.")
        if not (args.once or args.loop):
            parser.print_help()
            return

    if args.once:
        res = watch_once(provider, storage, tickers)
        print("Watch once result:", res)
        return

    if args.loop:
        print("Starting watch loop. tickers:", tickers or "auto")
        while True:
            try:
                res = watch_once(provider, storage, tickers)
                if res:
                    print("Updates:", res)
            except Exception as e:
                print("Error in loop:", e)
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
