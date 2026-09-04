# Code Review: Oracle Package Refactor

**Date**: 2026-02-13
**Scope**: Oracle ABC unification, module extraction, consumer updates
**Focus**: Correctness, behavioral preservation
**Score**: 8/10

## Scope

- Files reviewed: 15 (7 new, 8 modified)
- LOC: ~900 new, ~200 modified
- Tests: 27/27 passing (test_interactive), 13/13 passing (test_congen)

## Overall Assessment

Clean, well-executed refactor. The Oracle hierarchy unification (`Oracle` + `InteractiveOracle` merged into single `Oracle` ABC) is correct. All old references removed. No lingering imports to deleted files. Module extraction into separate files follows SRP well.

## Critical Issues

None.

## High Priority

### 1. `get_cnf_clauses()` called on `Oracle` ABC but only defined on `FeatureModelOracle`

**Files affected**:
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/testcases/generators/base.py:88` -- `self.oracle.get_cnf_clauses()`
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/testcases/generators/feature_frequency.py:208` -- `self.oracle.get_cnf_clauses()`

`ExampleGenerator.__init__` accepts `Oracle` (the ABC), but `_generate_valid_config()` calls `self.oracle.get_cnf_clauses()` which only exists on `FeatureModelOracle`. This worked before the refactor because the old `Oracle` ABC also lacked this method -- `FeatureModelOracle` was always passed in practice. However, the refactor makes this a type-safety gap: if a `UserPromptOracle` or `CachedOracle` were ever passed to an `ExampleGenerator`, it would fail at runtime with `AttributeError`.

**Pre-existing issue, not introduced by this refactor**, but worth noting. The type annotation on `ExampleGenerator.__init__` should be `FeatureModelOracle` instead of `Oracle`, or `get_cnf_clauses()` should be added to the `Oracle` ABC.

### 2. `classify()` removal from ABC is correct

The old `Oracle` ABC had `classify(example: Example) -> ExampleType` as an abstract method. The new ABC drops it. The only call site was `ExampleGenerator._classify_and_add()` in `base.py:57`, which now inlines the logic:
```python
is_valid = self.oracle.is_valid(example.assignments)
example.example_type = ExampleType.POSITIVE if is_valid else ExampleType.NEGATIVE
```
This preserves the exact same behavior as the old `FeatureModelOracle.classify()`. Correct.

## Medium Priority

### 3. `UserPromptOracle.get_feature_ids()` generates synthetic IDs

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/user_prompt.py:90`

```python
def get_feature_ids(self) -> Dict[str, int]:
    return {f: i + 1 for i, f in enumerate(sorted(self.features))}
```

This generates arbitrary 1-indexed IDs from sorted feature names. If `UserPromptOracle` is used with code that depends on specific feature-to-variable mappings (e.g., CNF clauses), the IDs won't match. This is acceptable for interactive mode where no CNF solving occurs, but should be documented. The old `UserPromptOracle` (in `interactive.py`) did not have `get_feature_ids()` at all -- it only had `get_feature_count()`. So this is **new behavior** added by the refactor to satisfy the ABC contract.

**Risk**: Low. Interactive mode doesn't use feature IDs for SAT solving. But a careless consumer could get wrong results.

## Low Priority

### 4. `CachedOracle` wraps `Oracle` instead of `InteractiveOracle`

Old `CachedOracle` wrapped `InteractiveOracle` and delegated to `.ask()`. New `CachedOracle` wraps `Oracle` and delegates to `.is_valid()`. Since `Oracle.ask()` just calls `self.is_valid()`, the behavior is preserved. The `CachedOracle.is_valid()` caches based on config dict -> tuple key, which is correct.

### 5. `ExampleProvider` unchanged

Extracted to separate file without any logic changes. Verified line-by-line: identical to old version in `interactive.py`.

## Verified Correct

| Check | Status |
|-------|--------|
| `classify()` inlining preserves behavior | OK |
| All `InteractiveOracle` -> `Oracle` renames | OK (0 lingering refs) |
| All `AutomatedOracle` -> `FeatureModelOracle` renames | OK (0 lingering refs) |
| Old files deleted (`oracle.py`, `interactive.py`, `oracle_extractor.py`) | OK |
| ABC compliance: `FeatureModelOracle` implements `is_valid`, `get_features`, `get_feature_ids` | OK |
| ABC compliance: `UserPromptOracle` implements all 3 abstract methods | OK |
| ABC compliance: `CachedOracle` implements all 3 abstract methods (delegates) | OK |
| `Oracle.ask()` alias works as compatibility bridge | OK |
| `OracleData.from_uvl()` uses `FeatureModelOracle` directly | OK |
| `eval/__init__.py` imports from `acqmss.oracle.extractor` (new path) | OK |
| `evaluator.py` imports from `acqmss.oracle.extractor` (new path) | OK |
| No `from acqmss.eval.oracle_extractor` references remain | OK |
| No `from acqmss.testcases.oracle` references remain | OK |
| Tests cover: oracle creation, valid/invalid config, caching, QuAcq learn, evaluate | OK |
| `FeatureModelOracle.__del__` cleanup preserved | OK |
| 27/27 interactive tests pass | OK |
| 13/13 congen tests pass | OK |

## Positive Observations

- Clean separation: each oracle concern in its own file
- `Oracle.ask()` alias provides backward compatibility without breaking existing call sites
- `ExampleProvider` properly separated from oracle hierarchy (it's not an oracle)
- `OracleData` dataclass is well-structured for evaluation use case
- `__init__.py` exports are clean and complete

## Recommended Actions

1. **[Medium]** Narrow `ExampleGenerator.__init__` type hint from `Oracle` to `FeatureModelOracle`, or add `get_cnf_clauses()` to ABC (pre-existing issue)
2. **[Low]** Add docstring to `UserPromptOracle.get_feature_ids()` noting IDs are synthetic and not tied to any SAT model

## Metrics

- Type Coverage: Good (all public methods have type hints)
- Test Coverage: Good (all oracle variants tested, integration tests pass)
- Linting Issues: 0 (no syntax errors, clean imports)

## Unresolved Questions

None. The refactor is behaviorally correct and all consumers are properly updated.
