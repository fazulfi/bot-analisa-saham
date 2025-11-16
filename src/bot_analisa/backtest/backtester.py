# src/bot_analisa/backtest/backtester.py
# (pastikan file sudah ada; berikut tambah/replace bagian class Backtester)

from typing import Callable, Optional, Tuple
import itertools
import json
import os
import pandas as pd
from dataclasses import dataclass, asdict

# import existing generate_signals default
try:
    from bot_analisa.strategy import generate_signals as default_generate_signals
except Exception:
    # fallback: define a dummy generator that returns []
    def default_generate_signals(df, params=None):
        return []

@dataclass
class TradeResult:
    ticker: str
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    result: float
    status: str
    tp: float
    sl: float

class Backtester:
    def __init__(self, strategy_version="v1"):
        self.strategy_version = strategy_version

    def load_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path, parse_dates=["Datetime"])
        df = df.sort_values("Datetime").set_index("Datetime")
        return df

    def run_backtest(self, ticker: str, df: pd.DataFrame,
                     signal_generator: Callable = None,
                     signal_params: Optional[dict] = None) -> dict:
        """Run backtest with optionally custom signal_generator(df, params) -> signals list."""
        if signal_generator is None:
            signal_generator = default_generate_signals

        if signal_params is None:
            signal_params = {}

        # generate signals
        try:
            signals = signal_generator(df, signal_params) if signal_params else signal_generator(df)
        except TypeError:
            # generator might expect (df) only
            signals = signal_generator(df)

        trades = []
        equity = 0.0
        peak_equity = 0.0
        equity_curve = []

        if not signals:
            return {"ticker": ticker, "total_trades": 0, "winrate": 0, "pf": 0,
                    "max_dd": 0, "equity_curve": [], "trades": []}

        # For each signal simulate TP/SL hit with naive approach
        for s in signals:
            entry_idx = pd.to_datetime(s.get("timestamp", s.get("datetime", s.get("entry_time"))))
            if entry_idx not in df.index:
                # try nearest index (forward fill)
                try:
                    entry_idx = df.index[df.index.get_indexer([entry_idx], method="pad")[0]]
                except Exception:
                    continue

            entry_price = float(s["entry"])
            # compute TP/SL - try using risk module if available
            try:
                from bot_analisa.risk import compute_tp_sl
                tp, sl = compute_tp_sl(entry_price, atr=s.get("ATR_14", None), params=s.get("risk_params", {}))
            except Exception:
                # fallback simple fixed percent (5% TP / 2% SL)
                tp = entry_price * 1.05
                sl = entry_price * 0.98

            df_future = df[df.index >= entry_idx]

            exit_price = None
            exit_time = None
            status = None

            for ts, row in df_future.iterrows():
                high = row["High"]
                low = row["Low"]
                if high >= tp:
                    exit_price = tp
                    exit_time = ts
                    status = "TP"
                    break
                if low <= sl:
                    exit_price = sl
                    exit_time = ts
                    status = "SL"
                    break

            if exit_price is None:
                last_ts = df.index[-1]
                exit_price = float(df.iloc[-1]["Close"])
                exit_time = last_ts
                status = "END"

            pnl = exit_price - entry_price
            equity += pnl
            peak_equity = max(peak_equity, equity)
            equity_curve.append(equity)

            trades.append(TradeResult(ticker=ticker,
                                      entry_time=str(entry_idx),
                                      exit_time=str(exit_time),
                                      entry=entry_price,
                                      exit=exit_price,
                                      result=pnl,
                                      status=status,
                                      tp=tp, sl=sl))

        # metrics
        total = len(trades)
        wins = len([t for t in trades if t.result > 0])
        losses = len([t for t in trades if t.result < 0])
        winrate = wins / total if total > 0 else 0
        gross_win = sum([t.result for t in trades if t.result > 0])
        gross_loss = abs(sum([t.result for t in trades if t.result < 0]))
        pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
        max_dd = max([0] + [peak_equity - eq for eq in equity_curve]) if equity_curve else 0

        return {
            "ticker": ticker,
            "total_trades": total,
            "winrate": winrate,
            "pf": pf,
            "max_dd": max_dd,
            "equity_curve": equity_curve,
            "trades": [asdict(t) for t in trades]
        }

    def tune_params(self, ticker: str, df: pd.DataFrame, param_grid: dict,
                    signal_generator: Callable = None,
                    walk_forward_days: Optional[int] = None) -> pd.DataFrame:
        """
        param_grid: dict of param_name -> list(values)
        walk_forward_days: if provided, perform sliding validation windows of this many days
        returns DataFrame with columns param..., total_trades, winrate, pf, max_dd, avg_winrate(if walk)
        """
        # build grid combos
        keys = list(param_grid.keys())
        combos = list(itertools.product(*[param_grid[k] for k in keys]))

        results = []
        for combo in combos:
            params = dict(zip(keys, combo))

            if walk_forward_days:
                # sliding windows: for each fold do train on beginning up to t, validate next window
                # we'll do expanding window: train_end moves forward by walk_forward_days
                metrics = []
                start = df.index[0]
                end = df.index[-1]
                window_delta = pd.Timedelta(days=walk_forward_days)
                split_point = start + window_delta
                while split_point + window_delta <= end:
                    train_df = df[df.index < split_point]
                    val_df = df[(df.index >= split_point) & (df.index < split_point + window_delta)]
                    if len(train_df) < 10 or len(val_df) < 2:
                        split_point = split_point + window_delta
                        continue

                    # run on validation only, but generator may expect historical to compute indicators.
                    # We'll generate signals on train+val but only evaluate trades that entry in val
                    combined = pd.concat([train_df, val_df])
                    res = self.run_backtest(ticker, combined, signal_generator=signal_generator, signal_params=params)
                    # filter trades to only those with entry_time in val_df
                    trades = res.get("trades", [])
                    val_trade_results = []
                    for t in trades:
                        try:
                            et = pd.to_datetime(t["entry_time"])
                            if (et >= val_df.index[0]) and (et <= val_df.index[-1]):
                                val_trade_results.append(t)
                        except Exception:
                            continue
                    if not val_trade_results:
                        metrics.append({"winrate": 0, "pf": 0, "trades": 0, "max_dd": 0})
                    else:
                        wins = sum(1 for t in val_trade_results if t["result"] > 0)
                        total = len(val_trade_results)
                        winrate = wins / total if total else 0
                        gross_win = sum(t["result"] for t in val_trade_results if t["result"] > 0)
                        gross_loss = abs(sum(t["result"] for t in val_trade_results if t["result"] < 0))
                        pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
                        max_dd = max(0, max([0]))  # placeholder, we didn't compute fold equity curve
                        metrics.append({"winrate": winrate, "pf": pf, "trades": total, "max_dd": max_dd})

                    split_point = split_point + window_delta

                # aggregate metrics
                if metrics:
                    avg_winrate = float(pd.Series([m["winrate"] for m in metrics]).mean())
                    avg_pf = float(pd.Series([m["pf"] if m["pf"] != float("inf") else 0 for m in metrics]).mean())
                    avg_trades = int(pd.Series([m["trades"] for m in metrics]).sum())
                    avg_maxdd = float(pd.Series([m["max_dd"] for m in metrics]).mean())
                else:
                    avg_winrate = 0.0
                    avg_pf = 0.0
                    avg_trades = 0
                    avg_maxdd = 0.0

                row = {**params, "avg_winrate": avg_winrate, "avg_pf": avg_pf,
                       "total_val_trades": avg_trades, "avg_max_dd": avg_maxdd}
                results.append(row)
            else:
                # single backtest on full df
                res = self.run_backtest(ticker, df, signal_generator=signal_generator, signal_params=params)
                row = {**params, "total_trades": res["total_trades"], "winrate": res["winrate"],
                       "pf": res["pf"], "max_dd": res["max_dd"]}
                results.append(row)

        df_res = pd.DataFrame(results)
        return df_res

    def save_report(self, result: dict, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(result, f, indent=2)
