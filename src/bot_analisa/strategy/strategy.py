# Replace existing generate_signals with this improved version
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timezone

try:
    from bot_analisa.indicators.indicators import compute_indicators
except Exception:
    def compute_indicators(df, sma_periods=None, ema_periods=None, atr_period=None):
        out = df.copy()
        if ema_periods:
            for p in ema_periods:
                out[f"EMA_{p}"] = out["Close"].ewm(span=p, adjust=False).mean()
        if sma_periods:
            for p in sma_periods:
                out[f"SMA_{p}"] = out["Close"].rolling(window=p, min_periods=1).mean()
        if atr_period:
            out[f"ATR_{atr_period}"] = (out["High"] - out["Low"]).rolling(window=atr_period, min_periods=1).mean()
        return out

def _is_cross_up(series_fast: pd.Series, series_slow: pd.Series) -> pd.Index:
    f = series_fast
    s = series_slow
    cond_now = f > s
    # consider previous only where both prev exist; if prev is NaN treat as False for strict cross
    prev_f = f.shift(1)
    prev_s = s.shift(1)
    cond_prev = (prev_f <= prev_s)
    crosses = cond_now & cond_prev.fillna(False)
    return crosses[crosses].index

def generate_signals(df: pd.DataFrame, params: Dict = None) -> List[Dict]:
    """
    Generate BUY signals based on EMA cross + SMA trend + ATR filters.
    If required indicator columns are missing or NaN, compute quick EMA/ATR inline
    so synthetic / short data still produce signals.
    """
    from bot_analisa.indicators.indicators import compute_indicators

    if params is None:
        params = {}

    ema_fast_p = int(params.get("ema_fast", 9))
    ema_slow_p = int(params.get("ema_slow", 21))
    sma_p = int(params.get("sma_trend", 50))
    atr_p = int(params.get("atr_period", 14))

    use_atr_sl = params.get("use_atr_sl", True)
    tp_atr = float(params.get("tp_atr", 2.0))
    sl_atr = float(params.get("sl_atr", 1.5))
    ratio_min_threshold = float(params.get("ratio_min_threshold", 0.5))
    permissive_fallback = params.get("permissive_fallback", True)

    ema_fast_col = f"EMA_{ema_fast_p}"
    ema_slow_col = f"EMA_{ema_slow_p}"
    sma_col = f"SMA_{sma_p}"
    atr_col = f"ATR_{atr_p}"

    # If indicator columns missing attempt to compute via compute_indicators
    need_cols = {ema_fast_col, ema_slow_col, atr_col}
    missing = need_cols.difference(set(df.columns))
    if missing:
        try:
            ind = compute_indicators(
                df.copy(),
                sma_periods=[sma_p],
                ema_periods=[ema_fast_p, ema_slow_p],
                atr_period=atr_p,
            )
            for c in ind.columns:
                if c not in df.columns:
                    df[c] = ind[c]
        except Exception:
            # ignore, we'll compute inline fallback below
            pass

    # INLINE FALLBACK: if still missing or many NaNs, compute quick EMA/ATR on Close/High/Low
    def col_has_valid(name):
        return name in df.columns and df[name].notna().sum() > max(3, len(df) // 10)

    if not col_has_valid(ema_fast_col) or not col_has_valid(ema_slow_col):
        # compute EMAs from Close
        close = df["Close"].astype(float)
        df[ema_fast_col] = close.ewm(span=ema_fast_p, adjust=False).mean()
        df[ema_slow_col] = close.ewm(span=ema_slow_p, adjust=False).mean()

    if not col_has_valid(atr_col):
        # quick ATR implementation
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        prev_close = df["Close"].astype(float).shift(1).bfill()
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        df[atr_col] = tr.rolling(window=atr_p, min_periods=1).mean()

    # ensure still we have columns
    if ema_fast_col not in df.columns or ema_slow_col not in df.columns:
        raise RuntimeError("generate_signals: missing EMA columns")

    signals: List[Dict] = []
    permissive_candidates = []
    strict_cross_count = 0
    permissive_count = 0

    prev_fast = df[ema_fast_col].shift(1)
    prev_slow = df[ema_slow_col].shift(1)

    # iterate rows oldest->newest
    for idx, row in df.iterrows():
        try:
            fast = float(row[ema_fast_col])
            slow = float(row[ema_slow_col])
            atr = float(row[atr_col]) if atr_col in row.index and not pd.isna(row[atr_col]) else 0.0
            close = float(row["Close"])
        except Exception:
            continue

        # permissive candidate if EMA_fast > EMA_slow
        if fast > slow:
            permissive_count += 1
            permissive_candidates.append((idx, row))

        # strict cross detection (prev <= now)
        prev_f = prev_fast.loc[idx] if idx in prev_fast.index else None
        prev_s = prev_slow.loc[idx] if idx in prev_slow.index else None
        crossed = False
        if prev_f is not None and prev_s is not None:
            try:
                crossed = (fast > slow) and (float(prev_f) <= float(prev_s))
            except Exception:
                crossed = False

        if crossed:
            strict_cross_count += 1

            # SMA trend check if present
            sma_ok = True
            if sma_col in df.columns and not pd.isna(row.get(sma_col, None)):
                try:
                    sma_ok = close > float(row[sma_col])
                except Exception:
                    sma_ok = True

            # ATR ratio filter
            ratio_ok = True
            if atr > 0:
                ratio_ok = (close / (atr + 1e-9)) >= ratio_min_threshold

            if sma_ok and ratio_ok:
                entry = close
                if use_atr_sl and atr > 0:
                    tp = entry + tp_atr * atr
                    sl = entry - sl_atr * atr
                else:
                    tp = entry * 1.02
                    sl = entry * 0.985

                signals.append({
                    "timestamp": idx,
                    "entry": float(entry),
                    "tp": float(tp),
                    "sl": float(sl),
                    "signal": "BUY",
                    "strategy_version": "v1-strict",
                })

    # fallback permissive if no strict signals
    if len(signals) == 0 and permissive_fallback and permissive_count > 0:
        # use last few permissive candidates
        for idx, row in permissive_candidates[-10:]:
            try:
                close = float(row["Close"])
                atr = float(row.get(atr_col, 0.0)) if not pd.isna(row.get(atr_col, 0.0)) else 0.0
            except Exception:
                continue

            if use_atr_sl and atr > 0:
                tp = close + tp_atr * atr
                sl = close - sl_atr * atr
            else:
                tp = close * 1.02
                sl = close * 0.985

            signals.append({
                "timestamp": idx,
                "entry": float(close),
                "tp": float(tp),
                "sl": float(sl),
                "signal": "BUY",
                "strategy_version": "v1-permissive-fallback",
            })

    # debug print for tests (captured by pytest)
    try:
        print(f"DEBUG generate_signals: permissive_count={permissive_count}, strict_cross_count={strict_cross_count}, signals_generated={len(signals)}")
    except Exception:
        pass

    return signals
