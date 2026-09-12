"""Modal credit watch — polls billing report, warns when est. balance < $15.

Usage:
    START_BALANCE=30.00 python scripts/modal_credit_watch.py
    # or: python scripts/modal_credit_watch.py --balance 30.00

Polls `modal billing report --for today --json` every POLL_SECS (default 300).
Remaining = START_BALANCE - (today_spend + PRIOR_SPEND). Prints a line each
poll; prints a loud WARNING when est. remaining <= WARN_AT ($15 default).

NOTE: billing report only covers "today" — if you've already spent on prior
days, pass --prior-spend so remaining is accurate. Check the dashboard for the
authoritative number; this is a tripwire, not an audit.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone


def today_spend() -> float:
    out = subprocess.run(
        ["modal", "billing", "report", "--for", "today", "--json"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print("billing report failed:", out.stderr.strip()[:200])
        return None
    try:
        rows = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return None
    return sum(float(r.get("Cost", 0) or 0) for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance", type=float,
                    default=float(__import__("os").environ.get("START_BALANCE", 30.0)))
    ap.add_argument("--prior-spend", type=float, default=0.0,
                    help="Spend before today not covered by 'today' report")
    ap.add_argument("--warn-at", type=float, default=15.0)
    ap.add_argument("--poll", type=int, default=300)
    args = ap.parse_args()

    print(f"watching: start_balance=${args.balance:.2f} prior_spend=${args.prior_spend:.2f} "
          f"warn_at=${args.warn_at:.2f} poll={args.poll}s")
    while True:
        spend = today_spend()
        ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
        if spend is None:
            print(f"[{ts}] report unavailable")
        else:
            remaining = args.balance - args.prior_spend - spend
            line = f"[{ts}] today spend ${spend:.4f} | est. remaining ${remaining:.2f}"
            if remaining <= args.warn_at:
                print("\n" + "!" * 60)
                print(f"CREDIT WARNING: est. remaining ${remaining:.2f} <= ${args.warn_at:.2f}")
                print("Stop running apps or top up — modal app list / modal app stop <id>")
                print("!" * 60 + "\n")
            else:
                print(line, flush=True)
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
