from typing import Dict, List

import pandas as pd


def generate_signals(df: pd.DataFrame, params: Dict | None = None) -> List[Dict]:
    """
    Generate BUY signals based on EMA cross + optional SMA/ATR filters.

    Params:
      - ema_fast (default 9)
      - ema_slow (default 21)
      - sma_trend (default 50)
      - atr_period (default 14)
      - use_atr_sl (default True)
      - tp_atr (default 2.0)
      - sl_atr (default 1.5)
      - ratio_min_threshold (default 0.5)
      - permissive_fallback (default True)
      - only_latest (default False): when True evaluate only the latest candle and emit max 1 signal
    """
    from bot_analisa.indicators.indicators import compute_indicators

    params = params or {}

    ema_fast_p = int(params.get("ema_fast", 9))
    ema_slow_p = int(params.get("ema_slow", 21))
    sma_p = int(params.get("sma_trend", 50))
    atr_p = int(params.get("atr_period", 14))

    use_atr_sl = bool(params.get("use_atr_sl", True))
    tp_atr = float(params.get("tp_atr", 2.0))
    sl_atr = float(params.get("sl_atr", 1.5))
    ratio_min_threshold = float(params.get("ratio_min_threshold", 0.5))
    permissive_fallback = bool(params.get("permissive_fallback", True))
    only_latest = bool(params.get("only_latest", False))

    ema_fast_col = f"EMA_{ema_fast_p}"
    ema_slow_col = f"EMA_{ema_slow_p}"
    sma_col = f"SMA_{sma_p}"
    atr_col = f"ATR_{atr_p}"

    out = df.copy()
    need_cols = {ema_fast_col, ema_slow_col, atr_col}
    missing = need_cols.difference(set(out.columns))
    if missing:
        ind = compute_indicators(
            out,
            sma_periods=[sma_p],
            ema_periods=[ema_fast_p, ema_slow_p],
            atr_period=atr_p,
        )
        for c in ind.columns:
            if c not in out.columns:
                out[c] = ind[c]

    if ema_fast_col not in out.columns or ema_slow_col not in out.columns:
        raise RuntimeError("generate_signals: missing EMA columns")

    prev_fast = out[ema_fast_col].shift(1)
    prev_slow = out[ema_slow_col].shift(1)

    rows = [out.iloc[-1]] if only_latest and not out.empty else [r for _, r in out.iterrows()]
    idxs = [out.index[-1]] if only_latest and not out.empty else list(out.index)

    signals: List[Dict] = []

    for idx, row in zip(idxs, rows):
        try:
            close = float(row["Close"])
            fast = float(row[ema_fast_col])
            slow = float(row[ema_slow_col])
            atr = float(row[atr_col]) if atr_col in row.index and not pd.isna(row[atr_col]) else 0.0
        except Exception:
            continue

        # strict cross on current bar
        crossed = False
        try:
            pf = float(prev_fast.loc[idx])
            ps = float(prev_slow.loc[idx])
            crossed = (fast > slow) and (pf <= ps)
        except Exception:
            crossed = False

        sma_ok = True
        if sma_col in out.columns and not pd.isna(row.get(sma_col)):
            try:
                sma_ok = close > float(row[sma_col])
            except Exception:
                sma_ok = True

        ratio_ok = True
        if atr > 0:
            ratio_ok = (close / (atr + 1e-9)) >= ratio_min_threshold

        should_signal = crossed and sma_ok and ratio_ok
        if not should_signal and permissive_fallback:
            # permissive only if fast above slow and basic filters pass
            should_signal = (fast > slow) and sma_ok and ratio_ok

        if should_signal:
            if use_atr_sl and atr > 0:
                tp = close + tp_atr * atr
                sl = close - sl_atr * atr
            else:
                tp = close * 1.02
                sl = close * 0.985

            signals.append(
                {
                    "timestamp": idx,
                    "entry": float(close),
                    "tp": float(tp),
                    "sl": float(sl),
                    "signal": "BUY",
                    "strategy_version": "v1",
                }
            )

    if only_latest and signals:
        return [signals[-1]]
    return signals
