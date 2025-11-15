# tests/test_cleaner.py
import pandas as pd
import numpy as np
from bot_analisa.data.cleaner import clean
import pytest

def make_sample_with_issues():
    # create sample datetime with duplicates, missing, tz naive and bad values
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    price = np.linspace(100, 110, len(dates))
    df = pd.DataFrame({
        "Date": dates.astype(str),  # as string, to test parsing
        "Open": price,
        "High": price + 1,
        "Low": price - 1,
        "Close": price + 0.5,
        "Volume": [100, 120, 0, 150, 160, 170, 180, 190, 200, 210]
    })
    # introduce missing
    df.loc[2, "Close"] = np.nan
    # introduce duplicate datetime (duplicate index later)
    dup = df.iloc[[4]].copy()
    df = pd.concat([df.iloc[:5], dup, df.iloc[5:]], ignore_index=True)
    # introduce an outlier big jump
    df.loc[7, "Close"] = df["Close"].iloc[7] * 1000
    return df

def test_clean_basic():
    df = make_sample_with_issues()
    cfg = {"tz": "UTC", "missing_method": "ffill", "outlier_z": 10.0, "freq": "D"}
    cleaned = clean(df, cfg=cfg)
    # basic checks
    assert isinstance(cleaned.index, pd.DatetimeIndex)
    assert cleaned.index.tz is not None  # timezone-aware
    # no duplicate datetimes
    assert not cleaned.index.duplicated().any()
    # mandatory columns present
    for c in ["Open","High","Low","Close","Volume"]:
        assert c in cleaned.columns
    # no NaN in OHLC after ffill (for our config)
    assert cleaned[["Open","High","Low","Close"]].notna().all().all()
