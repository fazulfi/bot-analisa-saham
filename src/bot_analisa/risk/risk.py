"""
risk.py
Menghitung TP/SL berdasarkan ATR atau persentase fixed.
"""

def compute_tp_sl(entry_price, atr, multiplier=2):
    tp = entry_price + atr * multiplier
    sl = entry_price - atr * multiplier
    return tp, sl
