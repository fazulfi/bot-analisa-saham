from __future__ import annotations

import numpy as np
import pandas as pd


def _coerce_datetime_col(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Datetime" in out.columns:
        col = "Datetime"
    elif "Date" in out.columns:
        col = "Date"
    else:
        col = out.columns[0]

    out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
    out = out.dropna(subset=[col]).rename(columns={col: "Datetime"})
    return out


def clean(df: pd.DataFrame, cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or {}
    missing_method = cfg.get("missing_method", "ffill")
    outlier_z = float(cfg.get("outlier_z", 10.0))
    freq = cfg.get("freq", None)

    out = _coerce_datetime_col(df)
    out = out.sort_values("Datetime").drop_duplicates(subset=["Datetime"], keep="last")
    out = out.set_index("Datetime")

    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")

    required = ["Open", "High", "Low", "Close", "Volume"]
    for c in required:
        if c not in out.columns:
            out[c] = np.nan
    out[required] = out[required].apply(pd.to_numeric, errors="coerce")

    if freq:
        out = out.asfreq(freq)

    if missing_method == "ffill":
        out[required] = out[required].ffill()
    elif missing_method == "bfill":
        out[required] = out[required].bfill()

    close = out["Close"]
    std = float(close.std(skipna=True) or 0.0)
    if std > 0:
        z = ((close - close.mean(skipna=True)) / std).abs()
        out.loc[z > outlier_z, "Close"] = np.nan
        if missing_method == "ffill":
            out["Close"] = out["Close"].ffill()
        elif missing_method == "bfill":
            out["Close"] = out["Close"].bfill()

    return out
