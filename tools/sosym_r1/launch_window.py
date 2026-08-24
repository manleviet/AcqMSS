#!/usr/bin/env python
"""Start a sweep window detached from the shell that launched it.

Two failures made this necessary, both on 2026-08-22: a probe was killed at 59
minutes by a SIGTERM nothing explained, and an analysis job launched normally died
at ~11 minutes while a detached one survived three hours. A window that dies
mid-unit loses that unit's work, so the window gets its own session and the
machine is held awake for the duration.

    launch_window.py --budget 6h
    launch_window.py --budget 5.5h --log data/results_sosym/window-work.log

Prints the pid and the log path, then returns. Progress is in the ledger, which is
rewritten atomically after every unit, so `sweep_queue.py status` works while the
window runs.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--budget', required=True, help="window budget, e.g. 6h")
    parser.add_argument('--log', help="log path (default: data/results_sosym/window-<utc>.log)")
    parser.add_argument('--max-queries', type=int, default=5000)
    parser.add_argument('--only',
                        help="forwarded to sweep_queue: run only units whose id contains "
                             "this substring. Without it the window works the whole "
                             "cheapest-first queue, which is rarely what you want when "
                             "you launched it to get one specific measurement.")
    parser.add_argument('--stop-on-failure', action='store_true',
                        help="forwarded to sweep_queue: stop the window on the first "
                             "failed unit instead of continuing.")
    parser.add_argument('--no-caffeinate', action='store_true',
                        help="do not hold the machine awake (use when on battery)")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log_path = Path(args.log) if args.log else REPO / 'data' / 'results_sosym' / f'window-{stamp}.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)

    inner = [sys.executable, '-u',  # -u: the log is the only view into a detached run
             str(REPO / 'tools' / 'sosym_r1' / 'sweep_queue.py'),
             'run', '--budget', args.budget, '--max-queries', str(args.max_queries)]
    if args.only:
        inner += ['--only', args.only]
    if args.stop_on_failure:
        inner += ['--stop-on-failure']

    # caffeinate holds the display, disk, system and user-idle timers. Without it a
    # home window ends when the machine sleeps rather than when the budget runs out.
    if not args.no_caffeinate and shutil.which('caffeinate'):
        inner = ['caffeinate', '-dimsu'] + inner
    elif not args.no_caffeinate:
        print("warning: caffeinate not found; the machine may sleep mid-window",
              file=sys.stderr)

    with open(log_path, 'ab') as log:
        proc = subprocess.Popen(
            inner, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'})

    print(f"window pid {proc.pid}, budget {args.budget}")
    print(f"log  {log_path}")
    print(f"watch: python tools/sosym_r1/sweep_queue.py status")
    return 0


if __name__ == '__main__':
    sys.exit(main())
