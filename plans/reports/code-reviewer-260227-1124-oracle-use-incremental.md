# Code Review: Wire `use_incremental` Through Runners to Oracle

**Date:** 2026-02-27
**Reviewer:** code-reviewer
**Scope:** BaseRunner extraction + `use_incremental` pass-through + CV integration

---

## Code Review Summary

### Scope
- **Files:** `base_runner.py` (new), `congen_runner.py`, `interactive_runner.py`, `interactive_model.py`, `cross_validation.py`, `apps/run_cv.py`, `apps/run_interactive.py`, `apps/run_evaluation.py`
- **LOC:** ~400 added/removed (significant refactor)
- **Focus:** `use_incremental` config pass-through chain, BaseRunner/BaseRunResult extraction, backward compatibility

### Overall Assessment

Solid refactoring. BaseRunner/BaseRunResult extraction eliminates duplication cleanly. The `use_incremental` pass-through chain is correct and complete for CV and ConGen paths. All new parameters have defaults (`True`), preserving backward compatibility. A few minor issues found.

---

### Critical Issues

None.

---

### High Priority

**H1. `ConGenRunner` sets `self.use_incremental` twice**
File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/congen_runner.py` line 112

```python
super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)
self.use_incremental = use_incremental  # <-- redundant, BaseRunner does not store this
```

But wait -- `BaseRunner.__init__` does NOT store `use_incremental` as an instance attribute. It only passes it to `FeatureModelOracle()`. So this second assignment is the ONLY place `self.use_incremental` is set for ConGenRunner, and it is used at line 117: `.use_incremental(use_incremental)` on `ConGenModelBuilder`.

This is not a bug, but it reveals an inconsistency: `BaseRunner` passes `use_incremental` to `FeatureModelOracle` but does not store it. `ConGenRunner` stores it. `InteractiveRunner` does NOT store it, but its `InteractiveModel.from_bias()` receives the value.

**Recommendation:** Either store `self.use_incremental` in `BaseRunner.__init__` (so children can reference `self.use_incremental` uniformly), or document the current pattern. Low risk of actual bugs since all current paths pass the value correctly through their respective constructors.

**H2. `apps/run_interactive.py` does NOT pass `use_incremental` to `InteractiveRunner`**
File: `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_interactive.py` lines 34-39

```python
runner = InteractiveRunner(
    bias_path=model_config.bias,
    fm_path=model_config.oracle,
    solver_name=solver_name,
    max_queries=max_queries
)
```

This relies on the default `use_incremental=True`. The TOML config is not parsed for an `incremental` setting here. Contrast with `apps/run_cv.py` which reads `is_incremental` from config and iterates solver modes. Not a breaking bug (default=True is reasonable), but the user has no way to disable incremental mode from the interactive runner CLI.

**H3. `apps/run_evaluation.py` does NOT pass `use_incremental` to either runner**
File: `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_evaluation.py` lines 53-58, 79-83

```python
interactive_runner = InteractiveRunner(
    bias_path=model_config.bias,
    fm_path=model_config.oracle,
    solver_name=solver,
    max_queries=max_queries
    # use_incremental missing
)
congen_runner = ConGenRunner(
    bias_path=model_config.bias,
    fm_path=model_config.oracle,
    solver_name=congen_solver
    # use_incremental missing
)
```

Both rely on defaults. For evaluation pipeline comparisons, the two runners should use the SAME solver mode to produce comparable results. Currently both default to `True`, so behavior is consistent -- but the config does not expose this option.

---

### Medium Priority

**M1. `CrossValidationFoldResult.n_mss` changed from required to `Optional[int] = None`**
File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/cross_validation.py` line 51

This is a dataclass field ordering change (moved from position 8 to after required fields). Any code constructing `CrossValidationFoldResult` by positional args will break. Checked: the only constructor call is at line 229 in `_run_cv_loop` and it uses keyword args, so this is safe. But external consumers loading serialized data would see `None` instead of `0` for interactive runs -- a positive semantic improvement (distinguishes "no MSS step" from "MSS=0").

**M2. `_run_cv_loop` removed `variables` parameter, now reads from `runner.feature_ids`**

Good simplification. All callers updated. The old callers (`n_fold_cross_validation` passed `runner.model.variables`, `n_fold_cross_validation_interactive` passed `runner.feature_ids`). Both now resolve through the abstract `feature_ids` property. Confirmed both `ConGenRunner.feature_ids` and `InteractiveRunner.feature_ids` are implemented.

**M3. `try/finally` pattern for `runner.cleanup()` in CV functions**

Good defensive addition. Previously cleanup was not guaranteed if an exception occurred mid-fold. Now the oracle is properly released even on error.

**M4. `bg_clauses` access: direct attribute vs `getattr`**

The diff changes `getattr(run_result, 'bg_clauses', [])` to `run_result.bg_clauses` (direct attribute). This is correct since `BaseRunResult` guarantees `bg_clauses` as a required field. Similarly `profiler_data` is now accessed directly. `redundant_constraints` and `n_mss` still use `getattr` since they are `ConGenRunResult`-specific. Correct.

---

### Low Priority

**L1. Import order in `cross_validation.py`**

`from conacq.runners.base_runner import BaseRunner, BaseRunResult` is imported at module level, while `from conacq.runners import ConGenRunner` and `InteractiveRunner` are lazy-imported inside functions. Consistent with avoiding circular imports. No issue.

**L2. `FeatureModelOracle` default `use_incremental=True` already existed**

The oracle constructor at `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle.py` line 36 already defaulted to `use_incremental=True`. The BaseRunner mirrors this default. Consistent.

**L3. `description_provider` passed through in `_run_example_mode` and `_run_oracle_mode`**

New method signatures include `description_provider` parameter. This was not part of the `use_incremental` wire-up but part of the broader InteractiveRunner refactor to use InteractiveModel directly.

---

### Edge Cases Found by Scout

1. **`InteractiveLearner` (deprecated) constructs its own `FeatureModelOracle` without `use_incremental` parameter** at lines 116 and 216. It defaults to `True`. Since this class is deprecated, this is acceptable tech debt, but if anyone still uses `InteractiveLearner`, they cannot control the incremental setting.

2. **`apps/generate_examples.py` line 142** constructs `FeatureModelOracle(fm_path)` without `use_incremental`. Default `True` applies. No issue for example generation.

3. **`ConGenRunner` creates oracle via `BaseRunner` with `use_incremental`, but also builds `ConGenModelBuilder.use_incremental(use_incremental)`** separately. These are two independent solver instances (one for Oracle validation, one for ConGen's internal checker). The flag is correctly threaded to both.

4. **`InteractiveModel.from_bias()` stores `use_incremental` but does not use it during `prepare()`**. The field is stored at line 48 but never read afterward. `prepare()` delegates to `InteractiveTaskPreparation.prepare()` which does not need it. This is dead state -- harmless but unnecessary.

---

### Positive Observations

- `BaseRunner` ABC with abstract `run()` and `feature_ids` property is a clean extraction
- `BaseRunResult` with `_base_to_dict()` eliminates duplicated serialization code
- `kw_only=True` on `profiler_data` field allows child dataclasses to add required positional fields
- `try/finally` cleanup pattern prevents oracle resource leaks
- All defaults are `True`, matching the pre-existing `FeatureModelOracle` default -- zero behavioral change for existing callers

---

### Recommended Actions

1. **(H1)** Store `use_incremental` in `BaseRunner.__init__` for uniformity:
   ```python
   # base_runner.py
   self.use_incremental = use_incremental
   ```
   Then remove the redundant `self.use_incremental = use_incremental` from `ConGenRunner.__init__`.

2. **(H2/H3)** Add `--incremental/--no-incremental` CLI flag to `run_interactive.py` and `run_evaluation.py`, or parse from TOML config. Low urgency since defaults work correctly.

3. **(M4, Edge Case 4)** Remove `InteractiveModel.use_incremental` field if unused, or document its intended future use.

---

### Pass-Through Chain Verification

```
apps/run_cv.py
  |-- is_incremental (from TOML config)
  |-- n_fold_cross_validation_interactive(use_incremental=is_incremental)
      |-- InteractiveRunner(use_incremental=use_incremental)
          |-- super().__init__(..., use_incremental)       # BaseRunner
          |   |-- FeatureModelOracle(fm_path, use_incremental=use_incremental)  [OK]
          |-- InteractiveModel.from_bias(..., use_incremental=use_incremental)  [OK]

apps/run_cv.py
  |-- is_incremental
  |-- n_fold_cross_validation(use_incremental=is_incremental)
      |-- ConGenRunner(use_incremental=is_incremental)
          |-- super().__init__(..., use_incremental)
          |   |-- FeatureModelOracle(fm_path, use_incremental=use_incremental)  [OK]
          |-- ConGenModelBuilder.use_incremental(use_incremental)              [OK]
```

Chain is correct and complete for the CV path. The `run_interactive.py` and `run_evaluation.py` paths rely on defaults.

---

### Metrics
- **Type Coverage:** Good -- type hints on all new signatures
- **Test Coverage:** Existing tests import/exercise runners; no new tests for `use_incremental=False` path specifically
- **Linting Issues:** 0 (imports verified clean)

---

### Unresolved Questions

1. Should `BaseRunner` store `self.use_incremental` as instance state, or leave it to subclasses?
2. Should `run_interactive.py` and `run_evaluation.py` expose `use_incremental` as a config/CLI option?
3. Is `InteractiveModel.use_incremental` field intended for future use, or dead code to remove?
