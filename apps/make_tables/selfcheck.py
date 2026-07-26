"""Self-checks (v1 Self-checks + v2 G4): anchors, row counts, raw==reduced equality.

Anchors are the exclude-2COV CV mean (the table cell), compared as PRE-ROUND floats with
tolerance 5e-3 — never string-compared. A drift means the INPUT changed, not the anchor:
FAIL loudly, never "fix the anchor to match output". RE7/fqa/arcade are FINAL (CW-Impl
2026-07-26); REAL-FM-4 + busybox QuAcq-active finalize after the overnight re-run and are
intentionally NOT pinned here (see PENDING_QUACQ_ACTIVE) — no temporary numbers.
"""
from __future__ import annotations

import logging

from .aggregate import cv_mean
from .filters import select

logger = logging.getLogger(__name__)

TOL = 5e-3
EXPECTED_ROWS_EXCL2COV = 15   # 5 samplings x 3 folds per (KB, strategy) with the pinned filter

# (kb, strategy, column, expected) — exclude-2COV CV mean; ABORT-level regression guards.
ANCHORS = [
    # Stage-1 sem-F1 — --conditions quacq-active does NOT touch A/C/C-union-S, so all 4 KB are final.
    ("REAL-FM-7", "C∪S", "sem_f1", 0.847), ("fqa", "C∪S", "sem_f1", 0.782),
    ("arcade-game", "C∪S", "sem_f1", 0.637), ("REAL-FM-4", "C∪S", "sem_f1", 0.776),
    ("REAL-FM-7", "A", "sem_f1", 0.605), ("fqa", "A", "sem_f1", 0.867),
    ("arcade-game", "A", "sem_f1", 0.380), ("REAL-FM-4", "A", "sem_f1", 0.642),
    ("REAL-FM-7", "C∪S", "desc_f1", 0.682),                    # desc headline (ruling b)
    # QuAcq example-only sem-F1 — RE7/fqa/arcade final (pool_exhausted, deterministic).
    ("REAL-FM-7", "QuAcq", "sem_f1", 0.012), ("fqa", "QuAcq", "sem_f1", 0.021),
    ("arcade-game", "QuAcq", "sem_f1", 0.022),
    # QuAcq-active — RE7/fqa/arcade final (fqa/arcade cap at max_queries; still a stable value).
    ("REAL-FM-7", "QuAcq-active", "sem_f1", 0.842), ("REAL-FM-7", "QuAcq-active", "desc_f1", 0.240),
    ("REAL-FM-7", "QuAcq-active", "n_kb", 12.0), ("REAL-FM-7", "QuAcq-active", "oracle_queries", 272.0),
    ("fqa", "QuAcq-active", "sem_f1", 0.062), ("fqa", "QuAcq-active", "desc_f1", 0.056),
    ("arcade-game", "QuAcq-active", "sem_f1", 0.452), ("arcade-game", "QuAcq-active", "desc_f1", 0.495),
]

# REAL-FM-4 QuAcq-active ends on a WALL-CLOCK timeout, so it is NON-DETERMINISTIC (679 queries
# at 400 s, 3220 at 7200 s) and can NEVER be a deterministic anchor — it deliberately has no
# numeric anchor here. (Its Stage-1 A/C/C∪S anchors are unaffected — the sweep doesn't touch them.)
NON_ANCHORABLE_QUACQ_ACTIVE = ("REAL-FM-4",)
# busybox QuAcq-active is PENDING tonight's run (max_queries=5000 is the effective, deterministic cap).
PENDING_QUACQ_ACTIVE = ("busybox-1.18.0",)


def check_anchors(data: dict):
    """Return (passed, failures, skipped). A cell that is EMPTY on a LOADED KB is a FAILURE
    (broken metric), not a skip — only a KB absent/out-of-scope legitimately skips."""
    passed, failures, skipped = 0, [], 0
    for kb, strat, col, exp in ANCHORS:
        rows = data.get(kb)
        tag = f"{kb}/{strat}/{col}"
        if not rows:                                   # KB absent / out of scope -> legit skip
            logger.info("anchor skip (KB not loaded): %s", tag)
            skipped += 1
            continue
        got = cv_mean(select(rows, strat), col).value
        if got is None:                                # KB loaded but cell empty -> BROKEN
            failures.append((tag, exp, None))
            logger.error("anchor BROKEN (empty cell on loaded KB %s): %s (expected %.3f)",
                         kb, tag, exp)
        elif abs(got - exp) < TOL:
            passed += 1
        else:
            failures.append((tag, exp, got))
            logger.error("anchor DRIFT: %s expected %.4f got %.4f — INPUT changed, do NOT re-fit",
                         tag, exp, got)
    return passed, failures, skipped


def check_rowcounts(data: dict):
    """Per (KB, strategy) exclude-2COV count should be 15; warn if a fresh KB is short."""
    short = []
    for kb, rows in data.items():
        if not rows or kb == "busybox-1.18.0":           # busybox is intentionally partial
            continue
        for strat in ("A", "C", "C∪S", "QuAcq", "QuAcq-active"):
            n = len(select(rows, strat))
            if n and n != EXPECTED_ROWS_EXCL2COV:
                short.append((kb, strat, n))
                logger.warning("row-count short: %s/%s = %d (expected %d)",
                               kb, strat, n, EXPECTED_ROWS_EXCL2COV)
    return short


def check_rawred(data: dict):
    """app-rawred: C-union-S(k=1) raw vs reduced must agree on sem_f1/accuracy/n_kb."""
    mismatches = []
    for kb, rows in data.items():
        if not rows:
            continue
        for col in ("sem_f1", "accuracy", "n_kb"):
            raw = cv_mean(select(rows, "C∪S", negatives="raw"), col).value
            red = cv_mean(select(rows, "C∪S", negatives="reduced"), col).value
            if raw is not None and red is not None and abs(raw - red) > TOL:
                mismatches.append((kb, col, raw, red))
                logger.warning("raw != reduced: %s/%s raw=%.4f reduced=%.4f", kb, col, raw, red)
    return mismatches


def run_all(data: dict):
    """Run every self-check. Returns (ok, skipped): ok=True means safe to publish (no anchor
    drift/broken cell AND no short-loaded KB). A short fresh KB gates emission (never emit a
    partial mean as final)."""
    passed, failures, skipped = check_anchors(data)
    short = check_rowcounts(data)
    check_rawred(data)
    ok = (not failures) and (not short)
    logger.info("self-check: %d passed, %d failed, %d skipped, %d short-KB -> %s",
                passed, len(failures), skipped, len(short), "OK" if ok else "BLOCK")
    logger.info("QuAcq-active NON-ANCHORABLE (wall-clock timeout, non-deterministic): %s; "
                "PENDING tonight's run: %s",
                ", ".join(NON_ANCHORABLE_QUACQ_ACTIVE), ", ".join(PENDING_QUACQ_ACTIVE))
    return ok, skipped
