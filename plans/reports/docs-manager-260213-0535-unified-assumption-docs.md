# Documentation Update Report: Unified Assumption-Based Solving

**Date**: 2026-02-13
**Scope**: Updated `docs/system-architecture.md`, `docs/code-standards.md`, and `docs/codebase-summary.md` to reflect unified assumption-based solving refactoring.

## Summary

Successfully updated documentation to reflect the major refactoring where all checker modes (Incremental, NonIncremental, SAT4J) now use identical assumption-based data representation (Dict[int, int] for neg_c_map, List[int] for all sets).

## Changes Made

### 1. docs/system-architecture.md

#### Updated Checker Implementations (Lines 265-326)

**Before**:
- NonIncrementalPySATChecker showed fresh solver per call without mentioning assumption-based data
- No unified representation described

**After**:
- `IncrementalPySATChecker`: Documents unified `set_kb` (CNF clauses) and `assumptions` (control literals)
- `NonIncrementalPySATChecker`: Explicitly states "Uses same assumption-based representation as IncrementalPySATChecker"
- Both implementations now show identical parameter signatures with `set_kb: List[List[int]]` and `assumptions: List[int]`
- Added docstring clarifying all checkers use unified assumption-based representation

#### Updated Non-Incremental Mode Description (Lines 658-676)

**Before**:
```python
checker = NonIncrementalPySATChecker(solver_factory, profiler=None)
```
Showed solver factory pattern without assumption details.

**After**:
```python
set_kb = [[1, -2, 3], [-1, 4]]  # CNF clauses with assumption literals
assumptions = [5, 6, 7]          # Assumption IDs that control constraints
checker = NonIncrementalPySATChecker(set_kb, assumptions, profiler=None)
```
Clearly shows assumption-based data initialization.

#### Updated CONGEN Learning Flow (Lines 521-551)

**Before**: Showed traditional E+/E-/NE processing without mentioning assumption IDs.

**After**:
- TaskPreparation step added showing unified representation
- Clarified all sets are assumption IDs: `set_c`, `set_tc`, `set_tv`, `set_b`
- Added note: "Mode-Agnostic Design: CONGEN, GenerateNE, and REDUCE contain no `if is_incremental` branching"
- Highlighted that only ConsistencyChecker implementation differs, not algorithms

#### Updated CONGENTask Documentation (Lines 196-203)

**Before**:
```python
class CONGENTask:
    self.set_kb: DiagnosisModel      # Set KB (bias)
    self.positive_examples: list     # E+
    self.negative_examples: list     # E-
```

**After**:
```python
class CONGENTask:  # ...unified assumption-based format...
    self.set_c: list[int]            # Bias constraint assumption IDs
    self.set_tc: list[int]           # Positive example (E+) assumption IDs
    self.set_tv: list[int]           # Negative example (E-) assumption IDs
    self.set_b: list[int]            # Background (BG) assumption IDs
    self.set_kb: list[list[int]]     # CNF clauses with assumption literals
    self.neg_c_map: Dict[int, int]   # Negation map: assumption_id → negated_id
```

### 2. docs/code-standards.md

#### Updated Dependency Injection Pattern (Lines 274-318)

**Before**: Showed only IncrementalPySATChecker usage, no mention of mode-agnosticism.

**After**:
- Added comprehensive example showing both checker modes
- Added docstring in `acquire()` method explicitly stating:
  > "Works identically with IncrementalPySATChecker or NonIncrementalPySATChecker (no is_incremental branching)"
- Updated benefits to emphasize mode-agnostic design and unified data representation
- Added note: "Both checkers use identical assumption-based data (set_kb, assumptions)"

### 3. docs/codebase-summary.md

#### Updated Checker Description (Line 111)

**Before**: `checker.py | 450 | ConsistencyChecker ABC + implementations (...)`

**After**: `ConsistencyChecker ABC + implementations (Incremental/NonIncremental both use assumption-based data)`

#### Updated Task Description (Line 22)

**Before**: `task.py | 106 | CONGENTask, IncrementalCONGENTask, NonIncrementalCONGENTask`

**After**: `task.py | 106 | CONGENTask hierarchy - unified assumption-based format for both modes`

#### Enhanced Critical Implementation Details (Lines 64-70)

**Before**: Only mentioned Feature ID Consistency.

**After**: Added second critical detail about unified assumption-based representation:
> "The `neg_c_map` is unified as `Dict[int, int]` mapping assumption IDs to their negation counterparts, used uniformly in REDUCE and other algorithms."

## Key Improvements

1. **Clarity on Unified Representation**: Documentation now explicitly states that Incremental and NonIncremental checkers use identical data structures (set_kb, assumptions, neg_c_map).

2. **Removal of Mode Branching**: Highlighted that CONGEN, GenerateNE, and REDUCE algorithms contain no `if is_incremental` branching, working identically regardless of checker type.

3. **Updated API Documentation**: NonIncrementalPySATChecker constructor now documented with correct parameters (set_kb, assumptions) instead of old solver_factory pattern.

4. **Assumption-Based Terminology**: Consistent use of "assumption IDs" and "assumption literals" throughout, making the data representation clear.

5. **Code Examples**: Updated concrete examples to match refactored code (e.g., TaskPreparation step in CONGEN flow).

## Files Updated

- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (5 edits)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` (1 edit)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` (3 edits)

## Verification

All documentation updates verified against current implementation in:
- `acqmss/algorithms/task.py` — CONGENTask structure
- `acqmss/algorithms/congen.py` — Mode-agnostic CONGEN implementation
- `explanation/operations/algorithms/checker.py` — Unified checker API

No inconsistencies found. Documentation accurately reflects refactored codebase.

## Unresolved Questions

None. The refactoring is complete and documentation is aligned with implementation.
