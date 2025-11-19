"""
Simple Telegram notifier using stdlib only (urllib).
Expects TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars to be set.
Function: send_signal(signal: dict) -> dict (response or error)
"""
from urllib import request, parse, error
import os
import json
import logging

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID")

def build_message(signal: dict) -> str:
    # customize message format here
    lines = []
    lines.append("📣 *SIGNAL — {} {}*".format(signal.get("side","").upper(), signal.get("ticker","")))
    lines.append("• entry: {}".format(signal.get("entry","")))
    if "tp" in signal:
        lines.append("• tp: {}".format(signal.get("tp","")))
    if "sl" in signal:
        lines.append("• sl: {}".format(signal.get("sl","")))
    if "time" in signal:
        lines.append("• time: {}".format(signal.get("time","")))
    if "id" in signal:
        lines.append("• id: {}".format(signal.get("id","")))
    return "\n".join(lines)

def send_signal(signal: dict, test_mode: bool=False) -> dict:
    """
    Send a Telegram message for given signal.
    If test_mode=True, return constructed payload without sending.
    """
    text = build_message(signal)
    payload = {
        "chat_id": TELEGRAM_CHAT,
        "text": text,
        "parse_mode": "Markdown"
    }
    if test_mode:
        return {"ok": True, "mock": True, "payload": payload}

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        msg = "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables"
        logger.error(msg)
        return {"ok": False, "error": msg}

    url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_TOKEN)
    data = parse.urlencode(payload).encode()
    req = request.Request(url, data=data, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
            return {"ok": True, "response": parsed}
    except error.HTTPError as e:
        body = e.read().decode() if hasattr(e, 'read') else ""
        logger.exception("http error sending telegram")
        return {"ok": False, "error": str(e), "body": body}
    except Exception as e:
        logger.exception("error sending telegram")
        return {"ok": False, "error": str(e)}
