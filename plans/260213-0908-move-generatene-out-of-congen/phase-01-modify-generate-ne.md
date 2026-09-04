# Phase 1: Modify GenerateNE to Return Data Instead of Mutating Checker

## Context Links

- Source: `acqmss/algorithms/generate_ne.py`
- Checker: `explanation/operations/algorithms/checker.py`
- Architecture: `docs/system-architecture.md`

## Overview

- **Priority**: P1 (blocks all other phases)
- **Status**: completed
- **Description**: Make `GenerateNE.generate()` return new clauses and assumption IDs in `NEResult` instead of calling `checker.add_clause()`/`checker.add_assumption()`.

## Key Insights

- `GenerateNE` currently calls `checker.add_clause()` and `checker.add_assumption()` in a loop
- These mutations have NO EFFECT on subsequent QuickXPlain calls (assumption semantics guarantee this)
- GenerateNE only needs checker for `QuickXPlain.find_conflict()` (read-only)
- Solution: collect clauses/assumptions in lists, return them in `NEResult`

## Requirements

### Functional
- `NEResult` must include `new_clauses` and `new_assumptions` fields
- `generate()` must NOT call `checker.add_clause()` or `checker.add_assumption()`
- QuickXPlain usage unchanged (still passes `e_neg` and `set_bg`)

### Non-functional
- Backward-compatible `NEResult` (existing fields unchanged)
- No change to algorithm correctness

## Architecture

```
Before: GenerateNE(checker) -> mutates checker -> returns NEResult(ids, neg_map, literals)
After:  GenerateNE(checker) -> pure read -> returns NEResult(ids, neg_map, literals, new_clauses, new_assumptions)
```

## Related Code Files

- **Modify**: `acqmss/algorithms/generate_ne.py`

## Implementation Steps

### Step 1: Extend `NEResult` dataclass

Add two new fields to `NEResult`:

```python
@dataclass
class NEResult:
    """Result of NE generation."""
    assumption_ids: List[int]
    neg_map: Dict[int, int]
    original_literals: List[List[int]]
    new_clauses: List[List[int]] = field(default_factory=list)      # NEW
    new_assumptions: List[int] = field(default_factory=list)        # NEW
```

### Step 2: Modify `generate()` to collect data instead of mutating

Replace the mutation calls with list appends. Current code (lines 96-109):

```python
# CURRENT (mutates checker)
self.checker.add_clause([-assumption_id] + blocking_clause)
self.checker.add_assumption(assumption_id)
# ...
for lit in minimal_conflict:
    self.checker.add_clause([-neg_assumption_id, lit])
self.checker.add_assumption(neg_assumption_id)
```

Replace with:

```python
# NEW (collects data)
new_clauses.append([-assumption_id] + blocking_clause)
new_assumptions.append(assumption_id)
# ...
for lit in minimal_conflict:
    new_clauses.append([-neg_assumption_id, lit])
new_assumptions.append(neg_assumption_id)
```

Initialize `new_clauses = []` and `new_assumptions = []` at the top of the method, alongside `assumption_ids`, `neg_map`, `original_literals`.

### Step 3: Include collected data in returned `NEResult`

```python
return NEResult(
    assumption_ids=assumption_ids,
    neg_map=neg_map,
    original_literals=original_literals,
    new_clauses=new_clauses,           # NEW
    new_assumptions=new_assumptions     # NEW
)
```

### Step 4: Update module docstring

Remove reference to "uses checker.add_clause()/add_assumption()" from class and module docstrings. Replace with "returns new clauses and assumptions in NEResult".

## Todo List

- [ ] Add `new_clauses` and `new_assumptions` fields to `NEResult`
- [ ] Replace `checker.add_clause()` calls with `new_clauses.append()`
- [ ] Replace `checker.add_assumption()` calls with `new_assumptions.append()`
- [ ] Include new fields in returned `NEResult`
- [ ] Update docstrings (module, class, method)

## Success Criteria

- `GenerateNE.generate()` returns `NEResult` with populated `new_clauses` and `new_assumptions`
- Zero calls to `checker.add_clause()` or `checker.add_assumption()` in `generate_ne.py`
- `generate_from_examples()` still works (delegates to `generate()`)

## Risk Assessment

- **Low risk**: Pure data transformation, no algorithm logic changes
- **Mitigation**: Verify identical NE output by comparing assumption_ids and neg_map in tests

## Security Considerations

None -- internal refactoring only.

## Next Steps

Phase 2: Update `task.py` (add `set_ne` field) and `congen.py` (remove GenerateNE call, use `task.set_ne`).
