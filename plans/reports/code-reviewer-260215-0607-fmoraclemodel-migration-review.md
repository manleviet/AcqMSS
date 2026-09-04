# Code Review: FMOracleModel Migration

## Scope
- **Files**: 20 files changed (+629, -434 lines)
- **Focus**: Recent commit `012a9db` -- migrate to FMOracleModel, enhance constraint handling and NE generation
- **Scout findings**: 3 critical issues, 2 high priority, 4 medium priority

## Overall Assessment

The migration from `OracleModel` to `FMOracleModel` is a significant refactoring that restructures how the oracle layer prepares assumption-guarded clauses. The core architecture change is sound: FM constraints now use `prepare_kb()` with assumption guards, and feature assignments get dedicated assumption IDs. However, several backward compatibility issues were introduced, including a **runtime-breaking reference** to a removed attribute and a **semantic change** in `get_cnf_clauses()` that silently returns different data than before.

---

## Critical Issues

### C1. `oracle.cnf_clauses` -- Runtime AttributeError in `InteractiveLearner.from_examples()`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py`, line 213

```python
learner._fm_clauses = oracle.cnf_clauses  # AttributeError: 'FeatureModelOracle' has no attribute 'cnf_clauses'
```

The `cnf_clauses` attribute was removed from `FeatureModelOracle` during migration, but this reference was not updated. Any call to `InteractiveLearner.from_examples()` will crash.

**Fix**: Replace `oracle.cnf_clauses` with `oracle.get_cnf_clauses()`. However, see C2 below -- `get_cnf_clauses()` itself has a semantic problem.

---

### C2. `get_cnf_clauses()` returns assumption-guarded clauses, not raw FM CNF

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, lines 204-206

```python
def get_cnf_clauses(self) -> List[List[int]]:
    """Get the ground truth CNF clauses."""
    return self._oracle_model.task.set_kb  # <-- includes assumption guards!
```

**Before migration**: `cnf_clauses` contained raw FM CNF clauses like `[[1, 2], [-1, 3]]`.
**After migration**: `set_kb` contains assumption-guarded clauses like `[[1, 2, -100], [-1, 3, -100], [-101, 1], [-102, -1]]`.

This breaks **every downstream caller** that feeds these clauses to a raw SAT solver:

1. `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/example_generators/base.py:88` -- `solver.add_clause(clause)` gets clauses with extra assumption literals, making the solver produce incorrect models
2. `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/example_generators/feature_frequency.py:208` -- same issue
3. `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/extractor.py:51,83` -- `OracleData.from_fm_file()` and `from_oracle()` extract clause sets for evaluation comparison; assumption-guarded clauses will produce false negatives during accuracy evaluation

**Fix**: `get_cnf_clauses()` should return raw FM CNF without assumption guards. Options:
- Store raw FM clauses separately in `FMOracleModel` (e.g., `self._raw_fm_clauses`)
- Extract from `constraint_map` values: `[clause for clauses in model.constraint_map.values() for clause in clauses]`

---

### C3. `is_valid()` signature change breaks `Oracle` ABC contract

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, line 146

```python
# Base class ABC:
def is_valid(self, assignments: Dict[str, bool]) -> bool: ...

# New signature:
def is_valid(self, configuration: Configuration) -> bool: ...
```

The `Oracle` ABC defines `is_valid(assignments: Dict[str, bool])`, but `FeatureModelOracle.is_valid()` now takes `Configuration` (flamapy type). While `with_configuration()` handles both `dict` and `Configuration` via duck typing, the `is_valid()` method itself iterates with `for name in configuration` which works for both dicts and `Configuration` objects. However:

1. **Type annotation mismatch**: The base class says `Dict[str, bool]`, the override says `Configuration`. Static analysis tools will flag this.
2. **Error behavior changed**: Previously, unknown features were silently filtered. Now, a `KeyError` is raised. This changes the contract for callers like `CachedOracle`, example generators, and QuAcq that pass `Dict[str, bool]`.

All actual callers (example generators, cached oracle, QuAcq) pass `Dict[str, bool]`, which works at runtime because `with_configuration()` has the `hasattr(configuration, 'elements')` duck-type check. But the type annotation and docstring are misleading.

**Fix**: Keep the parameter name as `assignments` with type `Dict[str, bool]` to match the ABC, or update the ABC. Keep the duck-typing support in `with_configuration()` but document it there, not in `is_valid()`.

---

## High Priority

### H1. `generate_ne.py` -- `new_tv = tv` when `tv` is an integer creates iteration bug

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/generate_ne.py`, lines 83-97

```python
tv_list = tv if isinstance(tv, list) else [tv]
minimal_conflict = self.quickxplain.find_conflict(tv_list, set_bg)

if len(minimal_conflict) == 0:
    new_tv = tv           # <-- If tv is an int, new_tv is an int
    ...
else:
    new_tv = minimal_conflict

blocking_clause = [-lit for lit in new_tv]  # <-- Iterating over int raises TypeError
```

When `find_conflict()` returns empty (no conflict found), `new_tv = tv` preserves the original type. If `tv` is a single integer (assumption ID), iterating `for lit in new_tv` will raise `TypeError: 'int' object is not iterable`.

The `isinstance(tv, list)` wrapping only applies to the `find_conflict()` call, not to the fallback path.

**Fix**: Use `tv_list` consistently:
```python
if len(minimal_conflict) == 0:
    new_tv = tv_list  # Always use the list form
```

---

### H2. `get_num_constraints()` returns count of assumption-guarded clauses, not FM constraints

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, lines 208-210

Same semantic issue as C2. `len(self._oracle_model.task.set_kb)` counts all clauses including assumption-guarded FM clauses and feature assignment clauses -- not the number of FM constraints.

---

## Medium Priority

### M1. Dead code: `assumption_ids` list in `generate_ne.py`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/generate_ne.py`, lines 70, 108

```python
assumption_ids = []    # Line 70: initialized but never populated
...
logging.debug('<<< GenerateNE: %d NE constraints', len(assumption_ids))  # Line 108: always 0
```

The `assumption_ids` list is initialized but never appended to after the refactoring removed `assumption_ids.append()`. The log message always reports 0 NE constraints.

**Fix**: Remove `assumption_ids` and use `len(set_neg_tv)` in the log:
```python
logging.debug('<<< GenerateNE: %d NE constraints', len(set_neg_tv))
```

---

### M2. Excessive commented-out code in `fm_oracle.py`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`

63 lines of commented-out code remain. This includes:
- Old `_load_fm()`, `_extract_features()`, `_extract_leaf_features()`, `_build_feature_ids()`, `_build_cnf()` methods
- Old `get_valid_configuration()` method
- Inline commented blocks in `__init__()`

This harms readability and increases maintenance burden. If the old code is needed for reference, it is preserved in git history.

---

### M3. `congen_model_builder.py` -- `_load_model()` return type annotation says `DiagnosisModel` but returns `PySATModel`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py`, line 152

```python
def _load_model(self) -> DiagnosisModel:
```

`FmToDiagPysat.transform()` returns whatever that transformation produces; it should match the annotated return type. Also, `DiagnosisModel` and `PySATModel` are imported but `PySATModel` is unused.

---

### M4. `get_valid_configuration()` removed without replacement

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`

The method is commented out. While the test is also commented out, this was a useful API for getting valid configurations from the oracle. Any external callers or scripts using this method will break silently.

---

## Low Priority

### L1. Missing newline at end of `congen_model_builder.py`

Standard Python style requires a newline at the end of files. The file ends with trailing whitespace after the `_load_model()` method.

### L2. Commented-out code in `generate_ne.py` and `task_preparation.py`

Several commented-out fields in `NEResult`, `ConGenTask`, and `merge_ne_into_task()`. These should be cleaned up once the migration is stable.

### L3. `_use_incremental` accessed directly in test

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_oracle_model.py`, line 16

```python
assert model._use_incremental is True  # Accesses private attribute
```

Should use the public property: `assert model.use_incremental is True`

---

## Edge Cases Found by Scout

1. **`InteractiveLearner.from_examples()` -- runtime crash** (line 213 references removed `cnf_clauses` attribute). No test covers this path since `test_interactive.py` only tests the oracle directly, not the learner factory.

2. **`OracleData` evaluation comparison -- silent accuracy regression**. `get_cnf_clauses()` now returns assumption-guarded clauses. `OracleData.from_oracle()` extracts these for `clause_set` comparison. Evaluation metrics comparing learned KB against oracle clauses will produce incorrect results (false negatives) because the clause format changed.

3. **Example generators produce incorrect configurations**. `base.py` and `feature_frequency.py` feed `get_cnf_clauses()` into raw solvers. With assumption-guarded clauses, the solver sees extra variables and may produce invalid models. Configurations generated this way could misclassify examples.

---

## Positive Observations

1. **Good protocol compliance**: `FMOracleModel` correctly satisfies the `CheckerModel` protocol with the `use_incremental` property, `get_kb()`, and `get_assumptions()`.

2. **Duck typing in `with_configuration()`**: Supporting both `dict` and `Configuration` objects via `hasattr(configuration, 'elements')` is practical and prevents coupling to flamapy types.

3. **Clean separation of concerns**: `OracleTaskPreparation` as a dedicated preparation strategy follows the same pattern as `ConGenTaskPreparation`.

4. **Builder pattern preserved**: `FMOracleModel.from_fm().set_incremental().build()` maintains fluent API consistency.

5. **Test coverage is comprehensive**: 301 tests pass, covering incremental/non-incremental modes with parameterized expansion.

---

## Recommended Actions

1. **[CRITICAL]** Fix `learner.py:213` -- replace `oracle.cnf_clauses` with a working alternative (see C1)
2. **[CRITICAL]** Fix `get_cnf_clauses()` and `get_num_constraints()` to return raw FM CNF (see C2, H2)
3. **[CRITICAL]** Verify/fix `is_valid()` type annotation to match ABC contract (see C3)
4. **[HIGH]** Fix `generate_ne.py` fallback path to use `tv_list` consistently (see H1)
5. **[MEDIUM]** Remove `assumption_ids` dead variable and fix log message in `generate_ne.py` (see M1)
6. **[MEDIUM]** Clean up commented-out code in `fm_oracle.py` (63 lines), `generate_ne.py`, `task_preparation.py` (see M2, L2)
7. **[LOW]** Fix `_load_model()` return type annotation and remove unused import (see M3)
8. **[LOW]** Add newline at end of `congen_model_builder.py` (see L1)
9. **[LOW]** Use public property in test assertion (see L3)

---

## Metrics

- **Type Coverage**: Moderate -- most public methods have annotations but `with_configuration()` takes untyped `configuration`
- **Test Coverage**: Good -- 301 tests pass; however, `InteractiveLearner.from_examples()` path is not tested
- **Linting Issues**: ~5 (commented-out code, dead variable, missing EOF newline, unused import, private access in test)

---

## Unresolved Questions

1. Should `get_cnf_clauses()` return only raw FM clauses, or should it be renamed/documented to clarify it now returns assumption-guarded clauses? The answer determines the fix strategy.
2. Is `get_valid_configuration()` needed in the new architecture? If so, it needs re-implementation using the `FMOracleModel` and its assumption-based approach.
3. Was the removal of `neg_map` from `NEResult` and `neg_c_map` updates in `merge_ne_into_task()` intentional? The REDUCE algorithm may depend on negated forms for redundancy detection -- needs verification.
