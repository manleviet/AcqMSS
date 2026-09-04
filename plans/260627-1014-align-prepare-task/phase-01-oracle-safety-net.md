---
phase: 1
title: Oracle + task-content safety-net
status: completed
priority: P1
effort: 3h
dependencies: []
---

# Phase 1: Oracle + task-content safety-net

## Overview

Pin BOTH (a) the oracle query hot-path and (b) the ConGen/QuAcq **task content** that Phases 3–4 change,
BEFORE any production change. **Test-only phase.** Red-team finding #3: existing tests pin
`set_c/set_tc/set_tv/set_b/assumptions` but NOT `set_neg_tv`/`negation_map` end-to-end, and the only ConGen
fixture has zero negative examples — so the negative-example path is currently unprotected.

## Requirements

- Functional: lock current oracle behavior + ConGen/QuAcq task content so Stages 2–4 are provably
  behavior-preserving (the "byte-identical" claim must be test-backed, not asserted).
- Non-functional: deterministic where possible; for the non-deterministic SAT completion path pin the
  *validity invariant*, not a brittle exact model.

## Architecture

`FeatureModelOracle` composes `FMOracleModel`, caches a base task + persistent checker. `is_valid` =
`base_set_c + codec.config_to_assumptions(cfg)` → `checker.is_consistent` (deterministic). ConGen/QuAcq task
content is produced via `model.prepare_task(...)` (the path Phases 3–4 rewire) and currently asserted only by
`test_assumption_slicer.py` (strong for set_c/tc/tv, silent on set_neg_tv).

## Related Code Files

- Create: `tests/test_oracle_hotpath_safety_net.py` (oracle queries)
- Create: `tests/test_prepare_task_content_safety_net.py` (ConGen/QuAcq task content, incl. negatives)
- Read for context: `conacq/oracle/fm_oracle.py` (`is_valid` :84, `complete_configuration` :139,
  `_model_to_config` :173, `get_c/get_kb/get_assumptions` :183-195), `tests/test_assumption_slicer.py`
  (Sites 3/4/5), `tests/resource_paths.py`, `data/` example fixtures (find one with negative examples;
  red-team Q: reuse existing or synthesize via oracle)
- Modify: none (test-only)

## Implementation Steps

1. **Oracle hot-path** (`test_oracle_hotpath_safety_net.py`, ≥2 FMs REAL-FM-7 + arcade-game):
   - `is_valid` exact bool: a valid full config from `oracle.complete_configuration({})` → `True`; the
     root-false config → `False`. **Derive invalid cases ONLY from root-false + oracle-validated configs**
     (red-team #11: no hand-authored exact configs, no "violate a mandatory" guesswork).
   - `complete_configuration`: returned config non-None and `oracle.is_valid(result) is True` (invariant only).
   - completeness: every name in `oracle.get_variables()` is a key in the completed config.
   - `is_valid({'__nope__': True})` raises `KeyError`.
2. **Task content** (`test_prepare_task_content_safety_net.py`):
   - ConGen: build a `ConGenModel` with a fixture that HAS negative examples; pin exact `set_c`, `set_b`,
     `set_tc`, `set_neg_tv`, and `negation_map` slices + a deterministic hash of `set_kb`. This is the only
     pin of the negative-example branch through `ConGenModel.prepare_task`.
   - QuAcq: build a `QuAcqModel`; pin `set_c`, `set_b`, `constraint_clauses` keys, and codec pos/neg map
     sizes via `QuAcqModel.prepare_task`.
   - Capture these against the CURRENT signatures (`prepare_task(task_input, oracle)` / `prepare_task(oracle)`)
     — they become the regression oracle for Phases 3–4.
3. Run both new files, then full suite.

## Success Criteria

- [ ] Oracle net green on both FMs; `is_valid` exact-bool + `complete_configuration` validity-invariant + KeyError.
- [ ] ConGen task-content test pins `set_neg_tv` + `negation_map` on a negative-example fixture.
- [ ] QuAcq task-content test pins set_c/set_b/constraint_clauses + codec maps.
- [ ] Full suite green; total test count strictly increased.

## Risk Assessment

- Risk: no ready negative-example fixture in `data/`. Mitigation: synthesize E- by taking a valid config and
  flipping to an oracle-invalid one (root-false), or reuse a KBDiag/test fixture; record which.
- Risk: over-pinning `complete_configuration`. Mitigation: validity invariant only.

## Next Steps

Commit `test: safety-net for oracle hot-path + ConGen/QuAcq task content (incl. negatives)`; proceed to Phase 2.
