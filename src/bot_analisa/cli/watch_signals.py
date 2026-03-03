from __future__ import annotations

import argparse
import time

from bot_analisa.data.provider import DataProvider
from bot_analisa.signals.storage import SignalStorage
from bot_analisa.signals.watcher import watch_once


def main() -> None:
    p = argparse.ArgumentParser(description="Watch OPEN signals from SQLite and update TP/SL status")
    p.add_argument("--tickers", default=None, help="Comma separated ticker list; default auto from OPEN signals")
    p.add_argument("--data-folder", default="data")
    p.add_argument("--signals-folder", default="signals")
    p.add_argument("--once", action="store_true")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--interval", type=int, default=300)
    args = p.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None
    provider = DataProvider(data_folder=args.data_folder)
    storage = SignalStorage(folder=args.signals_folder)

    if args.once or not args.loop:
        print(watch_once(provider, storage, tickers))
        return

    while True:
        print(watch_once(provider, storage, tickers))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
