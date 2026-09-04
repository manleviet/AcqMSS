# Phase B4 Implementation Report
## B4 — builder statelessness + FMOracle purity

**Status:** DONE  
**Suite:** 468 passed, 1 warning (same as baseline)

---

## Part 1 — Kill `builder.last_task`

### Complete reader set (found by grep before touching code)

| Location | Type | Conversion |
|---|---|---|
| `conacq/algorithms/acqmss/congen_model_builder.py` :57/:93/:97 | attr definition + write | Removed attr; `_post_negation_build` → no-op |
| `conacq/algorithms/quacq/quacq_model_builder.py` :34/:46 | attr definition + write | Removed attr; `_post_negation_build` → no-op |
| `conacq/algorithms/quacq/__init__.py` :27 | docstring example | Updated example to `model.prepare_task(oracle)` |
| `conacq/runners/quacq_runner.py` :227 | comment only | Updated comment |
| `tests/test_congen.py` :57 | `create_checker_and_task` helper | `pos,neg=builder.get_examples()` + `_make_task_input` + `model.prepare_task(task_input, oracle)` |
| `tests/test_congen.py` :277/:288/:289/:307/:362 | `TestConGenModelBuilder` assertions | Replaced with explicit `prepare_task()` call; assertions now on returned task |
| `tests/test_quacq.py` :55 | `interactive_model` fixture | `task = model.prepare_task(oracle)` |
| `tests/test_quacq.py` :253 | inline in `test_quacq_learn_with_query_limit` | `task = model.prepare_task(oracle)` |
| `tests/test_quacq.py` :420 | `test_prepare_task_returns_task` | `task = model.prepare_task(oracle)` |
| `tests/test_assumption_slicer.py` :309 | `congen_task` fixture | `pos,neg=builder.get_examples()` + `_make_task_input` + `model.prepare_task(task_input, oracle)` |
| `tests/test_assumption_slicer.py` :368 | `quacq_task` fixture | `model.prepare_task(oracle)` |
| `tests/test_assumption_slicer.py` :509/:526 | `TestOracleAwareTaskPreparationIntegration` | Same pattern as fixtures above |

**Assertion preservation confirmed:** every `assert builder.last_task is not None` and `assert len(builder.last_task.set_kb) > 0` was replaced with equivalent assertions on the explicit `prepare_task()` return. No assertion deleted.

`explanation/models/abstract_model_builder.py` docstring updated (references to `last_task` removed).

---

## Part 2 — FMOracle purity (FULL RESTRUCTURE)

### How maps now flow (no model round-trip)

**Before:**
```
prepare(model, config) → writes _pos_map, _neg_map, _base_set_c, _bg_data onto model
prepare_task() → reads self._pos_map etc. from model to build codec
fm_oracle.py → reads self._oracle_model._base_set_c
```

**After:**
```
prepare(model, config) → pure; computes all maps locally → returns _FMPrepResult(output, pos_map, neg_map, base_set_c, bg_data)
prepare_task() → reads directly from _FMPrepResult → builds codec → attaches task.base_set_c
fm_oracle.py → reads self._base_task.base_set_c  (# type: ignore[attr-defined])
```

**New internal carrier:** `_FMPrepResult` dataclass in `fm_oracle_model.py` holds the 4 maps. Never leaves the module.

**`_bg_data` on model:** kept as a cached field on `FMOracleModel` (populated lazily in `prepare_task()` on first call, idempotent). This allows `oracle.get_bg_data()` to work without requiring a task reference at the oracle level. The key invariant is that `prepare()` no longer writes it — only `prepare_task()` caches it after reading from `_FMPrepResult`.

### Files modified for PART 2

- `conacq/oracle/fm_oracle_model.py` — added `_FMPrepResult` dataclass; `prepare()` now pure; `prepare_task()` reads from result, attaches `task.base_set_c`
- `conacq/oracle/fm_oracle.py` `:106,:192` — `self._oracle_model._base_set_c` → `self._base_task.base_set_c`
- `tests/test_oracle_model.py` `:67,:90,:110,:122` — `model._base_set_c` → `task.base_set_c`
- `tests/test_assumption_slicer.py` `TestSite5` class — `model._base_set_c` → `task.base_set_c` (each test now calls `model.prepare_task()` to get task)

---

## model_to_config byte-identical evidence (≥2 FMs)

Verified via live Python execution post-restructure:

| FM | complete_configuration deterministic | get_c() == task.base_set_c |
|---|---|---|
| REAL-FM-7 (14 features, 14 constraints) | True | True |
| arcade-game (65 features, 71 constraints) | True | True |

`is_valid` confirmed working correctly (all-true config → False per FM constraints; oracle correctly rejects it).

---

## Files Modified

| File | Change |
|---|---|
| `conacq/oracle/fm_oracle_model.py` | FULL RESTRUCTURE — `_FMPrepResult` dataclass, pure `prepare()`, `prepare_task()` reads from result |
| `conacq/oracle/fm_oracle.py` | 2 reads: `_oracle_model._base_set_c` → `_base_task.base_set_c` |
| `conacq/algorithms/acqmss/congen_model_builder.py` | Remove `last_task`, `_post_negation_build` → no-op, update docstring examples |
| `conacq/algorithms/quacq/quacq_model_builder.py` | Remove `last_task` + `Optional` import, `_post_negation_build` → no-op, update docstring |
| `conacq/algorithms/quacq/__init__.py` | Update docstring example (line :27) |
| `conacq/runners/quacq_runner.py` | Update comment (line :227) |
| `explanation/models/abstract_model_builder.py` | Update docstring (remove last_task references) |
| `tests/test_congen.py` | Update `create_checker_and_task` helper + 4 `TestConGenModelBuilder` tests |
| `tests/test_quacq.py` | Update `interactive_model` fixture + 2 inline last_task usages |
| `tests/test_assumption_slicer.py` | Update `congen_task`/`quacq_task` fixtures + 2 integration tests + `TestSite5` (5 tests) |
| `tests/test_oracle_model.py` | Update 4 `model._base_set_c` → `task.base_set_c` |

---

## Tests Status

- **Baseline:** 468 passed, 1 warning
- **Post-implementation:** 468 passed, 1 warning
- **Type check:** N/A (Python; all `# type: ignore[attr-defined]` comments used where dynamic attrs added to dataclass instances)
- **Deviations from spec:** None

---

## Unresolved Questions

None.
