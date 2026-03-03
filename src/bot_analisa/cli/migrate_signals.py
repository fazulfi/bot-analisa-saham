from __future__ import annotations

import argparse
import csv
from pathlib import Path

from bot_analisa.signals.storage import SignalStorage


def migrate_folder(signals_folder: str) -> dict:
    folder = Path(signals_folder)
    folder.mkdir(parents=True, exist_ok=True)
    legacy_dir = folder / "legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)

    storage = SignalStorage(folder=str(folder))
    imported = 0
    scanned = 0

    for csv_path in sorted(folder.glob("*.csv")):
        scanned += 1
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker") or csv_path.stem
                entry_price = row.get("entry_price") or row.get("entry")
                tp = row.get("tp")
                sl = row.get("sl")
                if not ticker or entry_price in (None, "") or tp in (None, "") or sl in (None, ""):
                    continue
                signal = {
                    "id": row.get("id") or None,
                    "ticker": ticker,
                    "timestamp": row.get("timestamp") or None,
                    "entry_price": entry_price,
                    "tp": tp,
                    "sl": sl,
                    "signal": row.get("signal") or row.get("side") or "BUY",
                    "status": row.get("status") or "OPEN",
                    "status_info": row.get("status_info") or "",
                    "strategy_version": row.get("strategy_version") or "unknown",
                    "reason": row.get("reason") or "",
                    "updated_at": row.get("updated_at") or "",
                }
                storage.save_signal_dict(signal)
                imported += 1

        target = legacy_dir / f"{csv_path.name}.bak"
        csv_path.rename(target)

    return {"scanned_csv_files": scanned, "imported_rows": imported, "db": str(storage.db_path)}


def main() -> None:
    p = argparse.ArgumentParser(description="One-time migration of legacy signals CSV files into SQLite")
    p.add_argument("--signals-folder", default="signals", help="Folder containing legacy *.csv and signals.db")
    args = p.parse_args()

    res = migrate_folder(args.signals_folder)
    print(res)


if __name__ == "__main__":
    main()
