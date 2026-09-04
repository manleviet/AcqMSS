# Code Review: Add Root Constraint to Background Knowledge (BG)

## Scope
- Files: 10 changed files (algorithms, eval, apps)
- LOC: ~65 additions, ~12 deletions
- Focus: Root feature [root_id] added to BG across CONGEN and QuAcq paths

## Overall Assessment

Solid implementation. The root constraint is correctly propagated through both learning paradigms (CONGEN passive, QuAcq interactive) and evaluation paths. Data format consistency between incremental/non-incremental modes is correct. A few issues found.

---

## Critical Issues

None.

## High Priority

### 1. BUG: `from_bias()` hardcodes `[1]` instead of using dynamic root ID

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py`, line 155

```python
background=bg_clauses if bg_clauses else [1],
```

**Problem:** When `bg_clauses` is `None` (default), this hardcodes root feature ID as `1`. But `_build_task_from_bias()` correctly resolves the root dynamically via `oracle.get_root_feature()` + `feature_ids.get(root_name)`. The `from_bias()` method does not have access to an oracle, so it cannot resolve the root. However, hardcoding `[1]` is fragile -- flamapy assigns IDs via tree traversal order, and while root is typically 1, this is not guaranteed by the API contract.

**Impact:** If a feature model assigns root a variable ID other than 1, `from_bias()` would silently inject the wrong constraint into BG, causing incorrect SAT solving.

**Fix options:**
- (A) Accept `[1]` as a convention and document it clearly.
- (B) Require callers of `from_bias()` to always pass `bg_clauses` explicitly. Change the default to `[]` and let the caller be responsible.
- (C) Add oracle parameter to `from_bias()` and resolve dynamically like `_build_task_from_bias()`.

Option B is cleanest -- the caller should know the root ID if they are constructing from a Bias object directly.

### 2. Type annotation mismatch in `from_bias()` parameter

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py`, line 118

```python
bg_clauses: Optional[List[int]] = None,
```

**Problem:** The parameter is named `bg_clauses` but typed as `List[int]` (assumption literals). The naming suggests `List[List[int]]` (clause format). This is inconsistent with how `bg_clauses` is used elsewhere (e.g., `CONGENResult.bg_clauses: List[List[int]]`). The `InteractiveTask.background` field is `List[int]`, so the value stored is correct, but the parameter name is misleading.

**Fix:** Rename to `bg_assumptions` or `bg_literals` to match the `List[int]` type, or change the type to match the name.

---

## Medium Priority

### 3. Non-incremental `set_b` format: triple-nested list

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py`, line 259

```python
result.set_b.append([[model.root_feature_id]])
```

**Analysis:** In non-incremental mode, `set_b` elements are `List[List[int]]` (list of clauses). The root constraint `[[root_id]]` is a single unit clause wrapped as a clause-list. This matches the existing convention in the parent class (line 590-603: `result.set_b = [result.set_kb[i]]` where `set_kb` elements are `List[List[int]]`).

**Verdict:** Correct. The triple nesting `[[[root_id]]]` means `set_b = [element]` where `element = [[root_id]]` (one clause-list containing one unit clause). Consistent with framework.

### 4. BG extraction in `congen.py` acquire() for non-incremental mode

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen.py`, lines 198-201

```python
# Non-incremental: set_b contains clause lists (List[List[List[int]]])
for clause_list in task.set_b:
    for clause in clause_list:
        bg_clauses.append(clause)
```

**Analysis:** This correctly flattens `[[[1]]]` to `[[1]]`. The comment says `List[List[List[int]]]` which is accurate. Result: `bg_clauses = [[1]]`. Correct.

### 5. Missing `bg_clauses` in early-return path of `CONGEN.acquire()`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen.py`, lines 156-165

```python
self.result = CONGENResult(
    kb_constraints=[],
    kb_assumption_ids=[],
    redundant_constraints=[],
    n_bias=len(task.set_c),
    n_mss=0,
    n_kb=0,
    metadata={'error': 'E+ inconsistent with NE ^ BG'}
)
```

**Problem:** When examples are inconsistent, the result is returned without `bg_clauses`. It uses `default_factory=list` so it defaults to `[]`. This is technically fine since the KB is empty (no evaluation needed), but for consistency and traceability, it would be better to populate `bg_clauses` even on the error path, so downstream consumers can see what BG was used.

**Impact:** Low. Evaluation of an empty KB is meaningless anyway.

### 6. No validation that `root_feature_id` is within variable range

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/model.py`

The `root_feature_id` is accepted as `Optional[int]` with no validation that it falls within the variable ID range used by the model. If a caller passes an incorrect value, the SAT solver would silently treat it as a new variable.

**Impact:** Low -- all current callers derive it from `feature_ids.get(root_name)` which is safe.

---

## Low Priority

### 7. `apps/run_congen.py` calls `oracle.get_feature_ids()` twice

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen.py`

```python
feature_ids = oracle.get_feature_ids()
root_name = oracle.get_root_feature()
root_feature_id = feature_ids.get(root_name)
# ...
feature_ids=feature_ids,  # was oracle.get_feature_ids()
```

This is actually an improvement -- the diff shows it was refactored to call once and reuse. Correct.

---

## Positive Observations

1. **Dynamic root resolution** in `_build_task_from_bias()` and `run_congen.py` -- correctly uses `oracle.get_root_feature()` + `feature_ids.get()` instead of hardcoding.
2. **Backward compatibility** preserved: `Optional[int] = None` for `root_feature_id`, `default_factory=list` for `bg_clauses`. Old callers/data unaffected.
3. **Format consistency**: Incremental uses `int` literals in `set_b`, non-incremental uses `List[List[int]]` clause-lists. Both correctly converted to `List[List[int]]` (`bg_clauses`) for evaluation.
4. **Normalization in evaluator**: `tuple(sorted(clause))` ensures clause comparison is order-independent.
5. **QuAcq path** already handles `background` as `List[int]` with `isinstance` checks in `quacq.py` (lines 299-304, 398-402).

## Recommended Actions

1. **[High]** Fix `from_bias()` -- either remove hardcoded `[1]` fallback or add required `root_feature_id` parameter.
2. **[High]** Rename `bg_clauses` parameter in `from_bias()` to `bg_literals` or `bg_assumptions` to match `List[int]` type.
3. **[Medium]** Populate `bg_clauses` in early-return error path of `CONGEN.acquire()` for consistency.

## Unresolved Questions

1. Is `from_bias()` used by external callers currently? If not, the hardcoded `[1]` is benign (only tests/internal use). If yes, it needs the fix urgently.
2. Should `InteractiveOracle` (the abstract base) declare `get_root_feature()` and `get_feature_ids()`? Currently only `AutomatedOracle` has them, which means `UserPromptOracle` cannot be used with root-aware factory methods.
