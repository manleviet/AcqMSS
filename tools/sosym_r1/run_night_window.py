#!/usr/bin/env python
"""Tonight's window: one busybox rs_1n fold, then the post-patch cap re-probe.

An 11 h night window holds exactly one busybox rs_1n fold (8.57 h charged against a
4.76 h projected actual), leaving roughly 6 h that fits no second fold. The obvious
backfill — QuAcq units — is not usable yet: the query cap is unsettled pending the
post-patch re-probe, so any QuAcq unit run tonight would have to be run again.

So the tail runs the re-probe itself. It is the work that unblocks the cap decision,
it is CPU-bound, and it costs nothing if it is interrupted because it writes results
incrementally per cell.

The two phases run in SEQUENCE, never together: the fold is a paper number and a
second job on another core would contend with the wall-clock it is measuring.

    run_night_window.py                 # the whole night, detached by the launcher
    run_night_window.py --skip-probe    # fold only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / 'tools' / 'sosym_r1'
sys.path.insert(0, str(TOOLS))
from sweep_queue import acquire_window_lock  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--budget', default='11h')
    ap.add_argument('--skip-probe', action='store_true')
    ap.add_argument('--probe-out', default=str(REPO / 'data' / 'results_sosym' / 'cap_probe_postfix'))
    args = ap.parse_args()

    # The night needs its OWN lock, not just the window's. Phase 1 respects the
    # window lock and exits cleanly if another window holds it — but this script would
    # then fall straight through to phase 2 and start the probe alongside the fold that
    # is still running, which is the contention the sequencing exists to prevent. A
    # manual launch and a belt-and-braces scheduled launch make that a live case.
    night_lock = acquire_window_lock(REPO / 'data' / 'results_sosym' / 'night')
    if night_lock is None:
        print("another night sequence is already running — exiting cleanly", flush=True)
        return 0
    try:
        return _run(args)
    finally:
        night_lock.unlink(missing_ok=True)


def _run(args) -> int:
    print("=== phase 1: busybox rs_1n, reserved ===", flush=True)
    # --reserve rather than --only: if rs_1n is already done on a later night, the
    # budget still goes to whatever else is pending instead of the window idling.
    rc = subprocess.run(
        [sys.executable, '-u', str(TOOLS / 'sweep_queue.py'), 'run',
         '--budget', args.budget, '--reserve', 'busybox-1.18.0_rs_1n'],
        cwd=REPO).returncode
    print(f"=== phase 1 exit {rc} ===", flush=True)

    if args.skip_probe:
        return rc

    # The window's own lock is released by now, so nothing here can collide with it.
    print("\n=== phase 2: post-patch cap re-probe (tail) ===", flush=True)
    probe_rc = subprocess.run(
        [sys.executable, '-u', str(TOOLS / 'probe_query_budget.py'),
         '--out', args.probe_out,
         '--kbs', 'fqa', 'arcade-game', 'REAL-FM-4',
         '--modes', 'example_first',
         '--caps', '250', '500', '1000', '2000', '5000'],
        cwd=REPO).returncode
    print(f"=== phase 2 exit {probe_rc} ===", flush=True)
    return rc or probe_rc


if __name__ == '__main__':
    sys.exit(main())
