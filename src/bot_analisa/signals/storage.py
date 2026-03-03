from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import uuid

import fcntl
import pandas as pd


DEFAULT_COLUMNS = [
    "id", "ticker", "timestamp", "entry_price", "tp", "sl", "signal",
    "status", "status_info", "strategy_version", "reason", "updated_at"
]


class SignalStorage:
    def __init__(self, folder: str = "signals") -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _path(self, ticker: str) -> Path:
        return self.folder / f"{ticker}.csv"

    @contextmanager
    def _file_lock(self, ticker: str):
        lock_path = self.folder / f"{ticker}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load_unlocked(self, ticker: str) -> pd.DataFrame:
        path = self._path(ticker)
        if not path.exists():
            return pd.DataFrame(columns=DEFAULT_COLUMNS)

        df = pd.read_csv(path)
        if "entry" in df.columns and "entry_price" not in df.columns:
            df["entry_price"] = df["entry"]
        if "entry" in df.columns:
            df = df.drop(columns=["entry"])
        return df

    def _save_unlocked(self, ticker: str, df: pd.DataFrame) -> None:
        path = self._path(ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), suffix=".tmp") as tmp:
            df.to_csv(tmp.name, index=False)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def save_signal_dict(self, signal: dict) -> dict:
        ticker = signal["ticker"]
        entry = signal.get("entry_price", signal.get("entry"))
        record = {
            "id": signal.get("id", str(uuid.uuid4())),
            "ticker": ticker,
            "timestamp": signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "entry_price": float(entry),
            "tp": float(signal["tp"]),
            "sl": float(signal["sl"]),
            "signal": signal.get("signal", signal.get("side", "BUY")),
            "status": signal.get("status", "OPEN"),
            "status_info": signal.get("status_info", ""),
            "strategy_version": signal.get("strategy_version", "unknown"),
            "reason": signal.get("reason", ""),
        }
        with self._file_lock(ticker):
            df = self._load_unlocked(ticker)
            df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            self._save_unlocked(ticker, df)
        return record

    def add_signal(self, ticker: str, entry_price: float, tp: float, sl: float, strategy_version: str = "v1", **kwargs) -> dict:
        sig = {
            "ticker": ticker,
            "entry_price": entry_price,
            "tp": tp,
            "sl": sl,
            "strategy_version": strategy_version,
            **kwargs,
        }
        return self.save_signal_dict(sig)

    def list_signals(self, ticker: str | None = None, status: str | None = None) -> pd.DataFrame:
        if ticker:
            with self._file_lock(ticker):
                df = self._load_unlocked(ticker)
            if status:
                return df[df["status"] == status].copy()
            return df

        files = sorted(self.folder.glob("*.csv"))
        if not files:
            return pd.DataFrame(columns=DEFAULT_COLUMNS)
        frames = []
        for f in files:
            symbol = f.stem
            with self._file_lock(symbol):
                frames.append(self._load_unlocked(symbol))
        all_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=DEFAULT_COLUMNS)
        if status:
            all_df = all_df[all_df["status"] == status]
        return all_df

    def update_signal_status(self, ticker: str, signal_id: str, new_status: str, status_info: str = "") -> bool:
        with self._file_lock(ticker):
            df = self._load_unlocked(ticker)
            if df.empty or "id" not in df.columns:
                return False
            mask = df["id"].astype(str) == str(signal_id)
            if not mask.any():
                return False
            df.loc[mask, "status"] = new_status
            df.loc[mask, "status_info"] = status_info
            df.loc[mask, "updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_unlocked(ticker, df)
        return True
