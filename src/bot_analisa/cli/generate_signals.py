from __future__ import annotations

import argparse

from bot_analisa.data.cleaner import clean
from bot_analisa.data.provider import DataProvider
from bot_analisa.indicators.indicators import compute_indicators
from bot_analisa.signals.storage import SignalStorage
from bot_analisa.strategy.strategy import generate_signals


def main() -> None:
    p = argparse.ArgumentParser(description="Generate trading signals and persist them into SQLite storage")
    p.add_argument("tickers", nargs="+", help="Ticker list, e.g. BBCA.JK BBRI.JK")
    p.add_argument("--period", default="1y")
    p.add_argument("--interval", default="1d")
    p.add_argument("--data-folder", default="data")
    p.add_argument("--signals-folder", default="signals")
    args = p.parse_args()

    provider = DataProvider(data_folder=args.data_folder)
    storage = SignalStorage(folder=args.signals_folder)

    for ticker in args.tickers:
        df = provider.get_historical(ticker, period=args.period, interval=args.interval)
        if df is None or df.empty:
            print(f"{ticker}: no data")
            continue

        cleaned = clean(df)
        enriched = compute_indicators(cleaned)
        signals = generate_signals(enriched)

        count = 0
        for sig in signals:
            payload = {
                "ticker": ticker,
                "timestamp": sig.get("timestamp"),
                "entry_price": sig.get("entry_price", sig.get("entry")),
                "tp": sig.get("tp"),
                "sl": sig.get("sl"),
                "signal": sig.get("signal", "BUY"),
                "status": "OPEN",
                "strategy_version": sig.get("strategy_version", "v1"),
                "reason": sig.get("reason", ""),
            }
            storage.save_signal_dict(payload)
            count += 1

        print(f"{ticker}: saved {count} signals into {storage.db_path}")


if __name__ == "__main__":
    main()
