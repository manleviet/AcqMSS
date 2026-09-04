# Code Review: Remove DescriptionProvider from ConGen.acquire()

## Scope
- Files reviewed: 15 changed files (core algorithm, callers, tests, explanation layer)
- Focus: Correctness of DescriptionProvider removal, parameter rename consistency, backward compatibility
- Scout: Searched all `.py` files for stale references to old field/param names

## Overall Assessment

Clean SRP refactoring. Presentation logic (name resolution) correctly extracted from algorithm core into `resolve_congen_names()` utility. The unified `negation_map` replacing `neg_c_map` + `neg_tc_map` is a good simplification.

**One critical bug found in QuAcq.**

## Critical Issues

### 1. QuAcq passes old `neg_map=` keyword to renamed `Reduce.reduce()` parameter

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/quacq.py` line 438

```python
redundant, non_redundant = reduce.reduce(
    set_b_prime=set_b_prime,
    set_neg_tv=[],
    set_bg=set_bg,
    neg_map=neg_map  # BUG: parameter renamed to negation_map
)
```

`Reduce.reduce()` now expects `negation_map=`, not `neg_map=`. This will raise `TypeError` at runtime. The local variable `neg_map` on line 385 should also be renamed for consistency.

**Fix:**
```python
# Line 385: rename local variable
negation_map = {}
# Line 417:
negation_map[orig_id] = neg_id
# Line 438:
negation_map=negation_map
```

## Medium Priority

### 2. Module docstring in reduce.py still references old name

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/reduce.py` line 7

```python
Mode-agnostic: all elements are assumption IDs (int), neg_map is Dict[int, int].
```

Should say `negation_map`.

### 3. Closing paren indentation in test_congen.py

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` lines 91, 135, 180

```python
            result = congen.acquire(
                set_b=task.set_c,
                ...
                negation_map=task.negation_map,
        )  # <-- 8-space indent, should be 12 or 16
```

Occurs in all three test methods. Not a bug (Python accepts it), but inconsistent.

## Low Priority

### 4. Unused `congen_model` variable in tests

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` lines 76, 120, 165

`create_checker_and_task()` now returns `model` as the third element, but test methods never use `congen_model`. Consider using `_` placeholder or adding a comment explaining future use.

### 5. Deprecated `get_neg_tc_map()` methods have zero callers

**Files:**
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model.py` line 170
- `/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/pysat_diagnosis_model.py` line 186

Both deprecated in favor of `get_negation_map()`. No callers remain. Can be removed.

## Positive Observations

- `resolve_congen_names()` is a clean utility -- no side effects, duck-typed `provider` param
- `save_result()` with optional `description_provider` preserves JSON output format (`kb_constraints` / `redundant_constraints` keys) for backward-compatible file output
- `DescriptionProvider.get_description()` has safe fallback (`str(item)`) -- no crash on unknown IDs
- Unified `negation_map` in `DiagnosisTask` eliminates the confusing split between `neg_c_map` (constraints) and `neg_tc_map` (test cases)
- All assertion updates in tests correctly switched from `kb_constraints` to `kb_assumption_ids`
- `ConGenRunResult` (eval layer) still uses string names -- correct boundary between core (IDs) and presentation (names)
- `congen_runner.py` ID-to-name-to-clauses chain is correct: `provider.get_description(aid)` returns the constraint name, which is then looked up in `model.constraint_map`

## Recommended Actions

1. **[CRITICAL]** Fix `quacq.py` line 438: rename `neg_map` to `negation_map` to match `Reduce.reduce()` signature
2. **[MEDIUM]** Update reduce.py module docstring
3. **[LOW]** Fix closing paren indentation in test_congen.py (3 occurrences)
4. **[LOW]** Remove dead `get_neg_tc_map()` methods or keep with deprecation warning

## Unresolved Questions

- Should `resolve_congen_names` have a Protocol type hint for `provider` instead of duck typing? Not blocking, but would improve IDE support.
