# src/bot_analisa/backtest/backtester.py
"""
Simple Backtesting Framework (CSV per ticker)

Workflow:
1) Load price history (CSV) — expects Datetime, Open, High, Low, Close, Volume
2) Apply strategy to generate BUY signals
3) For each signal, simulate TP/SL hit using historical bars
4) Track equity curve, metrics, trade list
"""

import pandas as pd
from dataclasses import dataclass, asdict
from typing import List, Dict, Callable
from bot_analisa.strategy.strategy import generate_signals
from bot_analisa.risk import compute_tp_sl

@dataclass
class TradeResult:
    ticker: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    result: float  # profit/loss
    status: str    # TP / SL
    tp: float
    sl: float

class Backtester:
    def __init__(self, strategy_version="v1"):
        self.strategy_version = strategy_version

    def load_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path, parse_dates=["Datetime"])
        df = df.sort_values("Datetime").set_index("Datetime")
        return df

    def run_backtest(self, ticker: str, df: pd.DataFrame) -> Dict:
        ###
        # 1) Generate signals on full dataframe
        ###
        signals = generate_signals(df)
        if not signals:
            return {"ticker": ticker, "total_trades": 0, "winrate": 0, "pf": 0,
                    "max_dd": 0, "equity_curve": [], "trades": []}

        trades: List[TradeResult] = []
        equity = 0.0
        peak_equity = 0.0
        equity_curve = []

        ###
        # 2) Simulate each signal
        ###
        for s in signals:
            entry_idx = pd.to_datetime(s["timestamp"])
            if entry_idx not in df.index:
                continue

            entry_price = s["entry"]
            # calculate tp/sl using risk engine
            tp, sl = compute_tp_sl(entry_price, atr=s.get("ATR_14"), params={"mode": "atr"})

            # walk forward until TP/SL hit
            df_future = df[df.index >= entry_idx]

            exit_price = None
            exit_time = None
            status = None

            for ts, row in df_future.iterrows():
                high = row["High"]
                low = row["Low"]

                # TP first
                if high >= tp:
                    exit_price = tp
                    exit_time = ts
                    status = "TP"
                    break
                # SL next
                if low <= sl:
                    exit_price = sl
                    exit_time = ts
                    status = "SL"
                    break

            if exit_price is None:
                # no hit until end of data → close at last close price
                last_ts = df.index[-1]
                last_close = df.iloc[-1]["Close"]
                exit_price = last_close
                exit_time = last_ts
                status = "END"

            pnl = exit_price - entry_price
            equity += pnl
            peak_equity = max(peak_equity, equity)
            dd = peak_equity - equity
            equity_curve.append(equity)

            trades.append(
                TradeResult(ticker=ticker,
                            entry_time=str(entry_idx),
                            exit_time=str(exit_time),
                            entry=entry_price,
                            exit=exit_price,
                            result=pnl,
                            status=status,
                            tp=tp, sl=sl)
            )

        ###
        # 3) Compute metrics
        ###
        total = len(trades)
        wins = len([t for t in trades if t.result > 0])
        losses = len([t for t in trades if t.result < 0])
        winrate = wins / total if total > 0 else 0
        pf = (sum([t.result for t in trades if t.result > 0]) /
              abs(sum([t.result for t in trades if t.result < 0])) 
              if losses > 0 else float("inf"))
        max_dd = max([0] + [peak_equity - eq for eq in equity_curve])

        return {
            "ticker": ticker,
            "total_trades": total,
            "winrate": winrate,
            "pf": pf,
            "max_dd": max_dd,
            "equity_curve": equity_curve,
            "trades": [asdict(t) for t in trades]
        }

    def save_report(self, result: Dict, path: str):
        import json
        with open(path, "w") as f:
            json.dump(result, f, indent=2)
