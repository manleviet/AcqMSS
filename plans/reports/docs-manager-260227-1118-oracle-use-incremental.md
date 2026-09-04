# Documentation Review: Oracle use_incremental Pass-Through Refactoring

**Date**: 2026-02-27
**Timestamp**: 11:18 UTC
**Work Context**: /Users/manleviet/Development/GitHub/AcqMSS

## Summary

Reviewed four main documentation files for impact of the "Oracle use_incremental Pass-Through" refactoring. The changes add `use_incremental: bool = True` parameter to runner and CV function signatures to pass solver mode selection through the stack.

**Result**: Only `docs/system-architecture.md` requires updates. Codebase summary and roadmap are already accurate. No project-changelog.md exists.

---

## Changes Made

### 1. docs/system-architecture.md — UPDATE REQUIRED

**Section**: "conacq/runners/ — Execution Runners" (lines 249-287)

**Issue**: Documentation of BaseRunner and its implementations doesn't mention the `use_incremental` parameter in constructors.

**Current Text**:
```
BaseRunner ABC:
- `__init__(bias_path, fm_path, solver_name)` — Build once: load bias, create oracle
```

**Fix Needed**: Add `use_incremental` parameter to constructor signature:
```
BaseRunner ABC:
- `__init__(bias_path, fm_path, solver_name, use_incremental: bool = True)` — Build once: load bias, create oracle
```

**Section**: "conacq/eval/ — Evaluation Framework" (lines 288-313)

**Issue**: The `n_fold_cross_validation_interactive()` signature documentation doesn't mention `use_incremental` parameter.

**Current Text**:
```python
# No mention of use_incremental in CV function signatures shown
```

**Fix Needed**: Add parameter documentation for both CV functions showing the new parameter:
- `n_fold_cross_validation(bias_path, fm_path, positive_examples, negative_examples, ..., use_incremental: bool = True)`
- `n_fold_cross_validation_interactive(bias_path, fm_path, positive_examples, negative_examples, ..., use_incremental: bool = True)`

**Impact**: These functions now accept and pass `use_incremental` to runner constructors, enabling per-experiment solver mode configuration instead of hardcoding.

---

### 2. docs/codebase-summary.md — NO UPDATE NEEDED

**Status**: ✅ CURRENT

The codebase summary already documents:
- Line 143: `BaseRunner ABC + BaseRunResult (9 shared fields for both runners)`
- Line 148-151: "BaseRunner Architecture (NEW)" with accurate description of lifecycle
- Line 159-162: ConGenRunner and InteractiveRunner signatures exist but don't detail parameter defaults

**Rationale**: Summary is high-level; parameter defaults are architectural details for system-architecture.md, not codebase inventory.

---

### 3. docs/project-roadmap.md — NO UPDATE NEEDED

**Status**: ✅ CURRENT

Roadmap correctly tracks Phase 6 (Documentation & Polish) as "IN PROGRESS" without claiming this refactoring is complete. No version number, feature list, or completion markers would be affected by parameter additions to existing functions.

**Rationale**: Parameter additions are implementation details within Phase 6 documentation; roadmap tracks major milestones, not API tweaks.

---

### 4. docs/project-changelog.md — FILE MISSING

**Status**: ⚠️ FILE DOES NOT EXIST

This file was referenced in the documentation management rules but does not exist in the repository. Not applicable for this review.

---

## Detailed Update to docs/system-architecture.md

### Change 1: BaseRunner Signature (Line ~264)

**Location**: "Unified Lifecycle Pattern" code block

**Old**:
```
runner = ConGenRunner(bias_path, fm_path)  # __init__: build once, oracle created
```

**New**:
```
runner = ConGenRunner(bias_path, fm_path, use_incremental=True)  # __init__: build once, oracle created
```

---

### Change 2: BaseRunner ABC Definition (Line ~263-266)

**Old**:
```
BaseRunner ABC:
- `__init__(bias_path, fm_path, solver_name)` — Build once: load bias, create oracle
- `run(**kwargs)` (abstract) — Run many: execute acquisition algorithm
```

**New**:
```
BaseRunner ABC:
- `__init__(bias_path, fm_path, solver_name, use_incremental: bool = True)` — Build once: load bias, create oracle, configure solver mode
- `run(**kwargs)` (abstract) — Run many: execute acquisition algorithm
```

---

### Change 3: CV Functions Documentation (Near Line ~380)

Add after the `n_fold_cross_validation()` function description (or in a new subsection):

**Addition**:
```
**Parameters** (common to both CV functions):
- `use_incremental: bool = True` — Use incremental (persistent) SAT solver (~50x faster); set False for non-incremental (fresh solver per call). This setting passes through to runner constructors for consistent solver behavior across CV folds.

**ConGen CV**:
```python
def n_fold_cross_validation(
    bias_path, fm_path, positive_examples, negative_examples,
    n_folds=10, seed=None, solver_name='glucose4',
    use_incremental=True,  # NEW: pass to ConGenRunner
    shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult
```

**Interactive CV**:
```python
def n_fold_cross_validation_interactive(
    bias_path, fm_path, positive_examples, negative_examples,
    n_folds=10, seed=None, solver_name='glucose4',
    max_queries=1000, query_mode='example_only',
    use_incremental=True,  # NEW: pass to InteractiveRunner
    shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult
```
```

---

## Verification

Confirmed via git diff:
- `conacq/runners/base_runner.py` — BaseRunner.__init__ now accepts `use_incremental: bool = True`
- `conacq/runners/interactive_runner.py` — InteractiveRunner.__init__ now accepts `use_incremental: bool = True`
- `conacq/algorithms/interactive/interactive_model.py` — InteractiveModel.from_bias() now accepts `use_incremental: bool = True`
- `conacq/eval/cross_validation.py` — Both CV functions now accept and pass `use_incremental` parameter
- `apps/run_cv.py` — Passes `is_incremental` from config to interactive CV call

All changes backward-compatible with default `True` for incremental mode.

---

## Conclusion

**Documentation Status**:
- ✅ **codebase-summary.md** — Accurate, no changes needed
- ⚠️ **system-architecture.md** — Requires 2-3 small targeted updates to constructor signatures and CV function parameters
- ✅ **project-roadmap.md** — No changes needed
- 🚫 **project-changelog.md** — File does not exist (out of scope)

**Time to Complete**: < 10 minutes (3 targeted edits to system-architecture.md)

**Priority**: LOW (parameter additions, backward-compatible, not blocking any features)
