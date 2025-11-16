#!/usr/bin/env python3
import argparse
import os
from bot_analisa.backtest.backtester import Backtester

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", default="backtests")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    bt = Backtester()
    df = bt.load_csv(args.csv)
    result = bt.run_backtest(args.ticker, df)

    outfile = os.path.join(args.out, f"report_{args.ticker}.json")
    bt.save_report(result, outfile)

    print("Backtest saved to:", outfile)
    print("Trades:", result["total_trades"], 
          "Winrate:", round(result["winrate"]*100, 2),
          "PF:", result["pf"],
          "MaxDD:", result["max_dd"])

if __name__ == "__main__":
    main()
