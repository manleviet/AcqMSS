# Documentation Update: DiscriminatingGenerator DI Refactor

**Date**: 2026-02-28 (commit 260228)
**Changes**: Updated docs to reflect DI pattern refactor of DiscriminatingGenerator

## Summary

DiscriminatingGenerator was refactored to use Dependency Injection (DI) pattern, replacing raw PySAT Solver calls with injected ConsistencyChecker. All documentation code examples and references have been updated to reflect the new constructor signature and integration pattern.

## Changes Made

### 1. **docs/quacq.md** (Line 364)

**Before**:
```python
discrim_gen = DiscriminatingGenerator()
```

**After**:
```python
# DiscriminatingGenerator with injected checker + model (NEW - commit 260228)
discrim_gen = DiscriminatingGenerator(checker, model, model.task.set_b[0])
```

**Context**: Oracle-based learning example. Now shows correct DI parameters: ConsistencyChecker, QuAcqModel, and root BG assumption ID.

---

### 2. **docs/system-architecture.md** (Line 109)

**Before**:
```python
discrim_gen = DiscriminatingGenerator()
```

**After**:
```python
# DiscriminatingGenerator with injected checker + model (NEW - commit 260228)
discrim_gen = DiscriminatingGenerator(checker, model, model.task.set_b[0])
```

**Context**: Core API example. Now shows correct DI pattern matching implementation.

---

### 3. **docs/code-standards.md** (Lines 197-204)

**Updated QuAcqRunner.run() example**:

**Before**:
```python
def run(self, positive_examples=None, negative_examples=None, mode='oracle'):
    """Learn constraints interactively, resolve names."""
    query_prov = QueryProvider()
    discrim_gen = DiscriminatingGenerator()
    quacq = QuAcq.for_oracle(self.oracle, query_prov, discrim_gen)
```

**After**:
```python
def run(self, positive_examples=None, negative_examples=None, mode='oracle'):
    """Learn constraints interactively, resolve names."""
    # Create checker from model (DI pattern)
    from explanation.operations.algorithms.checker import CheckerFactory
    checker = CheckerFactory.create_from_model(self.model)

    # Inject checker + model into query provider
    query_prov = QueryProvider(checker=checker, model=self.model)

    # Inject checker + model + root_assumption into DiscriminatingGenerator (NEW - commit 260228)
    discrim_gen = DiscriminatingGenerator(checker, self.model, self.model.task.set_b[0])

    quacq = QuAcq.for_oracle(checker, self.oracle, query_prov, discrim_gen)
```

**Changes**:
- Shows full CheckerFactory integration (previously omitted)
- Demonstrates QueryProvider construction with checker + model injection
- Shows correct DiscriminatingGenerator constructor with all required parameters
- Updates QuAcq.for_oracle() call to include checker parameter

**Updated QuAcq.for_oracle() method signature** (Lines 300-305):

**Before**:
```python
def for_oracle(cls, oracle: Oracle, query_prov: QueryProvider,
               discrim_gen: DiscriminatingGenerator,
               profiler: AbstractProfiler = None) -> 'QuAcq':
```

**After**:
```python
def for_oracle(cls, checker: ConsistencyChecker, oracle: Oracle, query_prov: QueryProvider,
               discrim_gen: DiscriminatingGenerator,
               profiler: AbstractProfiler = None) -> 'QuAcq':
```

**Updated QuAcq.for_examples() method signature** (Lines 308-313):

**Before**:
```python
def for_examples(cls, oracle: Oracle, query_provider: QueryProvider,
                 discrim_gen: DiscriminatingGenerator = None,
                 profiler: AbstractProfiler = None) -> 'QuAcq':
```

**After**:
```python
def for_examples(cls, checker: ConsistencyChecker, oracle: Oracle, query_provider: QueryProvider,
                 discrim_gen: DiscriminatingGenerator = None,
                 profiler: AbstractProfiler = None) -> 'QuAcq':
```

---

## Implementation Details

### Constructor Pattern (commit 260228)

```python
class DiscriminatingGenerator:
    def __init__(self, checker: ConsistencyChecker, model, root_assumption: int) -> None:
        self.checker = checker
        self.model = model
        self.root_assumption = root_assumption

    def generate(self, c_i: int, c_j: int, learned_kb: List[int], scope: Set[str]) -> Optional[Dict]:
        """Find e' s.t. e' in sol(BG + C_L[Y]) and e' |= c_i and e' |/= c_j."""
        # C_L[Y]: learned constraints whose vars are in scope
        cl_y = [c_id for c_id in learned_kb if self.model.get_constraint_vars(c_id).issubset(scope)]

        # Get negated assumption for c_j
        negation_map = self.model.get_negation_map()
        neg_j = negation_map.get(c_j)

        # SAT: BG + C_L[Y] + c_i + neg(c_j)
        set_c = [self.root_assumption] + cl_y + [c_i, neg_j]

        if self.checker.is_consistent(set_c):
            return self.model.model_to_config(self.checker.get_model())
        return None
```

### Parameter Explanation

- **checker** (ConsistencyChecker): Injected SAT solver abstraction (Incremental or NonIncremental)
  - Used via `checker.is_consistent(set_c)` for SAT formula solving
  - Used via `checker.get_model()` for solution extraction
  - No longer accepts raw clause parameters or solver_name

- **model** (QuAcqModel): Injected model for:
  - `get_constraint_vars(assumption_id)` — Get variables in constraint
  - `get_negation_map()` — Get negated assumption IDs
  - `model_to_config(sat_model)` — Convert SAT assignment to feature config

- **root_assumption** (int): Root background constraint assumption ID
  - Enables SAT formulas to include BG clauses via assumptions
  - Extracted from `model.task.set_b[0]` (first BG assumption)

---

## Files Updated

| File | Lines | Change |
|------|-------|--------|
| docs/quacq.md | 364 | Constructor call + comment |
| docs/system-architecture.md | 109 | Constructor call + comment |
| docs/code-standards.md | 197-313 | QuAcqRunner example + factory signatures |

---

## Verification

All code examples now:
✓ Use correct DiscriminatingGenerator constructor with 3 parameters
✓ Show QueryProvider injection pattern with checker + model
✓ Demonstrate CheckerFactory integration
✓ Match actual implementation in conacq/algorithms/quacq/discriminating_generator.py
✓ Include commit reference (260228) for traceability

---

## Backward Compatibility

- No breaking changes to public APIs (examples only)
- Code examples are documentation, not importable modules
- Implementation verified against actual source code

---

## Related Files

- **Implementation**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/discriminating_generator.py`
- **Integration**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` (line 28)
- **Usage**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (for_oracle/for_examples factories)

---

## Summary of DI Refactor Benefits

1. **Decoupling**: DiscriminatingGenerator no longer depends on raw PySAT solver
2. **Testability**: Checker can be mocked for testing
3. **Flexibility**: Supports incremental/non-incremental solvers uniformly
4. **Consistency**: Matches FindScope/FindC DI patterns (oracle + checker + model)
5. **Safety**: Type hints clarify expected collaborators

