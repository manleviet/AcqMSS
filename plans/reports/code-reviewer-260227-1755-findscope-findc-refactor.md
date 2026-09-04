# Code Review: FindScope/FindC IJCAI 2013 Paper Alignment Refactoring

**Date**: 2026-02-27
**Scope**: FindScope/FindC oracle.is_valid() migration + DiscriminatingGenerator + OneShotModel removal
**Test Status**: 53 passed (test_quacq + test_oracle_model), 0 failures

---

## Scope

- **Files Modified**: findscope.py, findc.py, quacq.py, quacq_runner.py, fm_oracle_model.py, oracle/__init__.py, quacq/__init__.py, test_oracle_model.py, test_quacq.py
- **Files Created**: discriminating_generator.py (~65 LOC)
- **Files Deleted**: OneShotModel class (fm_oracle_model.py lines 272-290), TestOneShotModel class
- **LOC Delta**: ~65 added (generator), ~120 deleted (5 methods in quacq.py + OneShotModel + tests)
- **Focus**: Paper-alignment refactoring (IJCAI 2013 Algorithms 2-3)

---

## Overall Assessment

**Strong refactoring.** The migration from SAT-based FM clause checking to `oracle.is_valid()` is semantically correct and aligns with the paper's intended architecture. The DiscriminatingGenerator correctly implements Algorithm 3 line 5 using C_L[Y] + BG instead of ground truth FM clauses. Code is cleaner, more testable, and respects the oracle abstraction boundary.

---

## Critical Issues

None found.

---

## High Priority

### H1. `learner.py` still references deleted `_fm_clauses` parameter (BROKEN)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/learner.py` (staged as new file)

Lines 214, 233, 237: `InteractiveLearner.from_examples()` sets `self._fm_clauses = oracle.get_cnf_clauses()` and `learn_from_examples()` passes `self._fm_clauses` to `QuAcq.learn_from_examples()`. But the refactored `QuAcq.learn_from_examples()` signature no longer accepts `fm_clauses` -- it takes `oracle` instead (3rd positional arg).

```python
# learner.py line 237 (BROKEN):
result = self._quacq.learn_from_examples(
    self.task, self._example_provider, self._fm_clauses, ...)

# quacq.py actual signature (AFTER refactor):
def learn_from_examples(self, task, example_provider, oracle, description_provider, ...)
```

**Impact**: Any code calling `InteractiveLearner.learn_from_examples()` will pass FM clauses where an oracle is expected, causing a `TypeError` or silent semantic bug.

**Fix**: Either delete `learner.py` (it was scheduled for deletion per earlier refactoring -- the old `interactive/learner.py` was deleted) or update it to pass `oracle` instead of `_fm_clauses`.

### H2. `_narrow_with_generator` candidates rebind breaks outer for-loop iteration

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` lines 161-178

The outer loop `for i, c_i in enumerate(candidates)` iterates over the **original** candidates list. When `candidates` is rebound at line 174 (`candidates = [c for c in candidates if c != c_j]`), `c_i` and `i` from the outer `for` still reference positions in the **old** list. This means:

1. After rebinding, `enumerate(candidates)` continues with the old iteration state
2. `c_i` may have been removed from the new candidates list
3. `candidates[i + 1:]` at line 164 indexes the **new** list but with **old** `i`

**Example scenario**: candidates = [A, B, C, D]. i=0, c_i=A. Inner loop tests (A,B). If B is removed: candidates = [A, C, D]. Next outer iteration: i=1, c_i=B (from OLD list). Now comparing B (not in candidates) against C, D from the new list.

Actually, re-reading: the outer `for i, c_i in enumerate(candidates)` captures a snapshot of the original list for iteration. The inner `for c_j in list(candidates[i + 1:])` does use the current (rebound) `candidates`. So the indexing mismatch is real but partially mitigated by taking a snapshot via `list(...)`.

**Practical impact**: Low-medium. The algorithm still converges because:
- Eliminated candidates are also discarded from `remaining_bias`
- The pairwise loop may do redundant comparisons but not incorrect ones
- The early-exit at `len(candidates) == 1` prevents returning an eliminated candidate

**Fix**: Use `while` loop or rebuild enumeration after each rebind:
```python
remaining = list(candidates)
i = 0
while i < len(remaining) and len(remaining) > 1:
    c_i = remaining[i]
    j = i + 1
    while j < len(remaining):
        disc_e = generator.generate(c_i, remaining[j], learned_kb, scope)
        if disc_e is None:
            j += 1
            continue
        is_valid = oracle.is_valid(disc_e)
        record_query(disc_e, is_valid, 'findc')
        if is_valid:
            remaining_bias.discard(remaining[j])
            remaining.pop(j)
        else:
            j += 1
        if len(remaining) == 1:
            return remaining[0]
    i += 1
return remaining[0] if remaining else None
```

---

## Medium Priority

### M1. `record_query` guard silently drops queries at limit

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` lines 186-190, 303-307

```python
def record_query(config, answer, source='main'):
    nonlocal n_queries
    if n_queries < max_queries:
        n_queries += 1
        query_history.append(...)
```

When `n_queries >= max_queries`, FindScope/FindC continue executing and calling `oracle.is_valid()` but queries are silently unrecorded. The `n_queries` counter freezes, so the `while remaining_bias` loop's `n_queries >= max_queries` check eventually triggers, but not before FindScope recursion completes.

**Impact**: A few extra oracle calls may occur beyond `max_queries`. Query history is incomplete (missing tail queries). Not a correctness bug but a metrics accuracy issue.

**Suggestion**: Add a `limit_reached` flag that FindScope/FindC can check to short-circuit recursion early.

### M2. DiscriminatingGenerator generates full configs, not scope-restricted ones

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/discriminating_generator.py` line 52

```python
return self._task.model_to_config(solver.get_model())
```

The SAT model includes all variables (BG clauses constrain all features). The returned config is a full assignment, not restricted to scope Y. The paper says "choose e' in sol(C_L[Y])" -- `C_L[Y]` restricts to scope, but the generated example is a full config.

**Impact**: None for correctness -- oracle.is_valid() works on full configs. But it generates more information than needed (non-scope features get arbitrary values from SAT). This matches how the paper operates in practice (SAT produces full models).

### M3. No unit tests for DiscriminatingGenerator or FindScope/FindC directly

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py`

The new DiscriminatingGenerator class has no dedicated unit tests. FindScope and FindC are only tested indirectly through `QuAcq.learn()` integration tests. Since these are core paper algorithms, direct unit tests would catch regressions.

**Suggested tests**:
- `DiscriminatingGenerator.generate()` with known SAT/UNSAT cases
- `find_scope()` with a mock oracle to verify binary split behavior
- `find_c()` with known candidates and discriminating examples
- Edge: empty learned_kb, single candidate, scope with 1 variable

### M4. `_narrow_with_generator` only handles `is_valid=True` case

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` lines 172-175

When oracle says the discriminating example is valid (is_valid=True), c_j is eliminated (it rejects a valid example). But when is_valid=False, no narrowing happens -- the code just continues to the next pair.

Per the paper, if the discriminating example is invalid, c_i could potentially be eliminated (the valid constraint was c_j, not c_i). The current implementation is conservative (never wrongly eliminates) but may miss narrowing opportunities.

**Impact**: Convergence may require more iterations. Not a correctness bug.

---

## Low Priority

### L1. `_get_constraint_vars` uses private naming convention but is called externally

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` line 118

`_get_constraint_vars()` is prefixed with `_` (private), but is called from `findscope.py` line 85 and `discriminating_generator.py` line 62. Consider making it public.

### L2. `quacq.py` file is 471 lines

Exceeds the 200-line Python guideline from project standards. `QuAcqResult` (143 lines) could be extracted to its own module.

### L3. docs/quacq.md line 143 still references "SAT-based queries"

```
- **FindScope/FindC** uses both SAT-based queries and example pool matching
```

This should be updated to reflect the refactoring: FindScope/FindC now uses oracle.is_valid(), not SAT-based queries.

---

## Edge Cases Found

1. **Partial assignment with empty R**: `find_scope(e, R=set(), Y=all_vars, ask_query=False, ...)` -- initial call skips the oracle query (ask_query=False). Correct behavior.

2. **oracle.is_valid(partial) with partial config**: `FeatureModelOracle.is_valid()` correctly handles partial assignments -- unspecified features have no active assumptions, so SAT solver finds any valid completion. This is semantically equivalent to the paper's partial membership query "does there exist a valid config extending this partial?"

3. **Empty learned_kb in DiscriminatingGenerator**: When `learned_kb=[]`, `_get_learned_clauses_in_scope()` returns `[]`, so the SAT formula is `BG + c_i + neg(c_j)` (no C_L[Y]). Correct for early learning stages.

4. **Single candidate in find_c**: Returns immediately at line 65-66 without querying. Correct optimization.

5. **No rejecting constraints**: Returns None at line 79, logged at debug level. Caller (quacq.py line 251) logs a warning. Correct.

---

## Positive Observations

1. **Clean oracle abstraction boundary** -- all membership queries go through `oracle.is_valid()`, no leaked FM clauses
2. **DiscriminatingGenerator is well-scoped** -- 66 LOC, single responsibility, uses C_L[Y] as paper specifies
3. **Query source tagging** ('main', 'findscope', 'findc') enables precise progressive evaluation
4. **OneShotModel cleanup is complete** -- zero references in `conacq/` or `tests/`
5. **Documentation (docs/quacq.md)** was updated comprehensively to reflect all changes
6. **record_query callback pattern** cleanly separates query counting from algorithm logic

---

## Recommended Actions

1. **[HIGH]** Fix or delete `learner.py` -- it passes `_fm_clauses` to a method that now expects `oracle` (H1)
2. **[HIGH]** Rewrite `_narrow_with_generator` pairwise loop to avoid candidates rebind during iteration (H2)
3. **[MEDIUM]** Add unit tests for DiscriminatingGenerator, find_scope, and find_c (M3)
4. **[MEDIUM]** Handle is_valid=False case in `_narrow_with_generator` to narrow from c_i side (M4)
5. **[LOW]** Fix docs/quacq.md line 143 stale "SAT-based queries" reference (L3)
6. **[LOW]** Extract QuAcqResult to its own module to reduce quacq.py size (L2)

---

## Metrics

- **Type Coverage**: No type annotations on `oracle` param in find_scope/find_c (duck-typed). Acceptable given ABC pattern.
- **Test Coverage**: 53 tests pass. No direct unit tests for new components (DiscriminatingGenerator, find_scope, find_c).
- **Linting Issues**: 0 (no syntax errors, all imports clean in production code)

---

## Unresolved Questions

1. **learner.py intent**: Is `learner.py` meant to be included in the staged changes? It was deleted as `interactive/learner.py` and appears to be re-added under `quacq/learner.py` with stale `_fm_clauses` references. Likely should be deleted or updated.

2. **_narrow_with_generator semantics on invalid discriminating example**: The paper's Algorithm 3 implies both directions of discrimination. Current implementation only eliminates c_j when valid. Is this intentional conservatism or an oversight?
