"""ConMin AAAI-27 revision measurements (derived data; the submitted numbers in
``data/results_conmin/`` are unchanged).

Pipeline, all run from the repo root:

1. ``relearn_kbs_with_persistence`` — re-learn the Table-5 KBs (same folds, seed, solver) and
   persist every learned KB to ``data/results_conmin_r1/kbs/`` with its shipped scores.
2. ``semantic_tier_corrected`` — semantic P/R/F1 with the root axiom as background, beside
   the submitted values (reproduction-gated), plus the standard precision formula.
3. ``solution_set_model_counting`` — solution-set P/R by exact model counting (pysdd).
4. ``cover_share_and_exact_equiv`` — C ⊆ S_full per fold and exact-equivalence rates.
"""
from pathlib import Path

R1_DIR = Path('data/results_conmin_r1')
KB_DIR = R1_DIR / 'kbs'
COMMITTED_LONG_CSV = Path('data/results_conmin/conmin_eval_long.csv')

SEED = 82                     # apps/conf_conmin/run_conmin_eval_config.toml [general] seed
SOLVER = 'glucose4'           # solver of record (same config)
KBS = ('REAL-FM-7', 'fqa', 'arcade-game', 'REAL-FM-4')   # busybox excluded (bounds only)
EXAMPLE_SETS = ('ff', 'rs_1n', 'rs_2n', 'rs_3n', 'rs_m')  # Table 5 excludes 2cov
K_VALUES = (1, 2, 3, 5)

# QuAcq-active budgets exactly as recorded in the committed rows (qa_max_queries/qa_timeout_s).
QA_BUDGET = {'REAL-FM-7': (5000, 400.0), 'fqa': (5000, 400.0),
             'arcade-game': (5000, 7200.0), 'REAL-FM-4': (5000, 20000.0),
             # busybox stopped on the WALL CLOCK at 1,901 queries (36,000 s); re-learning with the
             # deterministic rail at that point should reproduce it (see busybox_rerun.md).
             'busybox-1.18.0': (1901, 72000.0)}


def fm_path(kb: str) -> str:
    return f'data/fms/{kb}.uvl'


def bias_path(kb: str) -> str:
    return f'data/bias/{kb}-bias.json'


def examples_path(kb: str, es: str) -> str:
    return f'data/examples/{kb}_{es}.json'


def folds_path(kb: str, es: str) -> str:
    return f'data/folds/{kb}_{es}_folds.json'
