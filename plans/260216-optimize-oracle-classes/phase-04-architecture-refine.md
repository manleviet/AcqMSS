# Phase 4: Architecture Refinements

## Context Links

- [Class Internals](research/researcher-01-class-internals.md) — DRY violations, magic numbers
- [Callers & Dependencies](research/researcher-02-callers-dependencies.md) — with_configuration usage
- [fm_oracle_model.py](../../conacq/oracle/fm_oracle_model.py) — FMOracleModel + OracleTaskPreparation
- [test_oracle_model.py](../../tests/test_oracle_model.py) — tests for with_configuration

## Overview

- **Priority**: Medium
- **Status**: complete
- **Effort**: 30m
- **Description**: Consolidate the DRY violation between `with_configuration()` and `OracleTaskPreparation` for `set_c` computation, replace magic numbers with named constants, and consider separating `OneShotModel` to its own file (given the 200 LOC guideline).

## Key Insights

- **DRY violation**: `set_c` computation logic duplicated:
  - `OracleTaskPreparation.prepare()` line 232-233: `result.set_c = [result.assumptions[i] for i in range(0, model.start_id_assignments, step)]`
  - `with_configuration()` line 125-127: `set_c = [self._task.assumptions[i] for i in range(0, self.start_id_assignments, step)]` + appends active assumptions
- **Magic number**: `step = 2` appears in both locations — represents paired pos/neg assumptions per FM constraint
- **OneShotModel**: 18 LOC, lives in `fm_oracle_model.py` but is a completely separate concern (no shared state or methods with FMOracleModel). Could move to own file, but YAGNI — only 18 lines.
- **negated_constraint_map**: Researcher 01 flagged it as "unused dict" on FMOracleModel, but `prepare_kb()` in `explanation/models/task_preparation.py` reads it (line 271-283). It IS used. Keep it.

## Requirements

### Functional
- Extract `set_c` computation into a shared helper to eliminate DRY violation
- Replace magic `step = 2` with named constant
- Verify `negated_constraint_map` is correctly used (confirmed: used by `prepare_kb`)

### Non-Functional
- Maintain backward compatibility
- All tests pass unchanged

## Architecture

```
Before:
  FMOracleModel.with_configuration():
    step = 2  # magic number
    set_c = [assumptions[i] for i in range(0, start_id, step)]  # DRY violation
    set_c += active_assumptions

  OracleTaskPreparation.prepare():
    step = 2  # magic number
    result.set_c = [assumptions[i] for i in range(0, start_id, step)]  # DRY violation

After:
  # Named constant at module level
  _ASSUMPTION_PAIR_STRIDE = 2  # Each FM constraint has pos + neg assumption

  FMOracleModel._compute_base_set_c() -> List[int]:
    return [self._task.assumptions[i] for i in range(0, self.start_id_assignments, _ASSUMPTION_PAIR_STRIDE)]

  FMOracleModel.with_configuration():
    set_c = self._compute_base_set_c()
    set_c += active_assumptions

  OracleTaskPreparation.prepare():
    # Uses _ASSUMPTION_PAIR_STRIDE constant
    result.set_c = [result.assumptions[i] for i in range(0, model.start_id_assignments, _ASSUMPTION_PAIR_STRIDE)]
```

## Related Code Files

### Files to Modify
- `acqmss/oracle/fm_oracle_model.py` — add constant, extract helper, update both callsites

### Files Unchanged
- `acqmss/oracle/fm_oracle.py` — no changes
- `tests/test_oracle_model.py` — existing tests for `with_configuration` cover this

## Implementation Steps

### Step 1: Add named constant

At module level in `fm_oracle_model.py`, after imports:

```python
# Each FM constraint produces a pair of assumptions (original + negated),
# so we stride by 2 to select only original constraint assumptions for set_c.
_ASSUMPTION_PAIR_STRIDE = 2
```

### Step 2: Extract _compute_base_set_c() helper

Add method to FMOracleModel:

```python
def _compute_base_set_c(self) -> list:
    """Compute base set_c from FM constraint assumptions (excluding feature assignments).

    Returns assumption IDs for original (non-negated) FM constraints only,
    by striding through paired pos/neg assumptions.
    """
    return [self._task.assumptions[i]
            for i in range(0, self._start_id_assignments, _ASSUMPTION_PAIR_STRIDE)]
```

### Step 3: Update with_configuration()

```python
# BEFORE (lines 120-130):
active_assumptions = []
for feat, value in items:
    assumption = self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]
    active_assumptions.append(assumption)

step = 2
set_c = [self._task.assumptions[i] for i in range(0, self.start_id_assignments, step)]
set_c += active_assumptions

self._task.set_c = set_c
return set_c

# AFTER:
active_assumptions = []
for feat, value in items:
    assumption = self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]
    active_assumptions.append(assumption)

set_c = self._compute_base_set_c() + active_assumptions
self._task.set_c = set_c
return set_c
```

### Step 4: Update OracleTaskPreparation.prepare()

```python
# BEFORE (lines 231-233):
# Step 4: assign to set_c for consistency checks
step = 2
result.set_c = [result.assumptions[i] for i in range(0, model.start_id_assignments, step)]

# AFTER:
# Step 3: assign to set_c for consistency checks
result.set_c = [result.assumptions[i]
                for i in range(0, model.start_id_assignments, _ASSUMPTION_PAIR_STRIDE)]
```

Note: Step number fix from Phase 1 is included here for completeness, but if Phase 1 already ran, this line just uses the constant.

### Step 5: Evaluate OneShotModel separation (DECISION: SKIP)

OneShotModel is 18 LOC. Moving to separate file:
- Pro: cleaner separation of concerns
- Con: extra file for trivial class, more imports to manage

**Decision**: Keep in `fm_oracle_model.py`. After all phases, `fm_oracle_model.py` will be ~220 LOC (under 200 LOC guideline threshold). YAGNI applies — separate only if file exceeds guideline.

### Step 6: Verify negated_constraint_map usage

Confirmed: `negated_constraint_map` IS used. The `prepare_kb()` function in `explanation/models/task_preparation.py` (lines 271-283) reads it to create negated assumption-guarded clauses. The researcher's finding was incorrect — it's passed through `OracleTaskPreparation.prepare()` → `prepare_kb()`.

No action needed. Keep the attribute.

### Step 7: Run tests

```bash
PYTHONPATH=. pytest tests/test_oracle_model.py -v
```

Specifically verify `test_config_to_active_assumptions`, `test_checker_integration_sat`, and `test_checker_integration_unsat` — these exercise `with_configuration()`.

## Todo List

- [ ] Add `_ASSUMPTION_PAIR_STRIDE = 2` constant to fm_oracle_model.py
- [ ] Add `_compute_base_set_c()` method to FMOracleModel
- [ ] Update `with_configuration()` to use `_compute_base_set_c()`
- [ ] Update `OracleTaskPreparation.prepare()` to use `_ASSUMPTION_PAIR_STRIDE`
- [ ] Remove local `step = 2` from both methods
- [ ] Run tests — all pass (especially with_configuration tests)
- [ ] Verify no behavioral change in set_c computation

## Success Criteria

- Magic number `2` replaced with `_ASSUMPTION_PAIR_STRIDE` constant
- `set_c` base computation defined once in `_compute_base_set_c()`
- `with_configuration()` and `OracleTaskPreparation.prepare()` both use shared logic/constant
- All tests pass (test_oracle_model.py: 9 tests)
- fm_oracle_model.py ~220 LOC

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| set_c computation produces different results | Low | High | Tests cover both SAT and UNSAT cases with with_configuration |
| Off-by-one in stride | Low | High | Existing test_config_to_active_assumptions validates |
| Removing negated_constraint_map breaks prepare_kb | N/A | N/A | Confirmed it's used; keeping it |

## Security Considerations

None — internal logic refactor.

## Next Steps

- After all phases: run full test suite, update `code-standards.md` and `system-architecture.md` if method signatures changed (they shouldn't — public API preserved)
