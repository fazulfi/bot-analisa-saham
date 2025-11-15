# tests/test_indicators_against_ta.py
import numpy as np
import pandas as pd
from bot_analisa.indicators.indicators import sma, ema, atr, rsi, macd, compute_indicators
import ta  # reference library
import pytest

def make_sample(n=200):
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    price = np.linspace(100, 130, n) + np.random.normal(0, 0.5, n)
    high = price + np.random.uniform(0.1, 0.6, n)
    low = price - np.random.uniform(0.1, 0.6, n)
    open_ = price + np.random.uniform(-0.3, 0.3, n)
    close = price
    vol = np.random.randint(100, 1000, n)
    df = pd.DataFrame({"Datetime": dates, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol})
    return df

def test_sma_ema_match_ta():
    df = make_sample()
    close = df["Close"]
    # SMA 20
    my_sma = sma(close, 20)
    ta_sma = ta.trend.sma_indicator(close, window=20)
    # compare only after warmup (index >= 19)
    idx = 19
    assert np.allclose(my_sma.iloc[idx:].fillna(0), ta_sma.iloc[idx:].fillna(0), rtol=1e-6, atol=1e-6)

    # EMA 9
    my_ema = ema(close, 9)
    ta_ema = ta.trend.ema_indicator(close, window=9)
    idx = 8
    assert np.allclose(my_ema.iloc[idx:].fillna(0), ta_ema.iloc[idx:].fillna(0), rtol=1e-6, atol=1e-6)

def test_atr_match_ta():
    df = make_sample()
    my_atr = atr(df, period=14)
    # ta's ATR uses AverageTrueRange class
    ta_atr = ta.volatility.AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14).average_true_range()
    # compare after warmup
    idx = 13
    # allow small differences in smoothing; use tolerance
    assert np.allclose(my_atr.iloc[idx:].fillna(0), ta_atr.iloc[idx:].fillna(0), rtol=1e-4, atol=1e-4)

def test_rsi_match_ta():
    df = make_sample()
    my_rsi = rsi(df["Close"], period=14)
    ta_rsi = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
    idx = 13
    assert np.allclose(my_rsi.iloc[idx:].fillna(0), ta_rsi.iloc[idx:].fillna(0), rtol=1e-4, atol=1e-4)

def test_macd_match_ta():
    df = make_sample()
    my_macd, my_signal, my_hist = macd(df["Close"], fast=12, slow=26, signal=9)
    ta_macd = ta.trend.MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
    ta_macd_line = ta_macd.macd()
    ta_signal = ta_macd.macd_signal()
    # compare after warmup
    idx = 25
    assert np.allclose(my_macd.iloc[idx:].fillna(0), ta_macd_line.iloc[idx:].fillna(0), rtol=1e-4, atol=1e-4)
    assert np.allclose(my_signal.iloc[idx:].fillna(0), ta_signal.iloc[idx:].fillna(0), rtol=1e-4, atol=1e-4)
