# Brainstorm: Merge ExampleProvider + QueryGenerator → QueryProvider

**Date**: 2026-02-28
**Status**: Agreed

## Problem Statement

`ExampleProvider` doesn't match the paper's method:
- Currently returns next shuffled example blindly (no condition checks)
- Paper requires: query ∈ sol(C_L ∪ BG) that violates ≥1 constraint in B
- `QueryGenerator` already matches paper via SAT solving
- Both serve same purpose: provide next query to ask oracle

## Evaluated Approaches

### Option A: Filter ExampleProvider only (keep separate classes)
- **Pro**: Minimal change, preserves existing structure
- **Con**: Two classes doing the same thing with different sources; mode dispatch in QuAcq.learn() remains complex

### Option B: Single class, two strategies (CHOSEN)
- **Pro**: KISS, eliminates redundancy, clean API, matches paper
- **Con**: Slightly larger class (but replaces two classes + mode dispatch)

### Option C: Strategy pattern (ABC + implementations)
- **Pro**: Extensible, testable in isolation
- **Con**: More classes than needed (YAGNI), over-engineered for two strategies

## Agreed Solution

### 1. Merge ExampleProvider + QueryGenerator → `QueryProvider`

Single class with optional pool + SAT generation:

```python
class QueryProvider:
    def __init__(self, solver_name='glucose4', pool=None, seed=None, profiler=None):
        # Optional pool (shuffled), SAT solver config

    def generate_from_pool(self, remaining_bias, kb_clauses, bg_clauses,
                           constraint_clauses, feature_ids) -> Tuple[Optional[Dict], Optional[int]]:
        """Paper-filtered pool: satisfies C_L ∪ BG AND violates ≥1 c ∈ B."""

    def generate_from_sat(self, remaining_bias, learned_kb, kb_clauses,
                          negated_clauses, bg_clauses, feature_ids,
                          id_to_feature, constraint_clauses) -> Tuple[Optional[Dict], Optional[int]]:
        """SAT-based: current QueryGenerator.generate() logic."""

    def generate(self, ...) -> Tuple[Optional[Dict], Optional[int]]:
        """Pool first, then SAT fallback."""
        result = self.generate_from_pool(...)
        if result[0] is not None:
            return result
        return self.generate_from_sat(...)

    @property
    def pool_exhausted(self) -> bool: ...

    @property
    def pool_remaining(self) -> int: ...
```

**Mode mapping in QuAcq.learn():**

| Mode | Method Called | Behavior |
|------|-------------|----------|
| `oracle` | `generate_from_sat()` | SAT only |
| `example_only` | `generate_from_pool()` | Pool only (stops when exhausted) |
| `example_first` | `generate()` | Pool first → SAT fallback |

### 2. Remove `_narrow_with_pool` from FindC

- Paper's Algorithm 3 does NOT use pool in FindC
- FindC only uses `DiscriminatingGenerator` (generates e' ∈ sol(BG + C_L[Y]) s.t. e' |= c_i, e' |/= c_j)
- Removing `_narrow_with_pool` simplifies FindC and matches paper exactly

### 3. Keep DiscriminatingGenerator separate

- Different condition: separate c_i from c_j (not "violate any c ∈ B")
- Different inputs: two constraint IDs + scope + C_L[Y]
- Different purpose: used exclusively in FindC
- Shares SAT infrastructure via sat_utils.py

### 4. Pool Filtering Condition

Full paper condition with SAT check:
```python
def _try_from_pool(self, remaining_bias, kb_clauses, bg_clauses,
                   constraint_clauses, feature_ids):
    while self._pool_index < len(self._pool):
        e = self._pool[self._pool_index]
        self._pool_index += 1

        # Condition 1: satisfies C_L ∪ BG (SAT check)
        assignment = config_to_assumptions(e, feature_ids)
        if not self._satisfies_formula(kb_clauses + bg_clauses, assignment):
            continue

        # Condition 2: violates ≥1 constraint in remaining_bias
        for c_id in remaining_bias:
            clauses = constraint_clauses.get(c_id)
            if clauses and violates_clauses(clauses, assignment):
                return (e, c_id)
    return (None, None)
```

## Impact Analysis

### Files to modify:
- `conacq/example_generators/query_generator.py` → becomes `query_provider.py`
- `conacq/example_generators/example_provider.py` → DELETE
- `conacq/example_generators/__init__.py` → update exports
- `conacq/algorithms/quacq/quacq.py` → simplify mode dispatch
- `conacq/algorithms/quacq/findc.py` → remove `_narrow_with_pool`, remove ExampleProvider usage
- `conacq/runners/quacq_runner.py` → construct QueryProvider instead of separate classes
- `tests/test_quacq.py` → update tests

### Breaking changes:
- ExampleProvider class removed
- QueryGenerator class renamed to QueryProvider
- QuAcq constructor: `query_generator` + `example_provider` → `query_provider`
- QuAcq.for_oracle() and QuAcq.for_examples() factory methods updated
- FindC signature: remove `example_provider` parameter

## Risk Assessment

- **Low risk**: Internal refactoring, no external API exposure
- **Performance**: SAT check per pool example adds overhead, but correctness matters more
- **Pool depletion**: With filtering, more pool examples will be skipped → `example_only` mode may converge less often
- **Test coverage**: Existing tests validate behavior; need to add pool-filtering tests

## Success Criteria

- [ ] QueryProvider replaces both ExampleProvider and QueryGenerator
- [ ] Pool examples filtered by paper's condition (satisfies C_L ∪ BG, violates ≥1 bias)
- [ ] FindC uses DiscriminatingGenerator only (no pool)
- [ ] All three modes (oracle, example_only, example_first) work correctly
- [ ] All existing tests pass (updated for new API)
- [ ] Matches paper's Algorithm 1 for query generation
