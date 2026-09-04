# Code Review: Pipeline Simplification Refactor

**Date**: 2026-02-18
**Scope**: `apps/run_congen_eval.py`, `apps/extract_results.py`, docs updates, deleted files
**LOC delta**: ~−547 net (1139 → 621 in extract_results, ~−92 in run_congen_eval)

---

## Overall Assessment

The simplification is sound. Deleting `evaluate_congen_results.py` + config is justified — the CV JSON already contains all needed data. The DRY refactor in `extract_results.py` is well-executed: `_compact_grid_md`, `_compact_grid_latex`, `_latex_wrap`, and `_get_result` are clean, composable helpers that correctly unify ~16 paired MD/LaTeX functions. No regressions in table logic found. Docs are consistently updated.

Two dead-code issues remain in `run_congen_eval.py` that should be cleaned up.

---

## Issues

### High Priority

#### H1 — Dead code: `get_strategies()` + `EvaluationStrategy` import in `run_congen_eval.py`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen_eval.py`, lines 27, 67–76, 244–245, 254

After removing Option 1 (pre-computed result evaluation), `EvaluationStrategy` and `get_strategies()` have no remaining callers in the CV-only path. The local `strategies` variable is built and only printed; it is never passed to `evaluate_model()` or `n_fold_cross_validation()`.

```python
# run_congen_eval.py — dead after Option 1 removal
from conacq.eval import (
    ComparationStrategy,  # ← never used in CV path

...
)

def get_strategies(strategy_config: str) -> List[ComparationStrategy]:  # ← dead function
    ...


# In main():
strategies = get_strategies(...)  # ← dead variable
print(f"Strategies: {[s.value for s in strategies]}")  # ← misleading output
```

`strategies` printed in the header implies this controls execution — it does not. A user passing `strategy=clause` in config would see it printed but get no change in behaviour. This is a **correctness / UX confound**.

**Fix**: Remove `EvaluationStrategy` import, `get_strategies()` function, and the `strategies` local + print line. Remove the `strategy` key from the config parsing block or document it as ignored.

---

### Medium Priority

#### M1 — Dead loop variable `args_extra` in `extract_results.py`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/apps/extract_results.py`, lines 580–587

```python
for gen, args_extra in [          # args_extra unpacked but never used
    (generate_table7, {}),
    (generate_table9, {}),
    (lambda r, m, f: ..., {}),
    (lambda r, m, f: ..., {}),
]:
    md_content.append(...)
    latex_content.append(...)
```

`args_extra` is always `{}` and never referenced inside the loop. This is likely a remnant from a design that planned per-generator extra kwargs. Since it's unused, the tuples should be unwrapped to a plain list of generators.

**Fix**:
```python
for gen in [generate_table7, generate_table9,
            lambda r, m, f: generate_single_strategy_table(r, m, f, '2cov', 10, 'Accuracy with 2-COV'),
            lambda r, m, f: generate_single_strategy_table(r, m, f, 'ff', 11, 'Accuracy with FF')]:
    md_content.append("\n" + gen(results, mode, 'md'))
    latex_content.append("\n" + gen(results, mode, 'latex'))
```

#### M2 — `_mean_std` defined inside `load_cv_result()` — consider module-level

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/apps/extract_results.py`, lines 137–142

`_mean_std` is a pure utility but is defined as a nested function inside `load_cv_result()`. It is called only four times in that same function, so semantically it's fine, but it is redefined on every call to `load_cv_result()`. Extracting it to module level as a private helper would make the function body more readable and avoids repeated allocation of the closure object.

This is low-severity (no correctness impact, just minor memory/style concern). Not required to fix.

#### M3 — `statistics.pstdev` guard inconsistency

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/apps/extract_results.py`, line 141

```python
s = statistics.pstdev(values) if len(values) > 1 else 0.0
```

`statistics.pstdev([x])` returns `0.0` for a list with a single value, so the guard is logically redundant. That said, the guard makes the intent explicit (single-fold = no spread), so it is harmless. Leave as-is or simplify to `statistics.pstdev(values)`.

---

### Low Priority

#### L1 — Plan file not updated to reflect completion

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260218-1514-simplify-pipeline/plan.md`

All five phases remain marked `status: pending` and all table rows show `pending`. The work is done — the plan should be updated to `complete` for all phases (or at least the overall status changed to `complete`).

#### L2 — `ModelConfig.result` field removed from dataclass but TOML config may still have `result = ...` entries

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen_eval.py`, line 39 (after diff)

The `result` field was removed from `ModelConfig` and `parse_models()`. If any existing TOML config files still contain `result = "..."` entries under `[[models]]`, they will be silently ignored (Python dicts don't error on unused keys from TOML). No runtime breakage, but stale config keys can mislead. Worth auditing the active TOML files.

---

## Positive Observations

- **DRY refactor quality is high.** `_compact_grid_md` / `_compact_grid_latex` / `_latex_wrap` are well-named, properly parameterised with `cell_fn: Callable[[CVResult], str]`, and used consistently across all generated tables. The `fmt` parameter approach cleanly unifies MD and LaTeX paths in each public generator.
- **`_get_result()` helper** eliminates repeated three-level dict lookups and centralises the `KB_REVERSE` lookup. Good abstraction.
- **`setdefault` chain** in `load_all_results()` (line 179) is a clean Pythonic replacement for the nested `if not in` pattern.
- **Fold metrics extraction** (lines 129–135) correctly iterates all folds (not just the first), and correctly handles empty `metrics` dicts via the `if metrics:` guard.
- **`_latex_wrap`** correctly conditionalises the `(mode)` suffix on the caption and label — the `mode=''` default supports callers like `generate_incremental_comparison` that pass no mode.
- **Deletion of `evaluate_congen_results.py`** is justified; the script was computing metrics already present in `_cv_*.json` and its output was not consumed by any paper table generator.
- **No leftover references** to the deleted files found in `apps/`, `conacq/`, or `tests/` (the remaining references to `Evaluator`, `BiasData`, `ConGenResultData`, etc. are in `run_interactive_eval.py`, `interactive/learner.py`, and `conacq/eval/` — all unrelated to the deleted scripts).
- **Docs updated consistently** across all four documents (`codebase-summary.md`, `project-roadmap.md`, `system-architecture.md`, `project-overview-pdr.md`).

---

## Summary of Actions Required

| Priority | File | Action |
|----------|------|--------|
| H1 | `apps/run_congen_eval.py` | Remove `EvaluationStrategy` import, `get_strategies()`, `strategies` variable, and its print line |
| M1 | `apps/extract_results.py` | Unwrap `(gen, args_extra)` tuples to plain generator list |
| L1 | `plans/260218-1514-simplify-pipeline/plan.md` | Update all phase statuses and overall status to `complete` |
| L2 | `apps/conf/run_congen_eval_config.toml` (and siblings) | Audit for stale `result = ...` keys under `[[models]]` |

---

## Unresolved Questions

- Should `strategy` config key in `run_congen_eval_config.toml` be removed or documented as "no-op (reserved)"? Currently it is parsed, printed, but has no effect on CV execution.
