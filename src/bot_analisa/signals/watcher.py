from __future__ import annotations

from typing import Iterable

import pandas as pd


def process_price_tick(storage, ticker: str, price: float) -> list[str]:
    open_signals = storage.list_signals(ticker=ticker, status="OPEN")
    updates = []
    if open_signals is None or open_signals.empty:
        return updates

    for _, row in open_signals.iterrows():
        sid = row["id"]
        tp = float(row["tp"])
        sl = float(row["sl"])

        if price >= tp:
            if storage.update_signal_status(ticker, sid, "TP", f"hit_tp_price={price}"):
                updates.append(sid)
            continue
        if price <= sl:
            if storage.update_signal_status(ticker, sid, "SL", f"hit_sl_price={price}"):
                updates.append(sid)
    return updates


def simulate_backfill(storage, ticker: str, price_series: pd.Series | pd.DataFrame):
    if isinstance(price_series, pd.DataFrame):
        if "Close" in price_series.columns:
            series = price_series["Close"]
        else:
            series = price_series.iloc[:, 0]
    else:
        series = price_series

    out = {ticker: []}
    for _, price in series.items():
        out[ticker].extend(process_price_tick(storage, ticker, float(price)))
    return out


def watch_once(provider, storage, tickers: Iterable[str] | None = None):
    if tickers is None:
        open_df = storage.list_signals(status="OPEN")
        if open_df is None or open_df.empty:
            return {}
        tickers = sorted(set(open_df["ticker"].astype(str).tolist()))

    result = {}
    for t in tickers:
        price = float(provider.get_last_price(t))
        updated = process_price_tick(storage, t, price)
        if updated:
            result[t] = updated
    return result
