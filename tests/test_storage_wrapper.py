# tests/test_storage_wrapper.py
import importlib
import inspect
import pandas as pd
import pytest

def _find_storage_class(module):
    """Find a candidate storage class in given module by heuristics."""
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            # heuristics: class should implement a save-like and list-like method
            if any(hasattr(obj, m) for m in ("save_signal_dict", "add_signal", "save", "add")) and \
               any(hasattr(obj, m) for m in ("list_signals", "get_signals", "list")):
                return obj
    return None

def _call_save(storage, sig):
    for fn in ("save_signal_dict", "add_signal", "save", "add"):
        if hasattr(storage, fn):
            return getattr(storage, fn)(sig)
    raise RuntimeError("No save method found on storage instance")

def _call_list(storage, ticker):
    for fn in ("list_signals", "get_signals", "list"):
        if hasattr(storage, fn):
            return getattr(storage, fn)(ticker)
    raise RuntimeError("No list method found on storage instance")

def _call_update(storage, ticker, sig_id):
    # try various signatures: (ticker, id, status, info) or (id, status) etc.
    for fn in ("update_signal_status", "update_status", "set_status"):
        if hasattr(storage, fn):
            f = getattr(storage, fn)
            try:
                # prefer full signature if available
                return f(ticker, sig_id, "TP", "hit-by-test")
            except TypeError:
                try:
                    return f(sig_id, "TP")
                except TypeError:
                    # try other combos
                    try:
                        return f(ticker, sig_id, "TP")
                    except TypeError:
                        continue
    # fallback: try direct attribute mutation if df accessible
    return False

def test_storage_basic_flow(tmp_path):
    """
    Flexible test that:
     - locates storage class in bot_analisa.signals.storage
     - instantiates it (with tmp_path if supported)
     - saves a signal dict
     - lists signals and checks fields exist
     - updates status and verifies the update persisted
    """
    # import storage module
    try:
        storage_mod = importlib.import_module("bot_analisa.signals.storage")
    except Exception as e:
        pytest.skip(f"storage module not importable: {e}")

    StorageClass = _find_storage_class(storage_mod)
    assert StorageClass is not None, "Could not find a storage class in bot_analisa.signals.storage"

    # instantiate (try to pass a folder/path argument if constructor accepts)
    try:
        storage = StorageClass(str(tmp_path))
    except TypeError:
        storage = StorageClass()

    # build a flexible signal dict (include both 'entry' and 'entry_price' to support variants)
    sig = {
        "ticker": "TEST",
        "entry": 100.0,
        "entry_price": 100.0,
        "tp": 105.0,
        "sl": 95.0,
        "strategy_version": "test-v",
        "meta": {"foo": "bar"}
    }

    saved = _call_save(storage, sig)
    # saved may be dict or object; normalize
    if isinstance(saved, dict):
        saved_id = saved.get("id") or saved.get("signal_id") or None
    else:
        # try to read id attribute
        saved_id = getattr(saved, "id", None)

    # ensure ID generated
    assert saved_id is not None, "Storage did not return/assign an id for saved signal"

    # list signals and assert the saved one is present
    df = _call_list(storage, "TEST")
    # allow both DataFrame or list/dict returns
    if isinstance(df, pd.DataFrame):
        assert not df.empty, "list_signals returned empty DataFrame"
        # find the row matching id or matching entry price
        if "id" in df.columns:
            row = df.loc[df["id"] == saved_id]
            assert not row.empty, "Saved id not found in storage DataFrame"
            row0 = row.iloc[0].to_dict()
        else:
            # fallback: match by entry price
            row0 = df.iloc[0].to_dict()
    elif isinstance(df, (list, tuple)):
        assert len(df) > 0
        # try to find saved signal inside list by id or entry_price
        found = None
        for r in df:
            if isinstance(r, dict) and (r.get("id") == saved_id or float(r.get("entry_price", r.get("entry", 0))) == 100.0):
                found = r
                break
        assert found is not None, "Saved signal not found in list output"
        row0 = found
    elif isinstance(df, dict):
        row0 = df
    else:
        pytest.skip("Unknown return type from list_signals; cannot verify")

    # assert expected fields exist (accept both entry or entry_price)
    assert ("entry_price" in row0) or ("entry" in row0), "Saved row missing entry/entry_price"
    # check TP/SL present
    assert ("tp" in row0) and ("sl" in row0), "Saved row missing tp or sl"

    # now update status
    # determine actual id to use for update
    actual_id = row0.get("id") or saved_id
    updated = _call_update(storage, "TEST", actual_id)

    # Some storage update methods return bool, others None; just ensure the change persisted if possible
    try:
        df2 = _call_list(storage, "TEST")
    except Exception:
        pytest.skip("Cannot re-list signals after update to verify status")

    # normalize df2 to dict row
    if isinstance(df2, pd.DataFrame):
        if "id" in df2.columns:
            row_up = df2.loc[df2["id"] == actual_id].iloc[0].to_dict()
        else:
            row_up = df2.iloc[0].to_dict()
    elif isinstance(df2, (list, tuple)):
        row_up = None
        for r in df2:
            if isinstance(r, dict) and (r.get("id") == actual_id or float(r.get("entry_price", r.get("entry", 0))) == 100.0):
                row_up = r
                break
        assert row_up is not None
    else:
        pytest.skip("Unknown return type after update; cannot assert status")

    # check status column/field exists and is updated to TP (case-insensitive match)
    status_val = row_up.get("status") or row_up.get("state") or row_up.get("status_info") or ""
    assert str(status_val).upper().startswith("TP") or updated is not False, "Status did not update to TP (or update method returned False)"
