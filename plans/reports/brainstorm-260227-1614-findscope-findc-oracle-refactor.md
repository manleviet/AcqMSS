# Brainstorm: FindScope/FindC Oracle Refactoring

**Date**: 2026-02-27
**Status**: Agreed — ready for implementation plan

## Problem Statement

Current FindScope/FindC implementation deviates from IJCAI 2013 paper in 5 ways:

| # | Paper | Current Implementation | Issue |
|---|-------|----------------------|-------|
| 1 | Main loop (no answer) → FindScope + FindC | `_find_conflict` (QuickXPlain) | Wrong algorithm |
| 2 | FindScope ASK(e[R]) = oracle partial query | SAT check via OneShotModel against FM clauses | Bypasses oracle |
| 3 | FindC line 5: `e' ∈ sol(C_L[Y])` | `fm_clauses + c_i + ¬c_j` | Uses FM (ground truth) instead of learned KB |
| 4 | FindC line 9: ASK(e') = oracle query | `_check_fm_consistency` SAT check | Bypasses oracle |
| 5 | All ASK operations count as queries | FindScope doesn't call record_query | Missing query counting |

### Key Insight: C_L vs FM clauses (information leak)

Paper Algorithm 3 line 5: `choose e' in sol(C_L[Y])` — discriminating examples come from **learned KB restricted to scope Y**, NOT FM clauses (target/ground truth). Using FM = cheating (learner uses answer before asking oracle).

## Agreed Design

### 1. FindScope — receives oracle, uses oracle.is_valid(partial)

```python
def find_scope(e, R, Y, ask_query, oracle, task, remaining_bias,
               record_query, profiler):
    if ask_query:
        partial = {k: e[k] for k in R}
        is_consistent = oracle.is_valid(partial)  # partial membership query
        record_query(partial, is_consistent, 'findscope')
        if is_consistent:
            _prune_rejecting_partial(task, remaining_bias, e, R)
        else:
            return []
    ...
```

- `oracle.is_valid(partial_dict)` already works for partial queries (verified: `_config_to_assumptions` handles partial dicts)
- Remove: `fm_clauses`, `solver_name` params
- Remove: `_check_partial_consistency()`, `OneShotModel` usage
- Add: `record_query` callback + `oracle` param

### 2. FindC — receives oracle + DiscriminatingGenerator

```python
def find_c(e, scope, task, remaining_bias, record_query, oracle,
           generator, ...):
    # ... narrow candidates ...
    disc_e = generator.generate(c_i, c_j, learned_kb, scope)
    if disc_e:
        is_valid = oracle.is_valid(disc_e)  # ASK oracle (paper line 9)
        record_query(disc_e, is_valid, 'findc')
```

- Remove: `fm_clauses`, `solver_name` params
- Remove: `_check_fm_consistency()`, `OneShotModel` usage
- Add: `oracle` + `generator` params

### 3. DiscriminatingGenerator — standalone class, uses C_L[Y]

```python
class DiscriminatingGenerator:
    """Paper Algorithm 3 line 5: generate e' in sol(C_L[Y])."""

    def __init__(self, model: QuAcqModel, solver_name='glucose4'):
        self._task = model.task
        self._solver_name = solver_name

    def generate(self, c_i, c_j, learned_kb, scope):
        """Find e' s.t. e' ∈ sol(C_L[Y]) ∧ e' |= c_i ∧ e' ⊭ c_j."""
        # C_L[Y]: learned constraints restricted to scope Y
        cl_y_clauses = self._get_learned_clauses_in_scope(learned_kb, scope)
        clauses_i = self._task.constraint_clauses[c_i]
        neg_j = self._task.negated_clauses[c_j]

        solver = Solver(bootstrap_with=cl_y_clauses + clauses_i + neg_j)
        try:
            if solver.solve():
                return self._task.model_to_config(solver.get_model())
        finally:
            solver.delete()
        return None
```

- File: `conacq/algorithms/quacq/discriminating_generator.py` (~40 LOC)
- Init: QuAcqModel + solver_name (no fm_clauses needed)
- SAT formula: `C_L[Y] + c_i + ¬c_j` (faithful to paper)

### 4. Oracle mode learn() — switch from QuickXPlain to FindScope/FindC

```python
# When oracle answers NO:
scope_vars = find_scope(e=query, R=set(), Y=all_variables,
                        ask_query=False, oracle=oracle, ...)
if scope_vars:
    c_id = find_c(e=query, scope=set(scope_vars), oracle=oracle,
                  generator=generator, ...)
```

### 5. learn_from_examples() — also pass oracle instead of fm_clauses

- Main loop: `oracle.is_valid(query)` replaces `_check_consistency_with_fm`
- Pass oracle to FindScope/FindC

## Components to Remove

| Component | File | Reason |
|-----------|------|--------|
| `OneShotModel` class | `fm_oracle_model.py` | No longer needed |
| `_check_partial_consistency()` | `findscope.py` | Replaced by oracle.is_valid |
| `_check_fm_consistency()` | `findc.py` | Replaced by oracle.is_valid |
| `_check_consistency_with_fm()` | `quacq.py` | Replaced by oracle.is_valid |
| `_find_conflict()` | `quacq.py` | Replaced by FindScope+FindC in oracle mode |
| `_quickxplain_constraints()` | `quacq.py` | Replaced by FindScope+FindC |
| `fm_clauses` param | findscope/findc/learn_from_examples | Oracle encapsulates FM |

## Open Questions

1. **_narrow_with_pool** in FindC also uses fm_clauses — needs same C_L[Y] treatment?
2. **learn_from_examples main loop** generates queries from example pool, not GenerateQuery. `oracle.is_valid()` replaces SAT check, but semantically example-based mode still needs oracle.
3. **BG clauses in C_L[Y]**: Should `C_L[Y]` include BG constraints whose scope ⊆ Y? Paper says `C_L` = learned network. BG is background knowledge, not learned. Need clarification.
