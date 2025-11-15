"""
risk.py

Fungsi-fungsi untuk menghitung TP/SL dan ukuran posisi (position sizing).

Fitur:
- compute_tp_sl(entry_price, atr=None, params=None)
  * params can specify mode:
    - mode="atr" -> TP = entry + tp_atr_mul * ATR ; SL = entry - sl_atr_mul * ATR
    - mode="percent" -> TP = entry * (1 + tp_pct) ; SL = entry * (1 - sl_pct)
  * If both atr and percent provided, mode selects which to use.

- compute_position_size(account_balance, entry_price, sl_price, risk_per_trade=0.01, lot_size=1)
  * returns number_of_shares (int) such that (entry - sl) * qty <= account_balance * risk_per_trade
  * respects minimum lot_size (round down to nearest lot multiple)

Notes:
- Harga diserahkan dalam satuan harga (float).
- Fungsi defensif terhadap input invalid (raises ValueError).
"""

from typing import Tuple, Optional, Dict
import math


def compute_tp_sl(entry_price: float,
                  atr: Optional[float] = None,
                  params: Optional[Dict] = None) -> Tuple[float, float]:
    """
    Compute target profit (TP) and stop loss (SL).

    params example:
      {"mode": "atr", "tp_atr_mul": 2.0, "sl_atr_mul": 1.5}
      OR
      {"mode": "percent", "tp_pct": 0.04, "sl_pct": 0.02}

    If mode not provided, default to "atr" if atr provided, otherwise "percent" (requires tp_pct/sl_pct).

    Returns: (tp_price, sl_price)

    Raises:
      ValueError on invalid inputs.
    """
    if params is None:
        params = {}

    if entry_price is None or entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    mode = params.get("mode", None)
    if mode is None:
        mode = "atr" if atr is not None else "percent"

    if mode == "atr":
        if atr is None or atr <= 0:
            raise ValueError("ATR must be provided and > 0 for mode='atr'")
        tp_atr_mul = float(params.get("tp_atr_mul", 2.0))
        sl_atr_mul = float(params.get("sl_atr_mul", 1.5))
        tp = entry_price + tp_atr_mul * float(atr)
        sl = entry_price - sl_atr_mul * float(atr)
        # Ensure SL is positive (price floor)
        if sl <= 0:
            sl = 0.0
        return round(float(tp), 8), round(float(sl), 8)

    elif mode == "percent":
        tp_pct = float(params.get("tp_pct", 0.04))  # 4% default
        sl_pct = float(params.get("sl_pct", 0.02))  # 2% default
        tp = entry_price * (1.0 + tp_pct)
        sl = entry_price * (1.0 - sl_pct)
        if sl <= 0:
            sl = 0.0
        return round(float(tp), 8), round(float(sl), 8)

    else:
        raise ValueError(f"Unknown mode '{mode}' for compute_tp_sl")


def compute_position_size(account_balance: float,
                          entry_price: float,
                          sl_price: float,
                          risk_per_trade: float = 0.01,
                          lot_size: int = 1) -> int:
    """
    Compute number of shares/contracts to buy such that the dollar risk does not exceed
    account_balance * risk_per_trade.

    Formula:
      risk_per_unit = entry_price - sl_price
      max_dollar_risk = account_balance * risk_per_trade
      qty = floor(max_dollar_risk / risk_per_unit)
      rounded down to nearest multiple of lot_size

    Returns integer quantity (0 if cannot afford even 1 lot).

    Raises:
      ValueError for invalid inputs.
    """
    if account_balance is None or account_balance <= 0:
        raise ValueError("account_balance must be > 0")
    if entry_price is None or entry_price <= 0:
        raise ValueError("entry_price must be > 0")
    if sl_price is None or sl_price < 0:
        raise ValueError("sl_price must be >= 0")
    if not (0 < risk_per_trade <= 1.0):
        raise ValueError("risk_per_trade must be in (0,1]")

    risk_per_unit = entry_price - sl_price
    if risk_per_unit <= 0:
        # Can't compute size if SL >= entry (no risk per unit)
        return 0

    max_dollar_risk = account_balance * risk_per_trade
    raw_qty = math.floor(max_dollar_risk / risk_per_unit)
    if raw_qty <= 0:
        return 0

    # round down to nearest multiple of lot_size
    if lot_size <= 1:
        qty = raw_qty
    else:
        qty = (raw_qty // lot_size) * lot_size

    return int(max(0, qty))
