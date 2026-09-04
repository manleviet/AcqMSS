# A1 — Unify Assumption Slicer

**Phase:** 2 (A1)  
**Plan:** plans/260621-1416-redesign-abc  
**Status:** DONE  
**Date:** 2026-06-21

---

## Slicer Signature + Location

```python
# explanation/models/task_preparation.py:98
def slice_assumptions(assumptions: List[int], start: int = 0,
                      stop: Optional[int] = None, stride: int = 1) -> List[int]:
    """Return a strided slice of assumption IDs as a new list."""
    return list(assumptions[start:stop:stride])
```

Exported from `explanation/models/__init__.py` (`__all__`).

---

## 5 Sites: Before → After

### Site 1 — DiagnosisTask._assign_sets (explanation/models/task_preparation.py:~422)

Before (5 separate range-based comprehensions):
```python
step = _ASSUMPTION_PAIR_STRIDE if has_negated_forms else _ASSUMPTION_SINGLE_STRIDE
# branch: not with_cf_in_c
result.set_b = [result.assumptions[i] for i in range(0, start_id_config, step)]
# branch: with_cf_in_c
result.set_c = [result.assumptions[i] for i in range(step, start_id_config, step)] + ...
# branch: test_case
result.set_c = [result.assumptions[i] for i in range(step, start_id_config, step)]
# branch: redundancy
result.set_c = result.assumptions[step:len(result.assumptions):step]
# branch: fm_diag
result.set_c = [result.assumptions[i] for i in range(step, len(result.assumptions), step)]
```

After:
```python
stride = _ASSUMPTION_PAIR_STRIDE if has_negated_forms else _ASSUMPTION_SINGLE_STRIDE
result.set_b = slice_assumptions(result.assumptions, 0, start_id_config, stride)
result.set_c = slice_assumptions(result.assumptions, stride, start_id_config, stride) + ...
result.set_c = slice_assumptions(result.assumptions, stride, start_id_config, stride)
result.set_c = slice_assumptions(result.assumptions, stride, None, stride)
result.set_c = slice_assumptions(result.assumptions, stride, None, stride)
```

### Site 2 — TestCaseTask._assign_sets (explanation/models/task_preparation.py:~570)

Before:
```python
tc_tv_assumptions = result.assumptions[start_id_tc:]
original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), _ASSUMPTION_PAIR_STRIDE)]
```

After:
```python
original_tc_tv = slice_assumptions(result.assumptions, start_id_tc, None, _ASSUMPTION_PAIR_STRIDE)
```

### Site 3 — ConGenTask._assign_sets (conacq/algorithms/acqmss/task_preparation.py:~223)

Before:
```python
from explanation.models.task_preparation import ... _ASSUMPTION_PAIR_STRIDE
result.set_c = result.assumptions[bias_start_id:start_id_tc:_ASSUMPTION_PAIR_STRIDE]
tc_tv_assumptions = result.assumptions[start_id_tc:]
original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), _ASSUMPTION_PAIR_STRIDE)]
```

After (import changed to `slice_assumptions`):
```python
from explanation.models.task_preparation import ... slice_assumptions
result.set_c = slice_assumptions(result.assumptions, bias_start_id, start_id_tc, 2)
original_tc_tv = slice_assumptions(result.assumptions, start_id_tc, None, 2)
```

### Site 4 — QuAcqTask._assign_sets (conacq/algorithms/quacq/task_preparation.py:~126)

Before:
```python
from explanation.models.task_preparation import ... _ASSUMPTION_PAIR_STRIDE
result.set_c = list(result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])
```

After:
```python
from explanation.models.task_preparation import ... slice_assumptions
result.set_c = slice_assumptions(result.assumptions, bias_start_pos, None, 2)
```

### Site 5 — FMOracleModel (conacq/oracle/fm_oracle_model.py:~197)

Before:
```python
from explanation.models.task_preparation import ... _ASSUMPTION_PAIR_STRIDE
model._base_set_c = [result.assumptions[i]
                     for i in range(0, assignments_start_index, _ASSUMPTION_PAIR_STRIDE)]
```

After:
```python
from explanation.models.task_preparation import ... slice_assumptions
model._base_set_c = slice_assumptions(result.assumptions, 0, assignments_start_index, 2)
```

---

## Conacq Stride Imports Removed

All 3 `from ... import _ASSUMPTION_PAIR_STRIDE` at conacq sites are gone:
- `conacq/oracle/fm_oracle_model.py:19` — replaced with `slice_assumptions`
- `conacq/algorithms/acqmss/task_preparation.py:19` — replaced with `slice_assumptions`
- `conacq/algorithms/quacq/task_preparation.py:19` — replaced with `slice_assumptions`

The constant `_ASSUMPTION_PAIR_STRIDE` is now entirely internal to `explanation/models/task_preparation.py`.

---

## Characterization Tests Added

File: `tests/test_assumption_slicer.py` (24 tests, 0 failures)

| Class | Tests | Coverage |
|---|---|---|
| `TestSite1DiagnosisTaskAssignSets` | 7 | All 5 branches × 2 stride modes |
| `TestSite2TestCaseTaskAssignSets` | 2 | With/without negative TCs |
| `TestSite3ConGenTaskAssignSets` | 4 | arcade-game FM, set_b/set_c/set_tc/set_tv |
| `TestSite4QuAcqTaskAssignSets` | 3 | REAL-FM-7 FM, set_b/set_c/assumption layout |
| `TestSite5FMOracleModelBaseSetC` | 5 | arcade-game + REAL-FM-7, exclusion check |
| `TestOracleAwareTaskPreparationIntegration` | 3 | Safety-net: Part3 copy, ConGen/QuAcq integration |

Tests run GREEN against current code first (captured ground truth), then remain GREEN after the swap.

---

## Final pytest Result

```
376 passed, 3 warnings in 51.58s
```

(352 original + 24 new characterization tests. No failures.)

---

## Files Modified

| File | Change |
|---|---|
| `explanation/models/task_preparation.py` | Added `slice_assumptions()` at line ~98; replaced all range-based list comprehensions in `DiagnosisTask._assign_sets` (Site 1) and `TestCaseTask._assign_sets` (Site 2) |
| `explanation/models/__init__.py` | Export `slice_assumptions` |
| `conacq/algorithms/acqmss/task_preparation.py` | Import `slice_assumptions` (removed `_ASSUMPTION_PAIR_STRIDE`); replaced Site 3 body |
| `conacq/algorithms/quacq/task_preparation.py` | Import `slice_assumptions` (removed `_ASSUMPTION_PAIR_STRIDE`); replaced Site 4 body |
| `conacq/oracle/fm_oracle_model.py` | Import `slice_assumptions` (removed `_ASSUMPTION_PAIR_STRIDE`); replaced Site 5 body |
| `tests/test_assumption_slicer.py` | New — 24 characterization tests |

---

## Deviations from Spec

None. All 5 sites unified, all 3 conacq stride imports removed, tests-first discipline followed, full suite green.

---

## Unresolved Questions

None.
