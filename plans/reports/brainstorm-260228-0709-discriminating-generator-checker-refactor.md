# Brainstorm: DiscriminatingGenerator → ConsistencyChecker DI

**Date**: 2026-02-28 07:09
**Status**: Agreed

---

## Problem Statement

`DiscriminatingGenerator` uses raw PySAT `Solver` directly while `FindScope`/`FindC` use injected `ConsistencyChecker`. This creates inconsistency in the DI pattern and duplicates solver management logic.

## Evaluated Approaches

### A. Full DI (like FindScope/FindC) ✅ CHOSEN
- Constructor: `__init__(checker, model, root_assumption)`
- `generate()` builds assumption list, calls `checker.is_consistent()` + `get_model()`
- Shares same solver instance → no duplicate allocation
- **Pro**: Consistent DI pattern, profiler integration, solver backend swappable
- **Pro**: Eliminates raw PySAT dependency in DiscriminatingGenerator
- **Con**: Slightly different mental model (assumptions vs raw clauses)

### B. New checker instance — REJECTED
- Separate ConsistencyChecker for generator
- **Con**: Doubles memory/solver resources, not needed

### C. Hybrid — REJECTED
- Mix checker + raw scope filtering
- **Con**: Half-measure, inconsistent pattern

## Final Recommended Solution

### New Constructor
```python
class DiscriminatingGenerator:
    def __init__(self, checker: ConsistencyChecker, model: QuAcqModel,
                 root_assumption: int):
        self.checker = checker
        self.model = model
        self.root_assumption = root_assumption
```

### New generate() Logic
```python
def generate(self, c_i, c_j, learned_kb, scope) -> Optional[Dict[str, bool]]:
    # 1. Build C_L[Y]: learned constraints in scope
    cl_y_assumptions = [c_id for c_id in learned_kb
                        if self.model.get_constraint_vars(c_id).issubset(scope)]

    # 2. Get negated assumption for c_j
    negation_map = self.model.get_negation_map()
    neg_j = negation_map.get(c_j)
    if neg_j is None:
        return None

    # 3. Build set_c: root + C_L[Y] + c_i + neg(c_j)
    set_c = [self.root_assumption] + cl_y_assumptions + [c_i, neg_j]

    # 4. SAT check
    if self.checker.is_consistent(set_c):
        return self.model.model_to_config(self.checker.get_model())
    return None
```

### New QuAcqModel Method
```python
def get_constraint_vars(self, assumption_id: int) -> Set[str]:
    """Get feature names for constraint by assumption ID."""
    task = self._require_task()
    clauses = task.constraint_clauses.get(assumption_id, [])
    return {task.id_to_feature[abs(lit)]
            for clause in clauses for lit in clause
            if abs(lit) in task.id_to_feature}
```

## Changes Required

### Files to Modify

1. **`quacq_model.py`** — Add `get_constraint_vars(assumption_id)` method
2. **`discriminating_generator.py`** — Rewrite with DI pattern (checker + model + root_assumption)
3. **`quacq_runner.py`** — Update 2 construction sites (lines 236, 265) to pass `checker, model, root_assumption`
4. **`quacq/__init__.py`** — Update example construction (line 29)
5. **`tests/test_quacq.py`** — Update test DiscriminatingGenerator creation

### Files NOT Changed

- `findc.py` — caller of `generate()` signature unchanged (4 args: c_i, c_j, learned_kb, scope)
- `findscope.py` — no relation
- `checker.py` — ConsistencyChecker interface unchanged

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| root_assumption | Constructor (not per-call) | Fixed per QuAcq session |
| model_to_config | Reuse model method | DRY — eliminate private _model_to_config() |
| Scope data | model.get_constraint_vars() | Cleaner DI, no raw data dicts |
| Checker instance | Same as FindScope/FindC | Share solver, no duplication |

## Risk Assessment

- **Low risk**: `generate()` return type unchanged (`Optional[Dict[str, bool]]`)
- **Low risk**: `FindC._narrow_with_generator()` call site unchanged
- **Medium risk**: Solver behavior difference — raw solver vs assumption-based may produce different models (both correct, just different valid assignments). Tests should verify functional equivalence.

## Success Criteria

- [ ] All existing tests pass
- [ ] DiscriminatingGenerator uses checker.is_consistent() + get_model()
- [ ] No raw PySAT import in discriminating_generator.py
- [ ] DI pattern consistent with FindScope/FindC

## Next Steps

1. Add `get_constraint_vars()` to QuAcqModel
2. Rewrite DiscriminatingGenerator class
3. Update all construction sites (runner, __init__, tests)
4. Run tests to verify functional equivalence
