"""Pre-merge freshness gate for the ConMin sweep.

WHY THIS EXISTS
---------------
Two earlier versions of this check were wrong in the same way — they checked a
PROXY instead of the property:

  v1 (CW Impl):  [ rs_1n_eval.json -nt ff_eval.json ]      # mtime
      A run that writes the file early and dies before filling the QuAcq-active
      block gives a NEWER file that is still stale. The gate says OK.

  v2 (CW Main):  grep -q 'convergence_reason' *_eval.json  # key presence
      `is_stale` rejects on a blank VALUE, not a missing KEY. A row carrying
      "convergence_reason": "" passes this grep and fails the real gate.
      `grep -q '"QuAcq-active"'` likewise passes on ONE occurrence, so a partial
      write with a single fold slips through.

Both were also a re-implementation of a predicate that already exists in the
codebase — and re-implementing a predicate in a second language is precisely the
drift that produced the FIX-4 defect.

So this script does not re-implement the predicate: it replicates the merge's
union + blank-fill (run_conmin_eval.py:83-99) and then calls the PRODUCTION
predicate `apps.make_tables.gates.is_stale` on the rows it will actually judge.

RESIDUAL DRIFT — READ BEFORE TRUSTING THIS SCRIPT
-------------------------------------------------
Calling `is_stale` closes the PREDICATE drift. It does NOT close the
ROW-CONSTRUCTION drift: the union + blank-fill above is a COPY of
`_merge_per_kb`'s logic, which is not factored out of that function. If that
blank-fill changes, this gate silently starts judging rows the merge would
never produce.

That residual is load-bearing, not theoretical. Measured 2026-07-27: run
`is_stale` on the RAW JSON rows, without the blank-fill, and it reports
**all five KBs stale** — four false positives — because `gates.is_stale` tests
`rows[0]` for counter columns and `rows[0]` is a condition-A row, which carries
no counters until the union fills them in. So the copy does not degrade
gracefully; drop it and the verdict inverts.

Therefore, the division of labour, stated so neither check is mistaken for the
other:

  * `make_tables`'s own `is_stale`, run on the REAL merged rows, is the
    AUTHORITATIVE check.
  * `freshness_gate.py` is an EARLY WARNING. It trades exactness for running
    before the CSV is written — which matters because `--merge` is silent about
    exactly this failure (`convergence_reason` and all five counters are listed
    ADDITIVE at run_conmin_eval.py:86-88, so the stale-mix warning at :90-95
    never fires and the rows blank-fill to None without comment).

Two checks with different jobs. Post-deadline: extract run_conmin_eval.py:83-99
into a function both call, and this residual disappears.

USAGE
-----
    cd <AcqMSS repo root>
    PYTHONPATH=. python3 freshness_gate.py     # exit 0 = safe to --merge, 1 = blocked

Run it BEFORE `--merge` and BEFORE `make_tables --official`.
"""
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from apps.make_tables import COUNTER_COLS, QUACQ_CONDITIONS   # noqa: E402
from apps.make_tables.gates import is_stale                    # noqa: E402

RESULTS_DIR = "data/results_conmin"


def main() -> int:
    kbs: dict = {}
    for path in sorted(glob.glob(f"{RESULTS_DIR}/*_eval.json")):
        payload = json.load(open(path))
        kbs.setdefault(payload["kb"], []).append((os.path.basename(path), payload.get("rows", [])))

    if not kbs:
        print(f"NO *_eval.json under {RESULTS_DIR} — did the sweep run?")
        return 1

    blocked = 0
    for kb, files in sorted(kbs.items()):
        # Replicate the merge (run_conmin_eval.py:83-99) so is_stale sees the rows it will judge.
        scored = [r for _, rows in files for r in rows
                  if "error" not in r and "gate_tripped" not in r]
        keys = list(dict.fromkeys(k for r in scored for k in r.keys()))
        merged = [{k: r.get(k, None) for k in keys} for r in scored]

        verdict = is_stale(kb, merged)
        blocked += verdict
        print(f"\n{kb}: {'STALE -> would blank the WHOLE KB' if verdict else 'OK'}")

        for name, rows in files:
            conditions = {r.get("condition") for r in rows}
            has_active = "QuAcq-active" in conditions
            blanks = sum(1 for r in rows
                         if r.get("condition") in QUACQ_CONDITIONS
                         and not (r.get("convergence_reason") or "").strip())
            counters = any(c in (rows[0] if rows else {}) for c in COUNTER_COLS)
            culprit = "  <== culprit" if (blanks or not has_active) else ""
            print(f"   {name:42s} QuAcq-active={has_active!s:5s} "
                  f"blank-reason-rows={blanks:2d} counters_on_row0={counters!s:5s}{culprit}")

    print("\n" + ("BLOCKED — do not --merge or --official." if blocked else "All KBs fresh."))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
