from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid

import pandas as pd


DEFAULT_COLUMNS = [
    "id", "ticker", "timestamp", "entry_price", "tp", "sl", "signal",
    "status", "status_info", "strategy_version", "reason", "updated_at"
]


class SignalStorage:
    """SQLite-backed signal storage.

    The constructor keeps the existing `folder` API and stores DB at `<folder>/signals.db`.
    """

    def __init__(self, folder: str = "signals") -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db_path = self.folder / "signals.db"
        self._init_db()
        self._migrate_csv_files()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    tp REAL NOT NULL,
                    sl REAL NOT NULL,
                    signal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_info TEXT,
                    strategy_version TEXT,
                    reason TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)")

    def _migrate_csv_files(self) -> None:
        csv_files = sorted(self.folder.glob("*.csv"))
        if not csv_files:
            return

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
            except Exception:
                continue

            if df.empty:
                continue

            if "ticker" not in df.columns:
                df["ticker"] = csv_file.stem
            if "entry_price" not in df.columns and "entry" in df.columns:
                df["entry_price"] = df["entry"]

            now = datetime.now(timezone.utc).isoformat()
            rows = []
            for _, row in df.iterrows():
                try:
                    rows.append(
                        (
                            str(row.get("id") or uuid.uuid4()),
                            str(row.get("ticker") or csv_file.stem),
                            str(row.get("timestamp") or now),
                            float(row.get("entry_price")),
                            float(row.get("tp")),
                            float(row.get("sl")),
                            str(row.get("signal") or row.get("side") or "BUY"),
                            str(row.get("status") or "OPEN"),
                            str(row.get("status_info") or ""),
                            str(row.get("strategy_version") or "unknown"),
                            str(row.get("reason") or ""),
                            str(row.get("updated_at") or ""),
                        )
                    )
                except Exception:
                    continue

            if not rows:
                continue

            with self._connect() as conn:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO signals
                    (id, ticker, timestamp, entry_price, tp, sl, signal, status, status_info, strategy_version, reason, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )

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
            "updated_at": signal.get("updated_at", ""),
        }

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO signals
                (id, ticker, timestamp, entry_price, tp, sl, signal, status, status_info, strategy_version, reason, updated_at)
                VALUES (:id, :ticker, :timestamp, :entry_price, :tp, :sl, :signal, :status, :status_info, :strategy_version, :reason, :updated_at)
                """,
                record,
            )
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
        query = "SELECT * FROM signals"
        clauses = []
        params: list[str] = []
        if ticker is not None:
            clauses.append("ticker = ?")
            params.append(str(ticker))
        if status is not None:
            clauses.append("status = ?")
            params.append(str(status))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp, id"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            return pd.DataFrame(columns=DEFAULT_COLUMNS)

        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[DEFAULT_COLUMNS]

    def update_signal_status(self, ticker: str, signal_id: str, new_status: str, status_info: str = "") -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE signals
                SET status = ?, status_info = ?, updated_at = ?
                WHERE ticker = ? AND id = ?
                """,
                (
                    str(new_status),
                    str(status_info),
                    datetime.now(timezone.utc).isoformat(),
                    str(ticker),
                    str(signal_id),
                ),
            )
            return cur.rowcount > 0
