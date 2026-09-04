# Phase 4: Remove add_clause/add_assumption from Checker

## Context Links

- Checker: `explanation/operations/algorithms/checker.py`
- Phases 1-3 must be complete before this phase

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Remove `add_clause()` and `add_assumption()` from `ConsistencyChecker` ABC and all three implementations. These methods are no longer called anywhere after phases 1-3.

## Key Insights

- After phases 1-3, no code calls `add_clause` or `add_assumption` on any checker
- Removing them makes checker a pure read-only query interface (immutable after construction)
- This is the payoff of the refactoring: cleaner, safer API

## Requirements

### Functional
- Remove `add_clause()` from `ConsistencyChecker`, `IncrementalPySATChecker`, `NonIncrementalPySATChecker`, `SAT4JChecker`
- Remove `add_assumption()` from all four classes

### Non-functional
- No behavioral change (methods were already unused after phases 1-3)

## Architecture

```
Before: ConsistencyChecker has is_consistent, is_consistent_test_cases, copy, cleanup,
        add_clause, add_assumption
After:  ConsistencyChecker has is_consistent, is_consistent_test_cases, copy, cleanup
```

## Related Code Files

- **Modify**: `explanation/operations/algorithms/checker.py`

## Implementation Steps

### Step 1: Verify no remaining callers

Before removing, confirm no code calls these methods:

```bash
PYTHONPATH=. grep -rn "add_clause\|add_assumption" acqmss/ explanation/ apps/ tests/ --include="*.py"
```

Expected: only hits in `checker.py` itself (the method definitions). If any other file still calls them, fix that file first.

### Step 2: Remove from `ConsistencyChecker` base class

Delete these two methods (lines 155-165 in current file):

```python
    def add_clause(self, clause: List[int]) -> None:
        """Add a clause to the knowledge base.

        Incremental: adds to live solver + set_kb.
        Non-incremental: adds to set_kb only (next fresh solver gets it).
        """
        pass

    def add_assumption(self, assumption_id: int) -> None:
        """Register a new assumption ID."""
        pass
```

### Step 3: Remove from `IncrementalPySATChecker`

Delete these two methods (lines 236-243):

```python
    def add_clause(self, clause: List[int]) -> None:
        """Add a clause to the live solver and set_kb."""
        self.solver.add_clause(clause)
        self.set_kb.append(clause)

    def add_assumption(self, assumption_id: int) -> None:
        """Register a new assumption ID."""
        self.assumptions.append(assumption_id)
```

### Step 4: Remove from `NonIncrementalPySATChecker`

Delete these two methods (lines 328-334):

```python
    def add_clause(self, clause: List[int]) -> None:
        """Add a clause to set_kb (next fresh solver gets it)."""
        self.set_kb.append(clause)

    def add_assumption(self, assumption_id: int) -> None:
        """Register a new assumption ID."""
        self.assumptions.append(assumption_id)
```

### Step 5: Remove from `SAT4JChecker`

Delete these two methods (lines 431-437):

```python
    def add_clause(self, clause: List[int]) -> None:
        """Add a clause to set_kb."""
        self.set_kb.append(clause)

    def add_assumption(self, assumption_id: int) -> None:
        """Register a new assumption ID."""
        self.assumptions.append(assumption_id)
```

### Step 6: Update module docstring

Update the module docstring at top of `checker.py` to remove any mention of `add_clause` or `add_assumption`. The checker is now a read-only query interface after construction.

## Todo List

- [ ] Verify no remaining callers via grep
- [ ] Remove `add_clause` and `add_assumption` from `ConsistencyChecker`
- [ ] Remove from `IncrementalPySATChecker`
- [ ] Remove from `NonIncrementalPySATChecker`
- [ ] Remove from `SAT4JChecker`
- [ ] Update module docstring

## Success Criteria

- `add_clause` and `add_assumption` do not exist anywhere in `checker.py`
- No code anywhere in the codebase calls these methods
- All tests pass

## Risk Assessment

- **Low risk**: Methods are already unused after phases 1-3
- **Mitigation**: Grep verification in step 1 ensures no remaining callers
- If any external/test code calls them, those must be updated first

## Security Considerations

None -- removing dead code improves maintainability.

## Next Steps

Phase 5: Update tests to match new flow (tests create GenerateNE before CONGEN).
