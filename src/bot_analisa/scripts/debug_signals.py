#!/usr/bin/env python3
"""
Universal Debug Signal Checker

Usage:
    python scripts/debug_signals.py --csv data/GOTO.JK.csv
"""

import argparse
import pandas as pd

from bot_analisa.indicators.indicators import compute_indicators
from bot_analisa.strategy.strategy import generate_signals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="CSV file of OHLCV data")
    args = parser.parse_args()

    print(f"[DEBUG] Loading CSV: {args.csv}")
    df = pd.read_csv(args.csv, parse_dates=["Datetime"], index_col="Datetime")

    print(f"[DEBUG] Rows loaded: {len(df)}")
    print(df.head())

    print("\n[DEBUG] Computing indicators...")
    ind = compute_indicators(
        df,
        sma_periods=[20, 50],
        ema_periods=[9, 21],
        atr_period=14
    )

    print("\n=== Last 20 indicator rows ===")
    print(ind.tail(20))

    print("\n[DEBUG] Running strategy...")
    signals = generate_signals(ind)

    print(f"\nPermissive count: {signals.permissive_count if hasattr(signals, 'permissive_count') else 'n/a'}")
    print(f"Strict cross count: {signals.strict_cross_count if hasattr(signals, 'strict_cross_count') else 'n/a'}")
    print(f"Signals generated: {len(signals)}")

    print("\n=== Sample signals (last 10) ===")
    if len(signals) > 0:
        for s in signals[-10:]:
            print(s)
    else:
        print("No signals found.")


if __name__ == "__main__":
    main()
