# Phase 2: Semantic Equivalence Check

## Context

- Parent plan: [plan.md](plan.md)
- Dependencies: None (independent of Phase 1)
- Blocks: Phase 3 (progressive evaluation uses semantic check at each checkpoint)

## Overview

- **Date**: 2026-02-26
- **Priority**: P1
- **Status**: pending
- **Effort**: 2h

New module implementing SAT-based semantic equivalence: KB equiv C_T iff (KB entails C_T) AND (C_T entails KB). For each clause c in target set, check whether source_clauses union BG union neg(c) is UNSAT. If UNSAT for all clauses, entailment holds.

Integrated into `KBComparator` as a new `SEMANTIC` strategy.

## Key Insights

- **Entailment check**: `KB entails c` iff `SAT(KB + neg(c))` is UNSAT.
- **Negate clause** `[a, b]` -> add unit clauses `[[-a], [-b]]` (De Morgan: neg(a OR b) = (NOT a) AND (NOT b)).
- **Existing infrastructure**: `pysat.solvers.Solver` available; `IncrementalPySATChecker` available but overkill here since we need fresh formulas per clause check.
- **bg_clauses** must be included in both directions: KB includes BG (root constraint), C_T already includes root in `GroundTruthData.clause_set`.
- **ne_* constraints** skipped in existing strategies; skip them here too for consistency.
- **Performance**: For each direction, O(|target_set|) SAT calls. Each call is fast (small formulas). For FM with ~50 clauses, this is negligible.

## Requirements

### Functional
1. `SemanticEquivalenceChecker` class with `check_equivalence()` returning both-direction results
2. `check_kb_entails_ct()` — does learned KB entail every clause in C_T?
3. `check_ct_entails_kb()` — does C_T entail every clause in KB?
4. Report unentailed clauses in each direction (diagnostic info)
5. Integrate as `ComparationStrategy.SEMANTIC` in `KBComparator`

### Non-functional
- Use `pysat.solvers.Solver` directly (lightweight, no checker model overhead)
- Each SAT call uses context manager (`with Solver(...) as s`) for cleanup
- Thread-safe (no shared mutable state)

## Architecture

```
SemanticEquivalenceChecker
    |
    +--- check_kb_entails_ct()
    |       For each c in C_T:
    |           SAT(KB_clauses + BG + neg(c)) ?
    |           UNSAT -> entailed; SAT -> not entailed
    |
    +--- check_ct_entails_kb()
    |       For each c in KB_clauses:
    |           SAT(CT_clauses + neg(c)) ?
    |           UNSAT -> entailed; SAT -> not entailed
    |
    +--- check_equivalence()
            Both directions -> SemanticResult
```

## Related Code Files

### Create
| File | Description |
|------|-------------|
| `conacq/eval/semantic_equivalence.py` | `SemanticEquivalenceChecker` + `SemanticResult` (~100 lines) |
| `tests/test_semantic_equivalence.py` | Unit tests |

### Modify
| File | Change |
|------|--------|
| `conacq/eval/kb_comparator.py` | Add `SEMANTIC` to `ComparationStrategy` enum; add `_compare_by_semantic()` method |
| `conacq/eval/__init__.py` | Export `SemanticEquivalenceChecker`, `SemanticResult` |

## Implementation Steps

### Step 1: Create `SemanticResult` dataclass

In `conacq/eval/semantic_equivalence.py`:

```python
@dataclass
class SemanticResult:
    """Result of semantic equivalence check.

    Attributes:
        kb_entails_ct: True if KB entails every clause in C_T
        ct_entails_kb: True if C_T entails every clause in KB
        is_equivalent: True if both directions hold
        unentailed_ct: C_T clauses NOT entailed by KB (diagnostic)
        unentailed_kb: KB clauses NOT entailed by C_T (diagnostic)
        n_ct_checked: Total C_T clauses checked
        n_kb_checked: Total KB clauses checked
    """
    kb_entails_ct: bool
    ct_entails_kb: bool
    is_equivalent: bool
    unentailed_ct: List[Tuple[int, ...]]
    unentailed_kb: List[Tuple[int, ...]]
    n_ct_checked: int
    n_kb_checked: int
```

Add `to_dict()` for JSON serialization.

### Step 2: Create `SemanticEquivalenceChecker`

```python
class SemanticEquivalenceChecker:
    """SAT-based semantic equivalence checker.

    Checks KB equiv C_T via bidirectional entailment:
    - KB entails C_T: for each c in C_T, KB + BG + neg(c) is UNSAT
    - C_T entails KB: for each c in KB, C_T + neg(c) is UNSAT
    """

    def __init__(
        self,
        kb_clauses: List[List[int]],
        ct_clauses: List[List[int]],
        bg_clauses: List[List[int]] = None,
        solver_name: str = 'glucose3'
    ):
        self.kb_clauses = kb_clauses
        self.ct_clauses = ct_clauses
        self.bg_clauses = bg_clauses or []
        self.solver_name = solver_name
```

### Step 3: Implement `_check_entails()`

Private helper used by both directions:

```python
def _check_entails(
    self,
    source_clauses: List[List[int]],
    target_clauses: List[List[int]]
) -> Tuple[bool, List[Tuple[int, ...]]]:
    """Check if source entails every clause in target.

    For each clause c in target:
        negated = [[-lit] for lit in c]
        formula = source + negated
        if SAT(formula) -> c is NOT entailed

    Returns:
        (all_entailed, list_of_unentailed_clauses)
    """
    unentailed = []
    for clause in target_clauses:
        negated = [[-lit] for lit in clause]
        formula = source_clauses + negated
        with Solver(name=self.solver_name, bootstrap_with=formula) as solver:
            if solver.solve():  # SAT -> not entailed
                unentailed.append(tuple(sorted(clause)))
    return len(unentailed) == 0, unentailed
```

### Step 4: Implement public methods

<!-- Updated: Validation Session 1 - BG included in source only, excluded from entailment targets -->
```python
def check_kb_entails_ct(self):
    """Does KB (+ BG) entail every clause in C_T?"""
    source = self.kb_clauses + self.bg_clauses  # BG in source
    return self._check_entails(source, self.ct_clauses)

def check_ct_entails_kb(self):
    """Does C_T entail every clause in KB? (BG excluded from targets)"""
    # BG NOT in target — only check KB-specific clauses
    return self._check_entails(self.ct_clauses, self.kb_clauses)

def check_equivalence(self) -> SemanticResult:
    """Full bidirectional equivalence check."""
    kb_ok, unentailed_ct = self.check_kb_entails_ct()
    ct_ok, unentailed_kb = self.check_ct_entails_kb()
    return SemanticResult(
        kb_entails_ct=kb_ok,
        ct_entails_kb=ct_ok,
        is_equivalent=kb_ok and ct_ok,
        unentailed_ct=unentailed_ct,
        unentailed_kb=unentailed_kb,
        n_ct_checked=len(self.ct_clauses),
        n_kb_checked=len(self.kb_clauses) + len(self.bg_clauses),
    )
```

### Step 5: Integrate into `KBComparator`

In `conacq/eval/kb_comparator.py`:

1. Add to `ComparationStrategy` enum:
   ```python
   SEMANTIC = "semantic"  # SAT-based semantic equivalence
   ```

2. Update `compare()` to handle new strategy:
   ```python
   elif strategy == ComparationStrategy.SEMANTIC:
       return self._compare_by_semantic(result)
   ```

3. Add `_compare_by_semantic()` method:
   - Resolve KB clauses from bias (same as `_compare_by_clause`)
   - Create `SemanticEquivalenceChecker(kb_clause_lists, ct_clause_lists, bg_clauses)`
   - Call `check_equivalence()`
   - Map `SemanticResult` to `ComparationResult` (kb_entails_ct count as recall proxy, ct_entails_kb as precision proxy)

### Step 6: Update `__init__.py`

Add exports:
```python
from .semantic_equivalence import SemanticEquivalenceChecker, SemanticResult
```

Add to `__all__`.

### Step 7: Unit tests

`tests/test_semantic_equivalence.py`:

1. **Equivalent sets**: KB == C_T -> both directions True
2. **KB subset of C_T**: KB entails C_T partially, C_T entails KB fully
3. **KB superset of C_T**: KB entails C_T fully, C_T entails KB partially
4. **Disjoint sets**: neither direction holds
5. **Empty KB**: nothing entails C_T (except tautologies)
6. **BG clauses included**: BG contributes to entailment
7. **Negation correctness**: verify `[a, b]` negated as `[[-a], [-b]]`
8. **to_dict() serialization**: verify JSON structure

## Todo List

- [ ] Create `conacq/eval/semantic_equivalence.py` with `SemanticResult` dataclass
- [ ] Implement `SemanticEquivalenceChecker.__init__()`
- [ ] Implement `_check_entails()` private helper
- [ ] Implement `check_kb_entails_ct()` and `check_ct_entails_kb()`
- [ ] Implement `check_equivalence()` returning `SemanticResult`
- [ ] Implement `SemanticResult.to_dict()`
- [ ] Add `SEMANTIC` to `ComparationStrategy` enum in `kb_comparator.py`
- [ ] Add `_compare_by_semantic()` to `KBComparator`
- [ ] Update `conacq/eval/__init__.py` exports
- [ ] Create `tests/test_semantic_equivalence.py`
- [ ] Run `PYTHONPATH=. pytest tests/test_semantic_equivalence.py -v`
- [ ] Run full test suite

## Success Criteria

1. `SemanticEquivalenceChecker` correctly identifies equivalent, subset, superset, and disjoint KB/C_T pairs
2. `KBComparator.compare(result, ComparationStrategy.SEMANTIC)` returns valid `ComparationResult`
3. All existing tests pass unchanged
4. New unit tests cover all edge cases

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| SAT calls slow for large C_T | Medium | Each call is a small formula; for FMs with <200 clauses, total time < 1s. Log timing. Add optional `max_clauses` parameter if needed. |
| Variable ID mismatch between KB and C_T | High | Both use same `FmToDiagPysat` transform with flamapy tree traversal order. Verify in tests with real FM. |
| BG clauses double-counted | Low | C_T from `GroundTruthData.clause_set` already includes root clause. KB's bg_clauses also include root. This is fine for entailment (adding redundant clauses doesn't affect SAT). |
| ne_* constraints included | Low | Filter before building clause lists, consistent with existing strategies. |

## Next Steps

After completion:
- Phase 3 uses `SemanticEquivalenceChecker` at each checkpoint to measure convergence
- Phase 4 includes semantic results in output JSON
