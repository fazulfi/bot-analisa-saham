"""
Simple storage adapter for notifier.
Fallback: file .notify_signals.json in repo root.
Data shape: list of signals (dict). Each signal at least has id/status fields.
API:
 - list_open_unnotified_signals() -> list
 - update_signal_notified(signal_id) -> bool
 - add_signal_local(signal) -> None (for testing / quick add)
"""
import json
import os
from typing import List, Dict

FILE_PATH = os.getenv("NOTIFY_STATE_FILE", ".notify_signals.json")

def _read_all() -> List[Dict]:
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, "r", encoding="utf8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def _write_all(data: List[Dict]):
    with open(FILE_PATH, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def list_open_unnotified_signals() -> List[Dict]:
    """
    Return signals with status == 'OPEN' and not 'notified': True.
    """
    all_s = _read_all()
    return [s for s in all_s if s.get("status") == "OPEN" and not s.get("notified")]

def update_signal_notified(signal_id: str) -> bool:
    all_s = _read_all()
    changed = False
    for s in all_s:
        if s.get("id") == signal_id:
            s["notified"] = True
            changed = True
    if changed:
        _write_all(all_s)
    return changed

def add_signal_local(signal: Dict):
    all_s = _read_all()
    all_s.append(signal)
    _write_all(all_s)

def get_signal_by_id(signal_id: str) -> Dict:
    for s in _read_all():
        if s.get("id") == signal_id:
            return s
    return None
