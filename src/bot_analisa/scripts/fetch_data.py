#!/usr/bin/env python3
"""
scripts/fetch_data.py
Usage:
  # fetch a few tickers daily data for 1y
  python scripts/fetch_data.py BBCA.JK BBRI.JK -p 1y -i 1d

  # fetch intraday 15m
  python scripts/fetch_data.py BBCA.JK -p 7d -i 15m
"""

import argparse
from bot_analisa.data.provider import DataProvider

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("tickers", nargs="+", help="Ticker(s), e.g. BBCA.JK")
    p.add_argument("-p", "--period", default="1y", help="Period for yfinance (1d, 1mo, 1y, etc) or use start/end")
    p.add_argument("-i", "--interval", default="1d", help="Interval (1d, 1h, 15m)")
    p.add_argument("--force", action="store_true", help="Overwrite CSV instead of merge")
    return p.parse_args()

def main():
    args = parse_args()
    dp = DataProvider(data_folder="data")
    for t in args.tickers:
        print(f"Fetching {t} period={args.period} interval={args.interval}")
        out = dp.fetch_and_save(t, period=args.period, interval=args.interval, force=args.force)
        if out:
            print("Saved:", out)
        else:
            print("No data for", t)

if __name__ == "__main__":
    main()
