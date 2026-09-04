# Code Review — ConGenModelBuilder Auto-Prepare Enhancement

**Date:** 2026-02-18
**Scope:** 3 files, ~120 LOC changed

---

## Scope

| File | Change |
|---|---|
| `conacq/algorithms/acqmss/congen_model_builder.py` | Added `with_oracle()`, last-call-wins in `with_examples()`/`with_examples_data()`, auto-prepare in `build()` |
| `conacq/algorithms/acqmss/congen_model.py` | `task` property: `RuntimeError` → `Optional[ConGenTask]` returning `None`; renamed `next_tseitin_var` → `next_available_id` |
| `tests/test_congen.py` | New `TestConGenModelBuilder` (5 tests), simplified `create_checker_and_task` helper |

---

## Overall Assessment

Clean, well-structured enhancement. All 5 new tests pass. The patterns are sensible and the builder interface is ergonomic. Three issues warrant attention, one of which is medium priority.

---

## Critical Issues

None.

---

## High Priority

None.

---

## Medium Priority

### 1. Convenience getters silently crash when `task` is `None`

`congen_model.py` lines 88–162: every convenience getter (`get_c()`, `get_b()`, `get_kb()`, `get_assumptions()`, `get_negation_map()`, etc.) calls `self.task.<attr>` directly. Because `task` now returns `Optional[ConGenTask]`, calling any getter on an unprepared model produces `AttributeError: 'NoneType' object has no attribute '...'` — a confusing error that doesn't tell the caller what went wrong.

`congen_runner.py` line 168 does `task = self.model.task` immediately after `model.prepare()`, so it's safe in that call path. But the 6 convenience getters on `ConGenModel` are part of the `CheckerModel` protocol and callers may invoke them without first checking `task is not None`.

**Recommended fix:** Add a guard in each getter, or consolidate into a single helper:

```python
def _require_task(self) -> ConGenTask:
    """Return task or raise descriptive error."""
    if self._task is None:
        raise RuntimeError(
            "Model not prepared. Call prepare() or use the builder "
            "with with_oracle() + with_examples() before calling this method."
        )
    return self._task
```

Then replace every `self.task.` in the getters with `self._require_task().`.

This restores the previous defensive behaviour without reverting the public `task` property back to raising — the `None` return is useful for tests (`assert model.task is None`).

---

## Low Priority

### 2. `with_examples_data` parameter rename is a breaking API change

The old signature was `with_examples_data(positive, negative)` (positional). The new signature is `with_examples_data(positive_examples, negative_examples=None)`. Any existing call site using positional-only or the old keyword names `positive=` / `negative=` will break silently (wrong-keyword `TypeError`) or pass successfully with the new keyword names only if the caller happened to use keyword form.

The diff shows no external callers of `with_examples_data` exist in the codebase right now (grep confirms), so this is low risk. Still, the docstring/commit should note it as a breaking rename in case callers exist outside the repo.

### 3. `get_examples()` public method has no test coverage

`ConGenModelBuilder.get_examples()` is a public method (lines 125–129) that resolves and returns examples. It has zero test coverage and is not used anywhere in the codebase. Per YAGNI, either add a test or remove it. If it exists to support a CV workflow, the CV test (`test_cv_re_prepare`) should exercise it.

---

## Positive Observations

- **Last-call-wins** is clearly documented in both docstrings and neutralises a potential footgun where mixing `with_examples()` and `with_examples_data()` would leave stale state.
- **`neg or []` fix in `_resolve_examples`** (line 144) corrects a pre-existing bug where `_negative_examples = None` was returned from `_resolve_examples` and then passed into `model.prepare()` as `None` rather than `[]`.
- **`next_tseitin_var` → `next_available_id` rename** aligns `ConGenModel` with `FMOracleModel` and `BGData`/`FMData`, which already used the new name. The rename in `congen_model.py` is complete; `task_preparation.py` correctly reads from `bg_data.next_available_id` and writes back to `model.next_available_id`.
- **`fm_data` extraction removed from `ConGenModel.prepare()`** — the model no longer calls `oracle.get_fm_data()` directly; `task_preparation.py` now fetches `bg_data` from the oracle internally. Correct separation of concerns.
- **`create_checker_and_task` simplification** — removing the unused `root_id` and `model` return values reduces noise in all three callers. All existing `TestCONGEN` tests updated consistently.
- **Test patterns directly mirror the three usage patterns in the docstring** — excellent alignment between docs and tests.

---

## Recommended Actions

1. **(Medium)** Add `_require_task()` helper to `ConGenModel` and redirect all convenience getters through it, so unprepared-model errors are descriptive rather than bare `AttributeError`.
2. **(Low)** Either add a test for `get_examples()` or remove the method.
3. **(Low)** Note the `with_examples_data` parameter rename in the commit/changelog if this API is consumed externally.

---

## Metrics

| Metric | Value |
|---|---|
| New tests | 5 (all passing) |
| Test patterns covered | 3/3 (file, data, CV) |
| Linting issues detected | 0 (via inspection) |
| mypy check | Not run (tool permission denied; flagged for follow-up) |

---

## Unresolved Questions

- Should `get_examples()` be retained as a helper for CV runners or removed (YAGNI)?
- Is `with_examples_data` API consumed by any external tool/script not in this repo?
