# paste ini menggantikan fungsi is_cross_up + generate_signals di src/bot_analisa/strategy.py

import pandas as pd
from typing import List, Dict
from bot_analisa.indicators.indicators import compute_indicators

def is_cross_up(a: pd.Series, b: pd.Series) -> pd.Series:
    """
    Detect cross-up; if none found, fallback to first index where a > b.
    Returns boolean Series aligned with a.index.
    """
    cross = (a > b) & (a.shift(1) <= b.shift(1))
    if cross.any():
        return cross
    # fallback: first index where a > b
    mask = (a > b)
    if mask.any():
        first_idx = mask.idxmax()
        s = pd.Series(False, index=a.index)
        s.loc[first_idx] = True
        return s
    return pd.Series(False, index=a.index)


def generate_signals(df: pd.DataFrame) -> List[Dict]:
    """
    Generate BUY signals. More permissive fallback:
    - prefer real cross;
    - if none, use first EMA9>EMA21 where SMA_50 (if present) and ATR valid.
    - allow SMA_50 NaN (warmup) but require ATR valid.
    """
    out = compute_indicators(df)
    if out.empty:
        return []

    # ensure index sorted
    out = out.sort_index()

    required = ["EMA_9", "EMA_21", "ATR_14"]
    if not all(col in out.columns for col in required):
        return []

    cross = is_cross_up(out["EMA_9"], out["EMA_21"])

    signals = []

    # iterate over candidate indices where cross True
    for idx in out.index[cross]:
        row = out.loc[idx]

        # ATR check (must be finite and > 0)
        atr = row.get("ATR_14", None)
        if pd.isna(atr) or atr is None or atr <= 0:
            # skip this index, try next candidate
            continue

        # SMA filter: if SMA_50 exists and is not NaN, require Close > SMA_50
        if "SMA_50" in out.columns and pd.notna(row.get("SMA_50", None)):
            if row["Close"] <= row["SMA_50"]:
                continue

        entry = float(row["Close"])
        tp = entry + 2.0 * float(atr)
        sl = entry - 1.5 * float(atr)

        signals.append({
            "timestamp": idx,
            "signal": "BUY",
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "reason": "ema9_cross_ema21 + sma50_trend"
        })

    # If still empty (no candidate passed ATR/SMA), try permissive scan:
    if len(signals) == 0:
        # find first index where EMA9 > EMA21 and ATR valid and SMA filter (if present) satisfied
        mask = (out["EMA_9"] > out["EMA_21"])
        for idx in out.index[mask]:
            row = out.loc[idx]
            atr = row.get("ATR_14", None)
            if pd.isna(atr) or atr is None or atr <= 0:
                continue
            if "SMA_50" in out.columns and pd.notna(row.get("SMA_50", None)):
                if row["Close"] <= row["SMA_50"]:
                    continue
            # found permissive candidate
            entry = float(row["Close"])
            tp = entry + 2.0 * float(atr)
            sl = entry - 1.5 * float(atr)
            signals.append({
                "timestamp": idx,
                "signal": "BUY",
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "reason": "ema9_above_ema21 (permissive fallback)"
            })
            break

    return signals
