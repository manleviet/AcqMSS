# Code Review: Part 4 ConsistencyChecker for Pruning

**Date**: 2026-02-28
**Reviewer**: code-reviewer
**Plan**: `plans/260228-0349-part4-consistency-checker/`

---

## Code Review Summary

### Scope
- **Files**: `bg_data.py`, `fm_oracle_model.py`, `task_preparation.py`, `quacq_model.py`, `quacq.py`, `quacq_runner.py`, `test_quacq.py`, `fm_oracle.py`, `example_generators/__init__.py`
- **LOC changed**: ~350 (additions/modifications)
- **Focus**: Part 4 feature assignment data flow from Oracle through BGData/QuAcqTask to SAT-based pruning in QuAcq
- **Tests**: 62/62 pass (test_quacq.py), 356/356 full suite reported passing

### Overall Assessment

Solid implementation. The data flow is clean: Oracle extracts Part 4 assignment assumptions -> BGData stores them -> QuAcqTask copies with defensive copies -> QuAcqModel exposes combined KB/assumptions -> CheckerFactory creates checker with full KB -> QuAcq uses checker for SAT-based pruning. Backward compatibility preserved via None defaults. Two notable issues found, one medium, one low.

---

### Critical Issues

None.

---

### High Priority

**H1. REDUCE exception handling removed**

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 262-268)

Old `_apply_reduce` had try/except that returned `learned_kb` as-is on failure. New inline REDUCE call has no safety net. If `Reduce.reduce()` throws (e.g., solver timeout, corrupt state), the entire `learn()` call crashes without returning partial results.

The old behavior was arguably too permissive (silently swallowing errors), but the new behavior is a regression in resilience.

**Recommendation**: Either restore lightweight error handling or document this as intentional (fail-fast is valid if caller is expected to handle exceptions).

```python
# Option: minimal safety
try:
    reduce = Reduce(self.checker, self.profiler)
    redundant, kb = reduce.reduce(
        set_b_prime=learned_kb, set_neg_tv=[],
        set_bg=set_b, negation_map=negation_map)
except Exception as e:
    logging.warning('REDUCE failed: %s, using learned KB as-is', e)
    kb = list(learned_kb)
```

**H2. `_prune_rejecting_constraints` missing KeyError guard**

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 311-312)

```python
config_assumptions = [pos_map[feat] if val else neg_map[feat]
                      for feat, val in positive_example.items()]
```

If `positive_example` contains a feature name not in `pos_map`/`neg_map`, this raises `KeyError`. The legacy fallback uses `config_to_assumptions()` which silently skips unknown features. Partial configs from FindScope/FindC could trigger this.

**Recommendation**: Add guard or use `.get()` with fallback.

```python
config_assumptions = []
for feat, val in positive_example.items():
    if feat in pos_map:
        config_assumptions.append(pos_map[feat] if val else neg_map[feat])
```

---

### Medium Priority

**M1. Variable naming typo in `fm_oracle_model.py`**

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` (line 207)

Local variable `neg_assumption_to_assumption` should be `neg_assignment_to_assumption` to match the field name and `pos_assignment_to_assumption` convention. Pre-existing but carried through all references in this file.

**M2. Eager import conflicts with lazy `__getattr__` in `example_generators/__init__.py`**

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/__init__.py` (line 4)

New direct import `from .query_generator import QueryGenerator, clause_count_priority, literal_count_priority` on line 4 makes the lazy `__getattr__` on lines 16-22 dead code. If the eager import works (confirmed: no circular import error), the lazy mechanism is redundant. Choose one approach.

**Recommendation**: Remove the `__getattr__` lazy loader since the eager import succeeds.

**M3. File size thresholds exceeded**

| File | Lines | Threshold |
|------|-------|-----------|
| `quacq.py` | 338 | ~200 |
| `fm_oracle_model.py` | 266 | ~200 |
| `quacq_runner.py` | 284 | ~200 |
| `test_quacq.py` | 825 | ~200 |

Pre-existing, but growing. `quacq.py` and `quacq_runner.py` could benefit from extraction.

**M4. `oracle.ask()` -> `oracle.is_valid()` is semantically equivalent but undocumented**

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (line 197)

Old code used `self.oracle.ask(query)` for oracle mode, `self.oracle.is_valid(query)` for example mode. New code uses `is_valid()` for both. Since `ask()` is just an alias for `is_valid()` in the ABC, this is semantically neutral but worth noting as an intentional consolidation.

---

### Low Priority

**L1. `QuAcqResult.__repr__` added but not tested with edge cases**

The new `__repr__` derives `n_kb` from `len(self.kb_assumption_ids)`. Test only checks `n_kb=3`. Edge case: empty list produces `n_kb=0`, which is fine.

**L2. `TODO: need check` comments remain in `fm_oracle.py`**

Lines 57, 88, 111, 167, 177, 193 still have `TODO: need check` comments. These are pre-existing but should be resolved.

---

### Edge Cases Found by Scouting

1. **Frozen dataclass inner mutation**: BGData is `frozen=True` with mutable list/dict fields. Attribute reassignment is blocked, but inner mutation (e.g., `bg_data.assignment_clauses.append(...)`) is possible. Mitigated by defensive copies in `QuAcqTaskPreparation`.

2. **Empty `set_b` edge case**: `_learn_params_from_task` uses `task.set_b[0] if task.set_b else None` for `root_assumption`. If `set_b` is empty, `root_assumption=None` and the legacy fallback is used. Correct behavior.

3. **REDUCE with empty learned_kb**: Old code had explicit `if not learned_kb: return []`. New code calls `reduce.reduce()` directly. Verified: `Reduce.reduce()` handles empty input correctly (empty loop -> returns `([], [])`).

4. **Checker lifecycle**: Runner creates checker after `prepare()`, passes to `learn()`, and cleans up in `finally`. If `prepare()` fails, checker is still None, cleanup is skipped (correct).

5. **`_compute_delta` with Part 4 assumptions**: The checker's `_compute_delta` computes `delta = assumptions \ set_c`. When `_prune_rejecting_constraints` passes only root + config + constraint assumption, all other assumptions (including other constraints' assumptions) are negated. This is correct: it disables all constraints except the one being tested.

---

### Positive Observations

1. **Clean data flow**: Part 4 data flows through a clear pipeline (Oracle -> BGData -> QuAcqTask -> QuAcqModel -> Checker) with defensive copies at each boundary.
2. **Backward compatibility**: None defaults on Part 4 params enable legacy fallback automatically.
3. **DI pattern consistency**: Checker injected via constructor, matching ConGen's pattern.
4. **Good test coverage**: New `TestBGDataPart4` and `TestQuAcqTaskPart4` classes verify data flow end-to-end, including default-empty and populated scenarios.
5. **Correct REDUCE refactoring**: Moving from ad-hoc `NonIncrementalPySATChecker` creation to using the DI-injected checker ensures REDUCE operates with the same KB view (including Part 4) as the rest of the algorithm.

---

### Recommended Actions

1. **[High]** Add KeyError guard in `_prune_rejecting_constraints` for partial configs (H2)
2. **[High]** Consider restoring minimal error handling around REDUCE call, or explicitly document fail-fast intent (H1)
3. **[Medium]** Fix `neg_assumption_to_assumption` typo to `neg_assignment_to_assumption` in `fm_oracle_model.py` (M1)
4. **[Medium]** Remove dead `__getattr__` lazy loader in `example_generators/__init__.py` (M2)
5. **[Low]** Clean up `TODO: need check` comments in `fm_oracle.py` (L2)

---

### Metrics

- **Type Coverage**: Adequate -- type hints on all public methods and parameters
- **Test Coverage**: 62 tests in test_quacq.py pass; 4 new Part 4 tests added
- **Linting Issues**: 0 (no syntax errors, imports resolve correctly)

---

### Unresolved Questions

1. Is the removal of REDUCE error handling intentional (fail-fast policy), or should partial results be preserved on REDUCE failure?
2. Can `_prune_rejecting_constraints` ever receive a `positive_example` with feature names not present in `pos_map`/`neg_map`? If queries always contain all features, the KeyError guard is unnecessary.
3. Should the `neg_assumption_to_assumption` typo be fixed in this changeset or tracked separately?
