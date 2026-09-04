# Detector run — SAT4J timeout contamination check

**Date:** 2026-07-12 · **Branch:** feat/redesign-abc-v2 · **After:** commit d72cc86 (SolverTimeoutError fix)

## Question
Did the old silent SAT4J timeout (`TimeoutExpired → output="TIMEOUT" → is_sat=False`, i.e. silent UNSAT)
contaminate any recorded result? Previously unanswerable — the failure was silent.

## Method
1. Provenance: grep SAT4J invocation across the production/paper pipeline.
2. Detector: re-run every SAT4J code path on the patched build; a raise ⇒ contaminated, clean ⇒ sound.

## Findings

### 1. Paper results are PySAT-only — SAT4J never in the pipeline
- `grep -rniE "sat4j" apps/ conacq/` → **0 hits**. No experiment runner (run_cv, run_compare,
  run_congen, run_quacq, run_evaluation) ever selects SAT4J.
- Apps toggle only `use_incremental` (PySAT incremental vs non-incremental). Result files tagged
  `_incremental` (e.g. `data/results/congen/REAL-FM-7_rs_m_cv_incremental.json`), never sat4j.
- ⇒ Recorded paper numbers could not be reached by the SAT4J timeout bug, regardless of whether a
  timeout ever occurred. Stronger than the pre-check assumption ("SAT4J only cross-validates").

### 2. The only SAT4J runs (test cross-validation) run clean
- SAT4J executes solely in `tests/test_diagnosis.py` (SAT4J-parametrized cases): cross-validates the
  diagnosis algorithms against an independent solver.
- Detector run: `pytest tests/test_diagnosis.py -k sat4j` → **70 passed, 0 SolverTimeoutError**, 56.7s
  total wall-clock across all 70 (no single call near the 300s ceiling — test FMs are small: REAL-FM-7 etc.).

## Conclusion
No contamination. Paper results never depended on SAT4J (PySAT-only pipeline); the SAT4J cross-validation
suite completes far under the timeout. The fix stands as a permanent detector: any future SAT4J timeout now
raises instead of silently recording a wrong UNSAT.

## Unresolved questions
None.
