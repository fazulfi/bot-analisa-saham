#!/usr/bin/env python3
"""
Run notifier: fetch open signals, send via telegram, mark notified.
Usage:
  python scripts/run_notify.py           # run once
  python scripts/run_notify.py --loop --sleep 60   # loop every 60s
"""
import time
import argparse
from bot_analisa.notify import telegram, storage_adapter

def process_once(test_mode=False):
    signals = storage_adapter.list_open_unnotified_signals()
    results = []
    for s in signals:
        res = telegram.send_signal(s, test_mode=test_mode)
        results.append((s.get("id"), res))
        if res.get("ok"):
            storage_adapter.update_signal_notified(s.get("id"))
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--loop", action="store_true", help="loop mode")
    p.add_argument("--sleep", type=int, default=60, help="sleep seconds between runs")
    p.add_argument("--test", action="store_true", help="test mode: do not call network")
    args = p.parse_args()

    if args.loop:
        print("Starting loop mode (sleep={}s)".format(args.sleep))
        try:
            while True:
                r = process_once(test_mode=args.test)
                print("Processed {} signals".format(len(r)))
                time.sleep(args.sleep)
        except KeyboardInterrupt:
            print("stopped by user")
    else:
        r = process_once(test_mode=args.test)
        print("Processed {} signals".format(len(r)))
        for sid, res in r:
            print(sid, res)

if __name__ == "__main__":
    main()
