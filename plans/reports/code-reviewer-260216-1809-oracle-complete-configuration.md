# Code Review: Oracle `complete_configuration()` Refactoring

**Reviewer**: code-reviewer-a99004c
**Date**: 2026-02-16
**Commit**: f0afaf9 (HEAD)
**Scope**: Oracle ABC extension + example generator simplification

---

## Scope

- **Files reviewed**: 6
- **LOC delta**: -65 (net reduction)
- **Focus**: Oracle interface extension, behavioral equivalence, type safety

| File | LOC | Change |
|------|-----|--------|
| `acqmss/oracle/base.py` | 67 | +21 (two new abstract methods) |
| `acqmss/oracle/fm_oracle.py` | 184 | +34 (implementation + helper) |
| `acqmss/oracle/cached.py` | 91 | +8 (delegation) |
| `acqmss/oracle/user_prompt.py` | 105 | +8 (NotImplementedError stubs) |
| `acqmss/example_generators/base.py` | 77 | -30 (SAT solver removal) |
| `acqmss/example_generators/feature_frequency.py` | 280 | -27 (SAT solver removal) |

---

## Overall Assessment

Clean, well-executed refactoring. Moves SAT-solver-based configuration completion from example generators into `Oracle.complete_configuration()`, establishing a single source of truth. Code compiles, imports resolve, ABC enforcement verified, and 299/301 tests pass (2 pre-existing failures from missing data file).

---

## Critical Issues

None.

---

## High Priority

### H1. Hardcoded solver name `'glucose4'` in `complete_configuration()`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, line 119

`FeatureModelOracle.__init__` accepts `solver_name` parameter (stored as `self.solver_name`), but `complete_configuration()` hardcodes `Solver(name='glucose4')` instead of using `self.solver_name`.

```python
# Current (line 119):
solver = Solver(name='glucose4')

# Suggested:
solver = Solver(name=self.solver_name)
```

**Impact**: If a user instantiates `FeatureModelOracle(fm_path, solver_name='cadical153')`, the main checker uses cadical but `complete_configuration()` silently uses glucose4. Low practical risk today since glucose4 is the default everywhere, but violates consistency.

### H2. Solver created per call -- no reuse or caching

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, lines 119-130

Each `complete_configuration()` call creates a new Solver, loads all clauses, solves, then deletes. For generators calling this in tight loops (e.g., FF generator with `max_examples * 10` attempts), this is ~O(n) solver instantiations.

**Impact**: Performance regression for large FMs. The original code in generators also did this per-call, so this is not a new issue -- but now that the method is centralized, it is a good opportunity to optimize later.

**Suggestion**: Consider caching the solver or reusing clauses. Not blocking for this PR, but worth a follow-up TODO.

---

## Medium Priority

### M1. Fallback silently ignores requested partial assignment

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py`, lines 126-128

When the partial assignment is unsatisfiable, the fallback `solver.solve()` (no assumptions) returns a configuration that may contradict the requested partial. For example, `complete_configuration({root: False})` returns a config with `root=True`.

This matches the original generator behavior -- the old code had the same fallback pattern. However, the ABC docstring says "Complete a partial configuration to a full valid one", which could mislead callers into assuming the partial is always respected.

**Suggestion**: Add a note to the docstring:

```python
"""Complete a partial configuration to a full valid one.

Note: If no valid completion exists for the given partial, falls back to
returning any valid configuration (ignoring the partial constraints).
Returns None only if no valid configuration exists at all.
"""
```

### M2. `feature_frequency.py` fallback behavior slightly changed

**Original**: Try all assumptions -> fallback to target-only assumption -> give up
**New**: Try full partial -> fallback to target-only partial (which internally also falls back to no-assumptions)

The new code effectively adds a third fallback layer (no-assumptions via `complete_configuration`'s internal fallback). This makes it slightly more likely to return a config that doesn't satisfy the target feature requirement. Functionally acceptable since the generator already handles non-coverage gracefully via its retry loop, but worth noting.

### M3. `get_cnf_clauses()` and `complete_configuration()` as abstract methods on Oracle ABC

These methods assume SAT/CNF-based oracle internals. `UserPromptOracle` correctly raises `NotImplementedError`, but this signals a potential Liskov Substitution Principle (LSP) concern. Any code accepting `Oracle` cannot safely call these methods without knowing the concrete type.

**Current mitigating factor**: Example generators only work with FM-based oracles in practice.

**Suggestion**: If the Oracle hierarchy grows, consider splitting into `SATOracle(Oracle)` ABC for CNF-aware oracles vs. the base `Oracle` for pure membership queries. Not blocking now.

---

## Low Priority

### L1. Import `List` type in `user_prompt.py`

The `List` import was added for the return type of `get_cnf_clauses()`, but the method just raises `NotImplementedError`. The import is correct and needed for type checker compliance.

### L2. `feature_frequency.py` line count at 280 (above 200 threshold)

Pre-existing issue. The coverage tracking logic accounts for most of the length. Not introduced by this change.

---

## Edge Cases Found

1. **Empty partial dict**: `complete_configuration({})` correctly returns a valid config (equivalent to `solver.solve()` with no assumptions). Verified via functional test.

2. **Unknown feature name**: `complete_configuration({'NONEXISTENT': True})` raises `KeyError` from `self._oracle_model.variables[name]`. This is acceptable behavior -- consistent with `is_valid()` which also raises `KeyError` for unknown features.

3. **Contradictory partial (root=False)**: Falls through to no-assumption fallback, returns valid config ignoring the partial. Documented in M1 above.

4. **UserPromptOracle + ExampleGenerator**: If a `UserPromptOracle` is passed to any `ExampleGenerator`, calling `_generate_valid_config()` will raise `NotImplementedError`. This is correct -- example generators require SAT-capable oracles.

---

## Positive Observations

1. **Net code reduction**: -65 lines. SAT solver logic consolidated into one location.
2. **Clean separation of concerns**: Example generators no longer import `pysat.solvers.Solver`.
3. **Proper resource management**: `try/finally/solver.delete()` pattern maintained.
4. **Helper extraction**: `_model_to_config()` eliminates duplicated model-to-dict conversion.
5. **Type annotations**: All new methods properly typed with `Optional`, `Dict`, `List`.
6. **CachedOracle delegation**: Correctly passes through without caching (correct -- completion results vary due to solver non-determinism).

---

## Recommended Actions

1. **[H1]** Use `self.solver_name` instead of hardcoded `'glucose4'` in `complete_configuration()` -- quick fix, high correctness value.
2. **[M1]** Update docstring to clarify fallback behavior.
3. **[M2]** No code change needed; behavioral difference is minor and well-handled by retry loops.
4. **[H2]** Consider solver reuse as follow-up optimization (not blocking).

---

## Metrics

- **Type Coverage**: 100% on new/modified public APIs
- **Test Results**: 299 passed, 2 failed (pre-existing missing data file), 2 warnings (pre-existing)
- **ABC Compliance**: All 3 subclasses implement both new abstract methods
- **Linting Issues**: 0 new

---

## Unresolved Questions

1. Should `complete_configuration()` accept a `solver_name` parameter for per-call override, or is `self.solver_name` sufficient?
2. Is the silent fallback-to-any-valid-config the desired behavior, or should it return `None` when the partial assignment is unsatisfiable (more honest to callers but breaks current generator flow)?
