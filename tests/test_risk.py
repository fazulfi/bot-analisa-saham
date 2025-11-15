# tests/test_risk.py
import pytest
from bot_analisa.risk.risk import compute_tp_sl, compute_position_size

def test_compute_tp_sl_atr_mode():
    entry = 100.0
    atr = 2.0
    tp, sl = compute_tp_sl(entry, atr=atr, params={"mode":"atr", "tp_atr_mul":2.0, "sl_atr_mul":1.5})
    assert tp == 100.0 + 2.0 * 2.0
    assert sl == 100.0 - 1.5 * 2.0

def test_compute_tp_sl_percent_mode():
    entry = 200.0
    tp, sl = compute_tp_sl(entry, atr=None, params={"mode":"percent", "tp_pct":0.05, "sl_pct":0.02})
    assert pytest.approx(tp, rel=1e-9) == 200.0 * 1.05
    assert pytest.approx(sl, rel=1e-9) == 200.0 * 0.98

def test_compute_tp_sl_default_atr_prefers_atr():
    # if atr provided and no mode param, defaults to atr
    entry = 50.0
    atr = 1.0
    tp, sl = compute_tp_sl(entry, atr=atr, params={})
    assert tp == 50.0 + 2.0 * 1.0
    assert sl == 50.0 - 1.5 * 1.0

def test_compute_position_size_basic():
    # account 10k, risk 1% = $100, entry 100, sl 95 => risk/unit = 5 => qty = floor(100/5)=20
    qty = compute_position_size(10000.0, entry_price=100.0, sl_price=95.0, risk_per_trade=0.01, lot_size=1)
    assert qty == 20

def test_compute_position_size_lot_rounding():
    # same but lot_size 10 -> qty must be multiple of 10 -> floor(20/10)=2 -> qty=20
    qty = compute_position_size(10000.0, entry_price=100.0, sl_price=95.0, risk_per_trade=0.01, lot_size=10)
    assert qty == 20

def test_compute_position_size_cannot_afford():
    qty = compute_position_size(1000.0, entry_price=100.0, sl_price=99.5, risk_per_trade=0.01, lot_size=1)
    # risk per unit = 0.5, max risk = 10 => qty = floor(10/0.5) = 20
    assert qty == 20

def test_invalid_inputs():
    with pytest.raises(ValueError):
        compute_tp_sl(0.0, atr=1.0, params={"mode":"atr"})
    with pytest.raises(ValueError):
        compute_position_size(0.0, 100.0, 90.0)
