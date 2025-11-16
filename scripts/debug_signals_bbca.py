# debug_signals_bbca.py
import pandas as pd
from bot_analisa.indicators.indicators import compute_indicators

df = pd.read_csv("data/BBCA.JK.csv", parse_dates=["Datetime"], index_col="Datetime")
ind = compute_indicators(df, sma_periods=[50], ema_periods=[9,21], atr_period=14)

ema_fast = 'EMA_9'
ema_slow = 'EMA_21'
sma_col = 'SMA_50'
atr_col = 'ATR_14'

print("Data rows:", len(ind))
# How many rows where fast > slow (permissive)
mask_perm = ind[ema_fast] > ind[ema_slow]
print("Permissive (EMA_fast>EMA_slow) count:", int(mask_perm.sum()))

# How many strict crosses (prev <= slow and now > slow)
prev_fast = ind[ema_fast].shift(1)
prev_slow = ind[ema_slow].shift(1)
cross_mask = (ind[ema_fast] > ind[ema_slow]) & (prev_fast <= prev_slow)
print("Strict cross up count:", int(cross_mask.sum()))

# Show last 30 rows of indicators to inspect
print("\n=== Last 30 indicator rows ===")
print(ind[[ema_fast, ema_slow, sma_col, atr_col, 'Close']].tail(30))

# Show a list of candidate indexes with values (if any permissive)
cands = ind[mask_perm].tail(20)
if len(cands):
    print("\n=== Sample permissive candidates (last 20) ===")
    print(cands[[ema_fast, ema_slow, sma_col, atr_col, 'Close']])
else:
    print("\nNo permissive candidates found.")
