from __future__ import annotations

import argparse
import hashlib

from bot_analisa.data.cleaner import clean
from bot_analisa.data.provider import DataProvider
from bot_analisa.indicators.indicators import compute_indicators
from bot_analisa.signals.storage import SignalStorage
from bot_analisa.strategy.strategy import generate_signals


def build_signal_id(ticker: str, ts: str, strategy_version: str, side: str) -> str:
    raw = f"{ticker}:{ts}:{strategy_version}:{side}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description="EOD signal generation: latest closed bar -> SQLite")
    p.add_argument("tickers", nargs="+", help="Ticker list, e.g. BBCA.JK BBRI.JK")
    p.add_argument("--period", default="1y")
    p.add_argument("--interval", default="1d")
    p.add_argument("--data-folder", default="data")
    p.add_argument("--signals-folder", default="signals")
    args = p.parse_args()

    provider = DataProvider(data_folder=args.data_folder)
    storage = SignalStorage(folder=args.signals_folder)

    for ticker in args.tickers:
        # refresh cache first, then read historical
        provider.fetch_and_save(ticker, period=args.period, interval=args.interval, force=False)
        df = provider.get_historical(ticker, period=args.period, interval=args.interval)
        if df is None or df.empty:
            print(f"{ticker}: no data")
            continue

        cleaned = clean(df)
        enriched = compute_indicators(cleaned)
        signals = generate_signals(enriched, {"only_latest": True})

        saved = 0
        for sig in signals:
            ts = sig.get("timestamp")
            entry_price = sig.get("entry_price", sig.get("entry"))
            tp = sig.get("tp")
            sl = sig.get("sl")

            # strict validation for live mode
            if ts is None or entry_price is None or tp is None or sl is None:
                continue

            try:
                entry_price = float(entry_price)
                tp = float(tp)
                sl = float(sl)
            except Exception:
                continue

            side = str(sig.get("signal", "BUY"))
            strategy_version = str(sig.get("strategy_version", "v1"))
            ts_text = str(ts)

            payload = {
                "id": build_signal_id(ticker, ts_text, strategy_version, side),
                "ticker": ticker,
                "timestamp": ts_text,
                "entry_price": entry_price,
                "tp": tp,
                "sl": sl,
                "signal": side,
                "status": "OPEN",
                "strategy_version": strategy_version,
                "reason": sig.get("reason", ""),
            }
            storage.save_signal_dict(payload)
            saved += 1

        print(f"{ticker}: saved {saved} signal(s) into {storage.db_path}")


if __name__ == "__main__":
    main()
