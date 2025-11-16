#!/usr/bin/env python3
"""
CLI for parameter sweep + walk-forward tuning.

Usage:
  python scripts/tune_params.py --ticker BBCA --csv data/BBCA.csv --out tuning --preset simple
  python scripts/tune_params.py --ticker BBCA --csv data/BBCA.csv --out tuning --grid '{"atr_period":[10,14],"ema_fast":[5,9],"ema_slow":[21,50]}' --walk 30
"""
import argparse
import json
import os
import pandas as pd
from datetime import datetime
from bot_analisa.backtest.backtester import Backtester
# optional: import strategy generator if you want to pass into backtester
try:
    from bot_analisa.strategy import generate_signals
    strategy_gen = generate_signals
except Exception:
    strategy_gen = None

PRESETS = {
    "simple": {
        "atr_period": [10, 14],
        "ema_fast": [5, 9],
        "ema_slow": [21, 50]
    },
}

def parse_grid(grid_str):
    try:
        return json.loads(grid_str)
    except Exception:
        raise

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="tuning")
    p.add_argument("--preset", default=None, help="use preset grid name")
    p.add_argument("--grid", default=None, help="json string param grid")
    p.add_argument("--walk", type=int, default=None, help="walk-forward window in days")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    bt = Backtester()
    df = bt.load_csv(args.csv)

    if args.preset:
        if args.preset not in PRESETS:
            raise SystemExit("Unknown preset")
        grid = PRESETS[args.preset]
    elif args.grid:
        grid = parse_grid(args.grid)
    else:
        raise SystemExit("Provide --preset or --grid")

    print("Running tuning for", args.ticker, "grid:", grid, "walk:", args.walk)
    res_df = bt.tune_params(args.ticker, df, grid, signal_generator=strategy_gen, walk_forward_days=args.walk)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_csv = os.path.join(args.out, f"tuning_{args.ticker}_{ts}.csv")
    res_df.to_csv(out_csv, index=False)
    print("Tuning results saved to:", out_csv)
    print(res_df.head())

if __name__ == "__main__":
    main()
