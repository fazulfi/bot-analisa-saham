import json
from bot_analisa.notify import storage_adapter, telegram
import os

def test_run_notify_once(monkeypatch, tmp_path):
    # make a temporary state file
    fp = tmp_path / "state.json"
    initial = [
        {"id":"S-1", "ticker":"PGAS.JK", "entry":1000, "status":"OPEN"},
        {"id":"S-2", "ticker":"BBCA.JK", "entry":5000, "status":"OPEN"},
    ]
    fp.write_text(json.dumps(initial))

    # point adapter to tmp file
    monkeypatch.setenv("NOTIFY_STATE_FILE", str(fp))
    # import reload adapter so FILE_PATH is updated (in case)
    import importlib
    importlib.reload(storage_adapter)

    called = []
    def fake_send(signal, test_mode=False):
        called.append(signal.get("id"))
        return {"ok": True, "mock": True}
    monkeypatch.setattr(telegram, "send_signal", fake_send)

    # run processing
    from bot_analisa.notify import storage_adapter as sa
    signals = sa.list_open_unnotified_signals()
    assert len(signals) == 2

    # emulate runner: call for each and mark
    for s in signals:
        res = telegram.send_signal(s, test_mode=True)
        assert res["ok"]
        sa.update_signal_notified(s["id"])

    # ensure send called twice
    assert called == ["S-1","S-2"]
    # ensure file updated
    all_data = json.loads(fp.read_text())
    assert all((item.get("notified") for item in all_data))
