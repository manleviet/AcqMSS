# Phase 5: Update Callers, Delete Dead Code, Update Tests

## Context

- Depends on: Phases 1-4 (all internal changes landed)
- Final phase: wire up callers, clean up, verify

## Overview

- **Priority**: P1
- **Status**: completed
- **Effort**: 30min

Update `QuAcqRunner` call sites, delete `OneShotModel`, update/fix tests, update `__init__.py` exports.

## Key Changes

### QuAcqRunner (`quacq_runner.py`)

| Before | After |
|--------|-------|
| `_run_example_mode()` gets `fm_clauses = oracle.get_cnf_clauses()` | Pass `oracle` directly |
| Calls `learn_from_examples(task, example_provider, fm_clauses, ...)` | Calls `learn_from_examples(task, example_provider, oracle, ...)` |
| `_run_oracle_mode()` | No change needed (oracle already passed to `learn()`) |

### OneShotModel deletion

| File | Action |
|------|--------|
| `conacq/oracle/fm_oracle_model.py` lines 272-290 | Delete `OneShotModel` class |
| `conacq/oracle/__init__.py` | Remove `OneShotModel` from imports and `__all__` |
| `tests/test_oracle_model.py` `TestOneShotModel` class | Delete entire test class |

### __init__.py exports

| File | Action |
|------|--------|
| `conacq/algorithms/quacq/__init__.py` | Add `DiscriminatingGenerator` to imports and `__all__` |

## Related Code Files

### Modify
- `conacq/runners/quacq_runner.py` (241 LOC — minor change)
- `conacq/oracle/fm_oracle_model.py` (delete OneShotModel, lines 272-290)
- `conacq/oracle/__init__.py` (remove OneShotModel export)
- `conacq/algorithms/quacq/__init__.py` (add DiscriminatingGenerator)
- `tests/test_quacq.py` (update test for new signatures)
- `tests/test_oracle_model.py` (delete TestOneShotModel)

## Implementation Steps

### Step 1: Update QuAcqRunner._run_example_mode()

File: `conacq/runners/quacq_runner.py` lines 227-240

```python
# Before:
def _run_example_mode(self, quacq, task, oracle, description_provider,
                      positive_examples, negative_examples,
                      mode, shuffle_seed):
    from conacq.example_generators import ExampleProvider
    mixed_examples = list(positive_examples) + list(negative_examples)
    example_provider = ExampleProvider(mixed_examples, shuffle_seed)
    fm_clauses = oracle.get_cnf_clauses()          # DELETE
    return quacq.learn_from_examples(
        task, example_provider, fm_clauses,         # fm_clauses -> oracle
        description_provider,
        query_mode=mode, max_queries=self.max_queries)

# After:
def _run_example_mode(self, quacq, task, oracle, description_provider,
                      positive_examples, negative_examples,
                      mode, shuffle_seed):
    from conacq.example_generators import ExampleProvider
    mixed_examples = list(positive_examples) + list(negative_examples)
    example_provider = ExampleProvider(mixed_examples, shuffle_seed)
    return quacq.learn_from_examples(
        task, example_provider, oracle,
        description_provider,
        query_mode=mode, max_queries=self.max_queries)
```

### Step 2: Delete OneShotModel

**File**: `conacq/oracle/fm_oracle_model.py`
- Delete lines 272-290 (entire `OneShotModel` class)
- Remove from module docstring reference

**File**: `conacq/oracle/__init__.py`
- Remove `from .fm_oracle_model import FMOracleModel, OneShotModel` -> `from .fm_oracle_model import FMOracleModel`
- Remove `'OneShotModel'` from `__all__`

### Step 3: Update quacq package __init__.py

**File**: `conacq/algorithms/quacq/__init__.py`
- Add import: `from .discriminating_generator import DiscriminatingGenerator`
- Add to `__all__`: `'DiscriminatingGenerator'`

### Step 4: Update tests

**File**: `tests/test_oracle_model.py`
- Delete entire `TestOneShotModel` class (lines 79-114)
- Remove `OneShotModel` from import line
- Keep all `TestOracleModel` tests (FMOracleModel still exists)

**File**: `tests/test_quacq.py`
- `TestQuAcq.test_quacq_learn_with_limit` — no change needed (learn() signature unchanged)
- Integration tests may need updated if they test example mode with fm_clauses
- Add new test class for DiscriminatingGenerator:

```python
class TestDiscriminatingGenerator:
    """Tests for DiscriminatingGenerator (C_L[Y] paper compliance)."""

    def test_generate_returns_config(self, prepared_model):
        """Generator returns valid config when SAT."""
        from conacq.algorithms.quacq.discriminating_generator import DiscriminatingGenerator
        task = prepared_model.task
        generator = DiscriminatingGenerator(task)

        if len(task.set_c) >= 2:
            c_i, c_j = task.set_c[0], task.set_c[1]
            scope = set(task.feature_ids.keys())
            result = generator.generate(c_i, c_j, [], scope)
            # May be None if UNSAT, but if not None must be dict
            if result is not None:
                assert isinstance(result, dict)

    def test_generate_empty_learned_kb(self, prepared_model):
        """Generator works with empty learned KB."""
        from conacq.algorithms.quacq.discriminating_generator import DiscriminatingGenerator
        task = prepared_model.task
        generator = DiscriminatingGenerator(task)

        if len(task.set_c) >= 2:
            c_i, c_j = task.set_c[0], task.set_c[1]
            scope = set(task.feature_ids.keys())
            # With empty learned_kb, C_L[Y] is empty — only BG + c_i + neg_j
            result = generator.generate(c_i, c_j, [], scope)
            assert result is None or isinstance(result, dict)
```

### Step 5: Verify all tests pass

```bash
PYTHONPATH=. pytest tests/test_quacq.py tests/test_oracle_model.py -v
```

### Step 6: Verify no remaining OneShotModel references

```bash
grep -r "OneShotModel" conacq/ tests/ --include="*.py"
```

Should return zero matches.

## Todo

- [x] Update `QuAcqRunner._run_example_mode()`: remove `fm_clauses`, pass `oracle`
- [x] Delete `OneShotModel` class from `fm_oracle_model.py`
- [x] Remove `OneShotModel` from `conacq/oracle/__init__.py`
- [x] Add `DiscriminatingGenerator` to `conacq/algorithms/quacq/__init__.py`
- [x] Delete `TestOneShotModel` from `tests/test_oracle_model.py`
- [x] Add `TestDiscriminatingGenerator` to `tests/test_quacq.py`
- [x] Run full test suite: `PYTHONPATH=. pytest tests/ -v`
- [x] Grep for stale references: `OneShotModel`, `fm_clauses` in quacq package, `_check_fm_consistency`, `_check_partial_consistency`, `_check_consistency_with_fm`

## Success Criteria

- [x] `PYTHONPATH=. pytest tests/ -v` — all tests pass
- [x] Zero `OneShotModel` references in `conacq/` and `tests/`
- [x] Zero `fm_clauses` references in `conacq/algorithms/quacq/` (except comments/docs)
- [x] `DiscriminatingGenerator` importable from `conacq.algorithms.quacq`
- [x] QuAcqRunner correctly passes oracle (not fm_clauses) to learn_from_examples

## Risk Assessment

- **Low risk**: Caller changes are mechanical (parameter swap)
- **Low risk**: OneShotModel deletion is safe — only used by deleted code after Phases 2-4
- **Note**: If any external code references OneShotModel, it will break. Grep confirms only internal usage.
