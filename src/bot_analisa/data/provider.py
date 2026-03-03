from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class DataProvider:
    """Simple market data provider with CSV cache and yfinance fallback."""

    def __init__(self, data_folder: str = "data") -> None:
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)

    def _file_path(self, ticker: str) -> Path:
        return self.data_folder / f"{ticker}.csv"

    def _ensure_datetime_column(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if "Datetime" not in out.columns:
            if "Date" in out.columns:
                out = out.rename(columns={"Date": "Datetime"})
            elif out.index.name in ("Datetime", "Date"):
                out = out.reset_index().rename(columns={out.index.name: "Datetime"})
            else:
                out = out.reset_index().rename(columns={out.columns[0]: "Datetime"})

        out["Datetime"] = pd.to_datetime(out["Datetime"], errors="coerce")
        out = out.dropna(subset=["Datetime"]).sort_values("Datetime")

        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in out.columns:
                out[col] = pd.NA

        return out[["Datetime", "Open", "High", "Low", "Close", "Volume"]]

    def _download_yfinance(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        import yfinance as yf

        raw = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
        if raw is None or raw.empty:
            return pd.DataFrame(columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])

        raw = raw.reset_index()
        if "Datetime" not in raw.columns and "Date" in raw.columns:
            raw = raw.rename(columns={"Date": "Datetime"})
        return self._ensure_datetime_column(raw)

    def get_historical(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        path = self._file_path(ticker)
        if path.exists():
            cached = pd.read_csv(path)
            return self._ensure_datetime_column(cached)
        return self._download_yfinance(ticker, period=period, interval=interval)

    def fetch_and_save(self, ticker: str, period: str = "1y", interval: str = "1d", force: bool = False) -> Optional[str]:
        new_df = self._download_yfinance(ticker, period=period, interval=interval)
        if new_df.empty:
            return None

        path = self._file_path(ticker)
        if path.exists() and not force:
            old_df = self._ensure_datetime_column(pd.read_csv(path))
            merged = pd.concat([old_df, new_df], ignore_index=True)
            merged = merged.drop_duplicates(subset=["Datetime"], keep="last").sort_values("Datetime")
        else:
            merged = new_df

        merged.to_csv(path, index=False)
        return str(path)

    def get_last_price(self, ticker: str) -> float:
        df = self.get_historical(ticker, period="7d", interval="1d")
        if df.empty:
            raise ValueError(f"No price data for ticker {ticker}")
        return float(df.iloc[-1]["Close"])
