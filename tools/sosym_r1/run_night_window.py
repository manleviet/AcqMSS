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
    ap.add_argument('--probe-first', action='store_true',
                    help="run the probe phases BEFORE the sweep window. Use when the "
                         "probe is what unblocks a decision and the sweep is filler: an "
                         "office window cannot hold a busybox fold anyway, so the "
                         "ordering costs nothing and banks the decision input first.")
    ap.add_argument('--probe-kbs', nargs='+',
                    help="restrict phase 2b to these knowledge bases. Re-running a cell "
                         "that already finished is not free of consequence: the folds "
                         "are skipped via their partials, so it completes in seconds and "
                         "OVERWRITES the recorded wall_s with a meaningless one. Target "
                         "what is missing.")
    ap.add_argument('--probe-caps', nargs='+', type=int,
                    help="restrict phase 2b to these caps, for the same reason.")
    ap.add_argument('--skip-extension', action='store_true',
                    help="skip phase 2a when the extension has already been measured.")
    ap.add_argument('--tail-budget-h', type=float, default=4.0,
                    help="hours the probe phases may spend in total, split between "
                         "2a and 2b. Bounds the half of the night that was unbounded.")
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
    if args.probe_first:
        probe_rc = _probes(args)
        sweep_rc = _sweep(args)
        return sweep_rc or probe_rc
    sweep_rc = _sweep(args)
    return sweep_rc or _probes(args)


def _sweep(args) -> int:
    print("=== phase 1: busybox rs_1n, reserved ===", flush=True)
    # --reserve rather than --only: if rs_1n is already done on a later night, the
    # budget still goes to whatever else is pending instead of the window idling.
    rc = subprocess.run(
        [sys.executable, '-u', str(TOOLS / 'sweep_queue.py'), 'run',
         '--budget', args.budget, '--reserve', 'busybox-1.18.0_rs_1n'],
        cwd=REPO).returncode
    print(f"=== phase 1 exit {rc} ===", flush=True)
    return rc


def _probes(args) -> int:
    if args.skip_probe:
        return 0

    # The window's own lock is released by now, so nothing here can collide with it.
    #
    # The question the probe answers has INVERTED since the fix. Before, it asked
    # whether a larger budget bought anything — the answer was no, because the run was
    # spinning. Post-fix the runs are still producing novel queries at ~4,990 of 5,000,
    # so the cap may now bind for an honest reason, and the question is where learning
    # actually stops. That cannot be answered from a grid bounded at 5,000: bounding it
    # there would report "still learning at the ceiling" and call it a result.
    #
    # So the extension runs FIRST, on the cheapest mid-size KB. The grid is the
    # familiar shape but it is now the secondary question, and if the tail is cut short
    # the extension is the half worth having.
    # The tail gets an explicit budget. Phase 1 is bounded and phase 2 was not, so a
    # 13 h night ran 13 h 40 m and was still probing at breakfast. The probe now stops
    # STARTING cells once its share is spent; a cell already running finishes, because
    # killing it mid-cell would discard the whole cell for nothing.
    tail_h = max(0.5, float(args.tail_budget_h))
    if args.skip_extension:
        print("\n=== phase 2a: skipped (already measured) ===", flush=True)
        ext_rc = 0
    else:
        print(f"\n=== phase 2a: where does learning stop? (fqa, past 5000) "
              f"[tail budget {tail_h} h] ===", flush=True)
        ext_rc = subprocess.run(
            [sys.executable, '-u', str(TOOLS / 'probe_query_budget.py'),
             '--out', args.probe_out + '_extended', '--kbs', 'fqa',
             '--modes', 'example_first',
             '--caps', '1000', '5000', '10000', '20000',
             '--budget-h', str(tail_h / 2)],
            cwd=REPO).returncode
        print(f"=== phase 2a exit {ext_rc} ===", flush=True)

    print("\n=== phase 2b: the standard grid, post-fix ===", flush=True)
    probe_rc = subprocess.run(
        [sys.executable, '-u', str(TOOLS / 'probe_query_budget.py'),
         '--out', args.probe_out,
         '--kbs', *(args.probe_kbs or ['arcade-game', 'REAL-FM-4']),
         '--modes', 'example_first',
         '--caps', *[str(c) for c in (args.probe_caps or [250, 500, 1000, 2000, 5000])],
         '--budget-h', str(tail_h if args.skip_extension else tail_h / 2)],
        cwd=REPO).returncode
    print(f"=== phase 2b exit {probe_rc} ===", flush=True)
    return ext_rc or probe_rc


if __name__ == '__main__':
    sys.exit(main())
