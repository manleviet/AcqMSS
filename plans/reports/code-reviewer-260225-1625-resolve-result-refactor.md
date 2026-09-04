# Code Review: resolve_result() Refactoring

**Date:** 2026-02-25
**Reviewer:** code-reviewer
**Plan:** [260225-1616-resolve-result-refactor](../260225-1616-resolve-result-refactor/plan.md)

## Scope

- Files: 4 modified + 1 commented-out method
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen_model.py` (+33 lines)
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen.py` (-5 lines)
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/congen_runner.py` (-13 lines, +3 lines)
  - `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` (-9 lines)
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle.py` (commented out `get_root_clauses`)
- LOC delta: net -21
- Focus: encapsulation refactoring of assumption ID resolution
- All 18 test_congen.py tests pass

## Overall Assessment

The refactoring correctly improves encapsulation by moving resolution logic into ConGenModel. However, there is one **critical behavioral change** in how `bg_clauses` is computed that produces **empty BG clauses** where the old code produced actual root constraint clauses. This affects downstream accuracy evaluation.

---

## Critical Issues

### 1. `_resolve_ids(self.get_b())` produces empty `bg_clauses` -- behavioral regression

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen_model.py`, line 200

**Old code** (congen_runner.py line 241):
```python
bg_clauses = self.oracle.get_root_clauses()
# Returned: list(self._oracle_model.constraint_map[root_name])
# Example: [[1]]  (raw SAT variable clause for root feature)
```

**New code** (congen_model.py line 200):
```python
bg_clauses, _ = self._resolve_ids(self.get_b())
```

Resolution chain:
1. `self.get_b()` returns `[root_assumption_id]` (e.g., `[3001]`)
2. `provider.get_description(3001)` returns root feature name (e.g., `"Sandwich"`)
3. Looks up `self.constraint_map["Sandwich"]` -- **NOT FOUND**

`self.constraint_map` is `ConGenModel`'s map, which contains only **bias constraints** (loaded from bias JSON). The root constraint `"Sandwich"` lives in the **oracle's** `FMOracleModel.constraint_map`, which is a completely separate map.

**Result:** `bg_clauses = []` (always empty), `names = ["Sandwich"]`

**Impact:** `ConGenRunResult.bg_clauses` will always be empty. Downstream consumers:
- `cross_validation.py` line 217: `AccuracyCalculator(run_result.kb_clauses + bg_clauses, ...)` -- root excluded from accuracy calc
- `kb_comparator.py` line 186-189: `if result.bg_clauses:` block never entered
- `run_congen.py` line 104: `save_kb_result(..., bg_clauses=[])` -- root lost from saved KB JSON

**Fix:** The model does not own the oracle's raw clauses. Options:

**Option A (recommended):** Keep `oracle.get_root_clauses()` alive and call it inside `resolve_result()`:
```python
def resolve_result(self, result: ConGenResult, oracle: FeatureModelOracle) -> Tuple[...]:
    bg_clauses = oracle.get_root_clauses()  # un-comment method in fm_oracle.py
    kb_clauses, kb_names = self._resolve_ids(result.kb_assumption_ids)
    _, redundant_names = self._resolve_ids(result.redundant_ids)
    return bg_clauses, kb_clauses, kb_names, redundant_names
```

**Option B:** Store the oracle's root clauses in ConGenModel during `prepare()`:
```python
# In prepare():
self._bg_raw_clauses = oracle.get_root_clauses()

# In resolve_result():
bg_clauses = self._bg_raw_clauses
```

Option B keeps the model self-contained but introduces state coupling. Option A is simpler.

### 2. `get_root_clauses()` commented out without migration

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle.py`, line 173

The method is commented out as dead code removal. But the replacement (`_resolve_ids`) does NOT produce equivalent results (see issue #1). If the fix above is adopted, this method needs to remain active (or be replaced by an equivalent).

---

## High Priority

### 3. No test verifies `ConGenRunResult.bg_clauses` is non-empty

The 3 removed assertions (`result.bg_clauses > 0`) tested `ConGenResult.bg_clauses` which is correctly removed. But there is no test that verifies `ConGenRunResult.bg_clauses` is correctly populated after `resolve_result()`. Given issue #1, this would have caught the regression.

**Fix:** Add a runner-level integration test:
```python
def test_run_result_bg_clauses_populated(self):
    """ConGenRunResult.bg_clauses must contain root constraint."""
    runner = ConGenRunner(bias_path, fm_path)
    result = runner.run(pos, neg)
    assert len(result.bg_clauses) > 0, "bg_clauses must have root constraint"
```

---

## Medium Priority

### 4. Return type is an unnamed tuple -- fragile API

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen_model.py`, line 191

`resolve_result()` returns `Tuple[List[List[int]], List[List[int]], List[str], List[str]]` -- four positional items. Callers must remember the order (bg_clauses, kb_clauses, kb_names, redundant_names). A `NamedTuple` or dataclass would be more maintainable:

```python
class ResolvedResult(NamedTuple):
    bg_clauses: List[List[int]]
    kb_clauses: List[List[int]]
    kb_names: List[str]
    redundant_names: List[str]
```

Not urgent since there's only one caller, but worth considering if more callers appear.

### 5. Discarded `_` return value from `_resolve_ids(self.get_b())`

**Location:** line 200: `bg_clauses, _ = self._resolve_ids(self.get_b())`

Even if issue #1 is fixed (making bg_clauses non-empty), the names list for BG constraints is discarded. This is fine for now, but the asymmetry (names kept for KB/redundant, discarded for BG) should be documented.

---

## Low Priority

### 6. `fm_oracle.py` change not in scope description

The scope description mentions 4 files, but `fm_oracle.py` is also modified (commenting out `get_root_clauses()`). Minor docs gap.

---

## Positive Observations

1. **Correct encapsulation for KB/redundant resolution** -- `_resolve_ids()` correctly moves the assumption-to-name-to-clause chain from runner into model
2. **Clean TYPE_CHECKING guard** -- `ConGenResult` import under `TYPE_CHECKING` avoids runtime circular dependency
3. **ConGenResult simplification** -- Removing `bg_clauses` from the algorithm result is conceptually correct; the algorithm should not own BG clause materialization
4. **Deleted TODO** -- Removed `# TODO: check lai` on the old `bg_clauses` line (congen.py line 138), cleaning up tech debt
5. **Net code reduction** -- 21 fewer lines

---

## Recommended Actions

1. **[Critical]** Fix `bg_clauses` resolution in `resolve_result()` -- either pass oracle or cache raw clauses during `prepare()`
2. **[Critical]** Un-comment `get_root_clauses()` in `fm_oracle.py` if Option A is chosen
3. **[High]** Add integration test for `ConGenRunResult.bg_clauses` being non-empty
4. **[Medium]** Consider `NamedTuple` return type for `resolve_result()`

## Unresolved Questions

1. **Design choice:** Should `resolve_result()` receive the oracle as a parameter (Option A, stateless) or cache raw clauses during `prepare()` (Option B, stateful)? Option A is simpler; Option B keeps the method signature oracle-free.
2. **BG clause format:** The old `ConGenResult.bg_clauses` used `[[lit] for lit in set_bg]` (assumption IDs), while `oracle.get_root_clauses()` returned actual SAT variable clauses. The runner always used the oracle version. Should the new API document which format is expected?
