#!/usr/bin/env python3
"""
Compare signal/trade lists produced by the production signal engine vs
the backtester. Input: two folders (csv_per_ticker) or two CSV files per ticker:
- engine output: signals produced by engine (CSV)
- backtest output: trades produced by backtester (CSV)

Expected CSV columns (minimal):
  - id (optional), ticker, entry_time, entry_price, exit_time, exit_price, status
Status: 'WIN' / 'LOSE' / 'OPEN' / 'TP' / 'SL' etc.
This script tries to match trades by (ticker + entry_time) or best-effort fuzzy match.
Outputs:
  - console summary
  - report CSV: reports/compare_<ticker>.csv (if mismatches found)
"""
import argparse
import csv
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class Trade:
    ticker: str
    entry_time: str
    entry_price: Optional[float]
    exit_time: Optional[str]
    exit_price: Optional[float]
    status: Optional[str]
    raw_row: Dict = None

def read_trades_from_csv(path: str) -> List[Trade]:
    rows = []
    with open(path, newline='') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            t = Trade(
                ticker = r.get('ticker') or r.get('symbol') or '',
                entry_time = r.get('entry_time') or r.get('timestamp') or r.get('entry') or '',
                entry_price = safe_float(r.get('entry_price') or r.get('price') or r.get('entry_price')),
                exit_time = r.get('exit_time') or r.get('close_time') or '',
                exit_price = safe_float(r.get('exit_price') or r.get('close_price')),
                status = (r.get('status') or '').upper(),
                raw_row = r
            )
            rows.append(t)
    return rows

def safe_float(v):
    try:
        return float(v) if v not in (None, '', 'None') else None
    except Exception:
        return None

def group_by_ticker(trades: List[Trade]) -> Dict[str, List[Trade]]:
    out = {}
    for t in trades:
        out.setdefault(t.ticker, []).append(t)
    return out

def key_for_trade(t: Trade) -> str:
    # canonical key: ticker + entry_time (trim to seconds)
    return f"{t.ticker}||{normalize_time(t.entry_time)}"

def normalize_time(s: str) -> str:
    if not s:
        return ''
    # try parse ISO or common formats, fallback full string
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except Exception:
            continue
    return s.strip()

def compare_for_ticker(engine_trades: List[Trade], backtest_trades: List[Trade], ticker: str):
    emap = {key_for_trade(t): t for t in engine_trades}
    bmap = {key_for_trade(t): t for t in backtest_trades}

    keys = set(emap.keys()) | set(bmap.keys())
    mismatches = []
    matched = 0
    wins_engine = 0
    wins_backtest = 0
    for k in sorted(keys):
        e = emap.get(k)
        b = bmap.get(k)
        if e and b:
            matched += 1
            # compare statuses and prices
            if (e.status or '').upper() != (b.status or '').upper() or not approx_equal(e.entry_price, b.entry_price) or not approx_equal(e.exit_price, b.exit_price):
                mismatches.append((k, e, b))
            if (e.status or '').upper() in ('WIN','TP'):
                wins_engine += 1
            if (b.status or '').upper() in ('WIN','TP'):
                wins_backtest += 1
        else:
            mismatches.append((k, e, b))
    summary = {
        'ticker': ticker,
        'engine_count': len(engine_trades),
        'backtest_count': len(backtest_trades),
        'matched': matched,
        'mismatches': len(mismatches),
        'wins_engine': wins_engine,
        'wins_backtest': wins_backtest,
    }
    return summary, mismatches

def approx_equal(a, b, tol=1e-6):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    except Exception:
        return False

def dump_mismatch_report(ticker: str, mismatches, outdir='reports'):
    os.makedirs(outdir, exist_ok=True)
    fname = os.path.join(outdir, f"compare_{ticker}.csv")
    with open(fname, 'w', newline='') as fh:
        fieldnames = ['key', 'side', 'ticker', 'entry_time', 'entry_price', 'exit_time', 'exit_price', 'status']
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for k,e,b in mismatches:
            if e:
                writer.writerow({'key': k, 'side':'engine', 'ticker':e.ticker, 'entry_time':e.entry_time, 'entry_price':e.entry_price, 'exit_time':e.exit_time, 'exit_price':e.exit_price, 'status':e.status})
            if b:
                writer.writerow({'key': k, 'side':'backtest', 'ticker':b.ticker, 'entry_time':b.entry_time, 'entry_price':b.entry_price, 'exit_time':b.exit_time, 'exit_price':b.exit_price, 'status':b.status})
    return fname

def discover_csvs_in_folder(folder: str) -> Dict[str,str]:
    """Return mapping ticker -> filepath (by filename without extension)."""
    out = {}
    for nm in os.listdir(folder):
        if not nm.lower().endswith('.csv'):
            continue
        ticker = os.path.splitext(nm)[0]
        out[ticker] = os.path.join(folder, nm)
    return out

def main():
    p = argparse.ArgumentParser(description="Compare engine signals vs backtest trades (CSV per ticker or single CSVs)")
    p.add_argument("--engine", required=True, help="engine csv file or folder with csvs per ticker")
    p.add_argument("--backtest", required=True, help="backtest csv file or folder with csvs per ticker")
    p.add_argument("--outdir", default="reports", help="output report dir")
    args = p.parse_args()

    # detect folder vs file
    engine_is_dir = os.path.isdir(args.engine)
    backtest_is_dir = os.path.isdir(args.backtest)

    engine_map = {}
    backtest_map = {}

    if engine_is_dir:
        engine_map = discover_csvs_in_folder(args.engine)
    else:
        engine_map = { os.path.splitext(os.path.basename(args.engine))[0]: args.engine }

    if backtest_is_dir:
        backtest_map = discover_csvs_in_folder(args.backtest)
    else:
        backtest_map = { os.path.splitext(os.path.basename(args.backtest))[0]: args.backtest }

    tickers = set(list(engine_map.keys()) + list(backtest_map.keys()))
    overall = []
    for t in sorted(tickers):
        eng_path = engine_map.get(t)
        bt_path = backtest_map.get(t)
        eng_trades = read_trades_from_csv(eng_path) if eng_path and os.path.exists(eng_path) else []
        bt_trades = read_trades_from_csv(bt_path) if bt_path and os.path.exists(bt_path) else []
        summary, mismatches = compare_for_ticker(eng_trades, bt_trades, t)
        overall.append(summary)
        if mismatches:
            rpt = dump_mismatch_report(t, mismatches, outdir=args.outdir)
            print(f"[{t}] MISMATCHES: {len(mismatches)} -> report saved {rpt}")
        else:
            print(f"[{t}] OK: matched {summary['matched']} trades, engine:{summary['engine_count']} backtest:{summary['backtest_count']}")
    # print overall table
    print("\nSUMMARY:")
    for s in overall:
        print(f"- {s['ticker']}: engine={s['engine_count']} backtest={s['backtest_count']} matched={s['matched']} mismatches={s['mismatches']} wins_engine={s['wins_engine']} wins_backtest={s['wins_backtest']}")
    # exit code = 0 if no mismatches across all, else 2
    total_mismatches = sum(s['mismatches'] for s in overall)
    sys.exit(0 if total_mismatches==0 else 2)

if __name__ == "__main__":
    main()
