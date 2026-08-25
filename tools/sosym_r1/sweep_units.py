"""The SoSyM revision sweep, enumerated one fold at a time.

An atomic unit is a single fold of a single (kb, sampling, algorithm) cell, run in
its own process. Fold granularity is what lets a window close without losing work
(``conacq.eval.cv_partials``). One *process* per fold is a separate requirement:
``memory_peak_mb`` is a tracemalloc peak that depends on where the fold sits in
its process — measured on REAL-FM-7 rs_1n, a fold running first in a fresh process
reports ~20 % more than the same fold running second in a warm one. Since the
large KBs must split across windows and the small ones need not, batching folds
would make the reported memory a function of the scheduling rather than of the
knowledge base.

Estimates are per fold, and every one of them is a FLOOR: they are derived from
``data/results_conmin/*_long.csv`` condition A, which is AcqMss alone, whereas
ConGen is AcqMss plus Reduce. Step 2 measures the real ratio and writes it into
the ledger as a multiplier; until then the runner's safety factor is doing all the
work. Do not treat any number here as a prediction.
"""

from __future__ import annotations

from typing import Dict, List, Optional

N_FOLDS = 3
SOLVER_MODE = 'incremental'

# (kb directory stem, short name used in the estimate table)
KBS: Dict[str, str] = {
    'REAL-FM-7': 'REAL-FM-7',
    'fqa': 'fqa',
    'arcade-game': 'arcade',
    'REAL-FM-4': 'REAL-FM-4',
    'busybox-1.18.0': 'busybox',
}

# Per-fold hours, condition A (AcqMss only), read off
# ``data/results_conmin/*_long.csv`` as mean(total_ms)/3.6e6 over the three folds.
# These are the measured reference values, not rounded bounds: rounding them up
# made the cheap cells look ~50x more expensive than they are, which reads as a
# calibration signal when it is only the rounding. None = never measured.
ESTIMATES: Dict[str, Dict[str, Optional[float]]] = {
    'REAL-FM-7': {'2cov': 0.0000, 'rs_m': 0.0001, 'rs_1n': 0.0002,
                  'rs_2n': 0.0005, 'rs_3n': 0.0007, 'ff': 0.0001},
    'fqa': {'2cov': 0.0000, 'rs_m': 0.0002, 'rs_1n': 0.0037,
            'rs_2n': 0.0126, 'rs_3n': 0.0212, 'ff': 0.0010},
    'arcade': {'2cov': 0.0009, 'rs_m': 0.0041, 'rs_1n': 0.0253,
               'rs_2n': 0.0677, 'rs_3n': 0.1340, 'ff': 0.0067},
    'REAL-FM-4': {'2cov': 0.0014, 'rs_m': 0.0106, 'ff': 0.0906,
                  'rs_1n': 0.4801, 'rs_2n': 1.7737, 'rs_3n': 4.1739},
    # busybox rs_2n / rs_3n are bounded, not completed: measured superlinear scaling
    # on REAL-FM-4 puts them at 317 h and 745 h for three folds. Absent by decision.
    #
    # busybox rs_m has examples and folds on disk but no condition-A reference: it is
    # the one sampling that has never been run. It carries a NOMINAL 0.2 h/fold --
    # ~18x REAL-FM-4's measured rs_m (0.0106) and charged at the default 1.0x, so
    # 0.30 h against a window. The figure is a placeholder chosen to be schedulable
    # and conservative, NOT a measurement; the queue records the actual on first run.
    # It is not left at None because a unit with no estimate is never picked, and a
    # table cell that quietly never runs is found at the worst possible moment.
    'busybox': {'2cov': 0.0000, 'rs_m': 0.2000, 'ff': 3.7923, 'rs_1n': 28.5637},
}

# Cheapest first, so partial results accrue on the small KBs before the long tail.
ORDER: List[tuple] = [
    ('REAL-FM-7', s) for s in ('2cov', 'rs_m', 'rs_1n', 'rs_2n', 'rs_3n', 'ff')
] + [
    ('fqa', s) for s in ('2cov', 'rs_m', 'rs_1n', 'rs_2n', 'rs_3n', 'ff')
] + [
    ('arcade', s) for s in ('2cov', 'rs_m', 'rs_1n', 'rs_2n', 'rs_3n', 'ff')
] + [
    ('REAL-FM-4', s) for s in ('2cov', 'rs_m', 'ff', 'rs_1n', 'rs_2n', 'rs_3n')
] + [
    ('busybox', s) for s in ('2cov', 'rs_m', 'ff', 'rs_1n')
]

# ea2468 is excluded from the evaluation tables and is not configured here.
# QuAcq's two published modes; example-first and example-only are separate
# conditions. QuAcq-active is not run (§7 C1 decision 1, retracted and re-settled).
QUERY_MODES = ('example_only', 'example_first')

# Cells with no condition-A reference at all. Their estimate is a placeholder chosen
# to be schedulable and conservative; it must never be used as a measurement baseline.
NOMINAL_ESTIMATES = {('busybox', 'rs_m')}

STATUS_PENDING = 'pending'
STATUS_LONG_RUN = 'long-run'
STATUS_NO_ESTIMATE = 'no-estimate'

# One fold of busybox rs_1n is ~1.2 days. No window holds it, so it is tagged out
# of windowed execution rather than left to be picked up and killed repeatedly.
LONG_RUN_THRESHOLD_H = 12.0

_STEM = {v: k for k, v in KBS.items()}


def _unit(kb: str, sampling: str, algorithm: str, fold: int,
          query_mode: Optional[str], estimate: Optional[float]) -> dict:
    stem = _STEM[kb]
    suffix = f"_{query_mode}" if query_mode else ""
    if estimate is None:
        status = STATUS_NO_ESTIMATE
    elif estimate >= LONG_RUN_THRESHOLD_H:
        status = STATUS_LONG_RUN
    else:
        status = STATUS_PENDING
    # A nominal estimate is a schedulable placeholder, not a condition-A reference.
    # Without this flag an "actual / estimate" ratio computed over it looks like a
    # measurement of ConGen against AcqMss when it is really a measurement against a
    # number invented to get the unit scheduled -- which is how busybox rs_m briefly
    # reported a 0.060x ratio against a figure nobody measured.
    source = 'nominal' if (kb, sampling) in NOMINAL_ESTIMATES else 'condition-A'
    return {
        'id': f"{algorithm}{suffix}|{stem}_{sampling}|fold{fold}",
        'kb': kb, 'kb_stem': stem, 'sampling': sampling,
        'estimate_source': source,
        'algorithm': algorithm, 'query_mode': query_mode,
        'solver_mode': SOLVER_MODE, 'fold': fold,
        'estimate_h': estimate, 'status': status,
        'actual_h': None, 'commit': None,
        'started_utc': None, 'finished_utc': None,
        'partial': (f"{stem}_{sampling}_{SOLVER_MODE}{suffix}_fold{fold}.json"),
        'note': None,
    }


# Per-fold hours for QuAcq example_only. This mode is cap-independent: the example
# pool exhausts long before any cap under consideration — the largest pool in the
# sweep is 582, at REAL-FM-4 rs_3n, against caps of 1,000 and 5,000 — so these units
# are not blocked by the cap decision and their cost does not depend on it.
#
# fqa and arcade are measured (15.3 s and 25.1 s for three folds: ~0.0014 and ~0.0023
# h/fold). The rest are NOMINAL and deliberately loose, because cost scales with pool
# size and bias size and busybox carries 6,635 bias constraints against arcade's
# 1,755. Rounding up can only make the queue decline a unit it could have run.
EXAMPLE_ONLY_ESTIMATES: Dict[str, float] = {
    'REAL-FM-7': 0.01, 'fqa': 0.01, 'arcade': 0.01, 'REAL-FM-4': 0.10,
    'busybox': 1.00,
}


def build_units() -> List[dict]:
    """Every atomic unit, cheapest first, ConGen before QuAcq.

    QuAcq units carry no estimate: the only measurement is 252 s for three KBs at
    rs_1n at the old 1,000 cap, and the cap is moving to 5,000. Step 4 probes one
    cell and fills these in; until then the runner will not pick them.
    """
    units: List[dict] = []
    for kb, sampling in ORDER:
        units.append(_unit(kb, sampling, 'congen', 0, None, ESTIMATES[kb][sampling]))
        units[-1:] = [_unit(kb, sampling, 'congen', f, None, ESTIMATES[kb][sampling])
                      for f in range(N_FOLDS)]
    for query_mode in QUERY_MODES:
        for kb, sampling in ORDER:
            # example_only is cap-independent, so it can be estimated and run before
            # the cap is settled. example_first cannot: its cost is a direct function
            # of the cap, and the cap is the open question.
            est = EXAMPLE_ONLY_ESTIMATES.get(kb) if query_mode == 'example_only' else None
            units += [_unit(kb, sampling, 'interactive', f, query_mode, est)
                      for f in range(N_FOLDS)]
    return units
