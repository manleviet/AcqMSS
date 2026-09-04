# Code Review: Oracle BG Data Extraction

**Date**: 2026-02-18
**Scope**: Unstaged changes extracting BGData from Oracle for ConGen consumption
**Files Changed**: 6 modified + 1 new (27 + 79 net lines changed)
**Test Results**: 302 passed, 2 failed (pre-existing missing data file, unrelated)

## Overall Assessment

Clean refactoring that eliminates `_prepare_bg`, `FMData` dependency, and skip arithmetic from `ConGenTaskPreparation`. The BGData frozen dataclass provides a well-defined interface between Oracle and ConGen. Production path is correct and verified. One medium-severity edge case in the non-production path needs a guard.

## Critical Issues

None.

## High Priority

### 1. BGData assumptions[1] incorrect when negated_constraint_map is empty

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` (lines ~265-272)

When `negated_constraint_map` is `{}` (e.g., via `from_fm_data()`), `prepare_kb` only adds the original constraint assumption -- no negated form. The code then takes `assumptions[1]` as the negated root, but it's actually the first feature assignment.

```python
# Current: always takes pair regardless of negation presence
model._bg_data = BGData(
    set_kb=result.set_kb[:root_kb_size],
    assumptions=(result.assumptions[0], result.assumptions[1]),  # [1] may be wrong
    negation_map={result.assumptions[0]: result.assumptions[1]},  # wrong mapping
    ...
)
```

**Impact**: Low in practice -- `from_fm_data()` is test-only and ConGen always uses `build()` with full negation. But the data is silently wrong.

**Fix**: Guard on negation presence:

```python
if negated_constraint_map and neg_root_key in negated_constraint_map:
    bg_assumptions = (result.assumptions[0], result.assumptions[1])
    bg_negation_map = {result.assumptions[0]: result.assumptions[1]}
else:
    bg_assumptions = (result.assumptions[0], result.assumptions[0])  # or raise
    bg_negation_map = {}
```

Or simply skip BGData creation when negation absent (raise RuntimeError on access).

## Medium Priority

### 2. Missing type annotation on `get_descriptions_for` parameter

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py`

```python
def get_descriptions_for(self, ids) -> Dict[int, str]:  # ids has no type hint
```

**Fix**: `def get_descriptions_for(self, ids: List[int]) -> Dict[int, str]:`

### 3. Missing return type annotation on `get_bg_data`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle.py`

```python
def get_bg_data(self):  # no return type
    """Return root BG assumption data for ConGen."""
    return self._oracle_model.bg_data
```

**Fix**: `def get_bg_data(self) -> 'BGData':`  (with import)

### 4. File size: fm_oracle_model.py at 299 lines

Exceeds the 200-line Python threshold. OracleTaskPreparation (52 lines) could be extracted to its own module. Not urgent since it's tightly coupled to FMOracleModel internals.

## Low Priority

### 5. BGData.set_kb typed as List but could be tuple for immutability

`BGData` is `frozen=True` but `set_kb: List[List[int]]` is a mutable list. Callers use `.extend()` to copy, which is fine, but `tuple` would enforce immutability at the data level.

### 6. Unused `Tuple` import in bg_data.py if not used elsewhere

`from typing import Dict, List, Tuple` -- `List` is used for `set_kb`, `Dict` for descriptions/negation_map, `Tuple` for assumptions. All used. No issue.

## Key Correctness Checks

### Root constraint ordering (VERIFIED)

- `FmToPysat.transform()` calls `add_root()` before `add_relation()` and `add_constraint()`
- Python dicts (3.7+) maintain insertion order
- `first_key = next(iter(model.constraint_map))` reliably gets root
- Verified with real FMs: arcade-game (ArcadeGame), REAL-FM-7 (jplug), REAL-FM-4 (eShop)

### set_kb[:root_kb_size] extraction (VERIFIED)

- `root_clause_count` = number of original root clauses
- `neg_root_count` = number of negated root clauses (0 if no negation)
- `prepare_kb` adds root clauses first, so `set_kb[:root_kb_size]` is correct
- Verified: arcade-game produces 2 KB clauses (root + NOT(root))

### No dead code (VERIFIED)

- `_prepare_bg` function fully removed
- `FMData` import removed from task_preparation.py
- `fm_data` parameter removed from `prepare()` signature
- `fm_data` usage removed from `congen_model.py`
- `_start_id_assignments` renamed to `_assignments_index` everywhere

### ID layout continuity (VERIFIED)

- Oracle Parts 1-4 end at `bg_data.next_available_id`
- ConGen Part 5 starts from `bg_data.next_available_id`
- No ID gap or overlap

### ConGen task structure (VERIFIED)

- `set_b = [assumptions[0]]` correctly references root from BGData
- `set_c` correctly references bias constraints
- `negation_map` correctly propagated from BGData + ConGen additions
- All 302 tests pass

## Positive Observations

1. **Clean separation of concerns**: BGData is a frozen dataclass, clearly defining the Oracle-to-ConGen contract
2. **Good documentation**: ID layout documented in both OracleTaskPreparation and ConGenTaskPreparation docstrings
3. **DRY improvement**: Eliminates ~35 lines of duplicated root constraint logic from ConGen
4. **No API leakage**: BGData is a snapshot, not a reference -- ConGen copies data, preventing coupling
5. **Cross-validation DRY**: The `_run_cv_loop` extraction is a clean factoring with appropriate `getattr` fallbacks for runner-specific fields

## Recommended Actions

1. **[Medium]** Add guard for BGData when negated_constraint_map is empty (or skip creation)
2. **[Medium]** Add type annotations to `get_descriptions_for(ids)` and `get_bg_data()`
3. **[Low]** Consider extracting OracleTaskPreparation to separate module if fm_oracle_model.py grows further

## Metrics

- Type Coverage: ~85% (minor gaps in new methods)
- Test Coverage: All 302 tests pass (2 unrelated failures from missing data file)
- Linting Issues: 2 (missing type annotations)

## Unresolved Questions

1. Should `from_fm_data()` factory skip BGData creation entirely (since it lacks negation and ConGen never uses that path)? This would surface misuse early via RuntimeError.
