from conacq.algorithms.quacq.quacq_model import _model_to_config

# Phase 1: Create QueryProvider Class

## Context Links

- Brainstorm: `plans/reports/brainstorm-260228-0420-merge-example-query-provider.md`
- Source: `conacq/example_generators/query_generator.py` (168 LOC)
- Source: `conacq/example_generators/example_provider.py` (51 LOC)
- Target: `conacq/example_generators/query_provider.py` (NEW)

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Create `QueryProvider` merging ExampleProvider pool logic (with paper filtering) + QueryGenerator SAT logic into single class

## Key Insights

- ExampleProvider currently returns examples blindly -- no condition check against C_L or BG
- Paper requires: query in sol(C_L + BG) that violates >=1 constraint in B
- QueryGenerator already matches paper via SAT (iterates bias, solves KB+BG+neg(c))
- Both share same return type: `Tuple[Optional[Dict[str, bool]], Optional[int]]`
- QueryGenerator has `generate_with_priority()` -- keep it (used nowhere currently, but clean API)

## Requirements

### Functional
- Pool filtering: each pool example must (1) satisfy C_L + BG via SAT, (2) violate >=1 c in remaining_bias
- SAT generation: exact same logic as current QueryGenerator.generate()
- Combined mode: pool first, SAT fallback
- Pool state: track index, expose `pool_exhausted` and `pool_remaining` properties
- Profiler integration: @measure_time/@count_calls decorators on generate methods

### Non-Functional
- Single file ~200 LOC (merges 168 + 51 = 219 LOC, minus duplication)
- Preserve all profiler metric names (query_generation_runtime, query_generation_calls, sat_checks_query_gen)

## Architecture

```
QueryProvider
  __init__(solver_name, pool=None, seed=None, profiler=None)
  generate_from_pool(remaining_bias, kb_clauses, bg_clauses, constraint_clauses, feature_ids)
  generate_from_sat(remaining_bias, learned_kb, kb_clauses, negated_clauses, bg_clauses, feature_ids, id_to_feature, constraint_clauses, n_bg)
  generate(remaining_bias, learned_kb, kb_clauses, negated_clauses, bg_clauses, feature_ids, id_to_feature, constraint_clauses, n_bg)
  generate_with_priority(..., priority_fn)
  pool_exhausted: bool (property)
  pool_remaining: int (property)
  _satisfies_formula(clauses, assumptions) -> bool
  _try_generate_for_constraint(...) -> Optional[Dict]
  _model_to_config(model, id_to_feature) -> Dict
```

## Related Code Files

### Files to create
- `conacq/example_generators/query_provider.py`

### Files NOT modified in this phase
- `conacq/example_generators/query_generator.py` (kept until Phase 5)
- `conacq/example_generators/example_provider.py` (kept until Phase 5)

## Implementation Steps

### Step 1: Create `conacq/example_generators/query_provider.py`

Create new file with merged class:

```python
"""
Unified query provider for QuAcq constraint acquisition.

Merges pool-based (ExampleProvider) and SAT-based (QueryGenerator) strategies
into single class with paper-aligned pool filtering.

Paper condition for pool: query in sol(C_L + BG) AND violates >=1 c in B.
"""

import logging
import random
from typing import Optional, Dict, List, Tuple
from pysat.solvers import Solver

from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)
from .sat_check import config_to_assumptions, violates_clauses  # reuse from sat_utils via local import
```

Wait -- `config_to_assumptions` and `violates_clauses` are in `conacq/algorithms/quacq/sat_utils.py`. QueryProvider in `example_generators/` importing from `algorithms/quacq/` would create a coupling concern. However QueryGenerator already has no such import (it does the SAT solving inline). We need `config_to_assumptions` and `violates_clauses` for pool filtering.

**Resolution**: Import from `conacq.algorithms.quacq.sat_utils`. This is acceptable because:
- `query_generator.py` already does inline SAT solving (same level of coupling)
- `sat_utils.py` contains pure functions with no circular dependency risk
- Alternative (duplicating functions) violates DRY

### Step 2: Implement `__init__`

```python
class QueryProvider:
    """Unified query provider: pool-filtered + SAT-based strategies.

    Replaces ExampleProvider (pool) + QueryGenerator (SAT).
    Pool filtering follows paper: query in sol(C_L + BG) AND violates >=1 c in B.

    Args:
        solver_name: PySAT solver name (default: glucose4)
        pool: Optional list of example configs for pool-based generation
        seed: Random seed for pool shuffling
        profiler_instance: Optional profiler for timing/counting
    """

    def __init__(self, solver_name: str = 'glucose4',
                 pool: List[Dict[str, bool]] = None,
                 seed: int = None,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

        # Pool state
        self._pool: List[Dict[str, bool]] = []
        self._pool_index: int = 0
        if pool is not None:
            self._pool = list(pool)
            if seed is not None:
                random.Random(seed).shuffle(self._pool)
            else:
                random.shuffle(self._pool)
```

### Step 3: Implement `generate_from_pool`

Paper condition: (1) satisfies C_L + BG, (2) violates >=1 c in remaining_bias.

```python
    @count_calls('pool_generation_calls')
    def generate_from_pool(
            self,
            remaining_bias: set,
            kb_clauses: List[List[int]],
            bg_clauses: List[List[int]],
            constraint_clauses: Dict[int, List[List[int]]],
            feature_ids: Dict[str, int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query from pool with paper filtering.

        Paper condition: query in sol(C_L + BG) AND violates >=1 c in B.

        Returns:
            Tuple of (query_config, violated_constraint_id) or (None, None)
        """
        formula = kb_clauses + bg_clauses

        while self._pool_index < len(self._pool):
            e = self._pool[self._pool_index]
            self._pool_index += 1

            # Condition 1: satisfies C_L + BG
            assumptions = config_to_assumptions(e, feature_ids)
            if not self._satisfies_formula(formula, assumptions):
                continue

            # Condition 2: violates >=1 constraint in remaining_bias
            assignment = {abs(lit): lit > 0 for lit in assumptions}
            for c_id in remaining_bias:
                clauses = constraint_clauses.get(c_id)
                if clauses and violates_clauses(clauses, assignment):
                    logging.debug('Pool query found testing constraint %s', c_id)
                    return e, c_id

        logging.debug('Pool exhausted (%d examples checked)', self._pool_index)
        return None, None
```

### Step 4: Implement `_satisfies_formula`

```python
    def _satisfies_formula(self, clauses: List[List[int]],
                           assumptions: List[int]) -> bool:
        """Check if assumptions satisfy the given CNF formula."""
        if not clauses:
            return True
        solver = Solver(name=self.solver_name, bootstrap_with=clauses)
        try:
            return solver.solve(assumptions=assumptions)
        finally:
            solver.delete()
```

### Step 5: Implement `generate_from_sat`

Copy existing QueryGenerator.generate() logic exactly (lines 27-74 of query_generator.py):

```python
    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate_from_sat(
            self,
            remaining_bias: set,
            learned_kb: list,
            kb_clauses: List[List[int]],
            negated_clauses: Dict[int, List[List[int]]],
            bg_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            n_bg: int = 0,
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query via SAT solving (matches paper Algorithm 1).

        Find config satisfying KB + BG but violating some c in Bias.
        """
        logging.debug('QueryProvider SAT: KB=%d, Bias=%d, BG=%d',
                      len(learned_kb), len(remaining_bias), n_bg)

        for c_id in remaining_bias:
            neg_c_clauses = negated_clauses.get(c_id)
            if neg_c_clauses is None:
                logging.warning('No negated form for constraint %s, skipping', c_id)
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses, bg_clauses=bg_clauses,
                neg_c_clauses=neg_c_clauses, feature_ids=feature_ids,
                id_to_feature=id_to_feature)

            if query_result is not None:
                logging.debug('SAT query testing constraint %s', c_id)
                return query_result, c_id

        logging.debug('No SAT query possible - all bias implied by KB + BG')
        return None, None
```

### Step 6: Implement `generate` (combined)

```python
    def generate(
            self,
            remaining_bias: set,
            learned_kb: list,
            kb_clauses: List[List[int]],
            negated_clauses: Dict[int, List[List[int]]],
            bg_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            constraint_clauses: Dict[int, List[List[int]]],
            n_bg: int = 0,
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Pool first, then SAT fallback."""
        if not self.pool_exhausted:
            result = self.generate_from_pool(
                remaining_bias, kb_clauses, bg_clauses,
                constraint_clauses, feature_ids)
            if result[0] is not None:
                return result

        return self.generate_from_sat(
            remaining_bias, learned_kb, kb_clauses,
            negated_clauses, bg_clauses, feature_ids,
            id_to_feature, n_bg)
```

### Step 7: Implement properties and helper methods

```python
    @property
def pool_exhausted(self) -> bool:
    """Check if pool has been fully consumed."""
    return self._pool_index >= len(self._pool)


@property
def pool_remaining(self) -> int:
    """Number of pool examples remaining."""
    return max(0, len(self._pool) - self._pool_index)


@count_calls('sat_checks_query_gen')
def _try_generate_for_constraint(
        self, kb_clauses, bg_clauses, neg_c_clauses,
        feature_ids, id_to_feature):
    """Try to generate query violating specific constraint."""
    all_clauses = list(kb_clauses) + list(bg_clauses) + list(neg_c_clauses)
    solver = Solver(name=self.solver_name, bootstrap_with=all_clauses)
    try:
        with self.profiler.timer('sat_solve_time'):
            is_sat = solver.solve()
        if is_sat:
            return _model_to_config(solver.get_model(), id_to_feature)
        return None
    finally:
        solver.delete()


def _model_to_config(self, model, id_to_feature):
    """Convert SAT model to configuration dictionary."""
    config = {}
    for lit in model:
        var = abs(lit)
        if var in id_to_feature:
            config[id_to_feature[var]] = lit > 0
    return config
```

### Step 8: Implement `generate_with_priority` (preserve from QueryGenerator)

Copy lines 115-157 of query_generator.py, adapting to use `self._try_generate_for_constraint`:

```python
    def generate_with_priority(
            self, remaining_bias, learned_kb, kb_clauses,
            negated_clauses, constraint_clauses, bg_clauses,
            feature_ids, id_to_feature, priority_fn=None, n_bg=0,
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query with constraint priority ordering."""
        if priority_fn is None:
            return self.generate_from_sat(
                remaining_bias, learned_kb, kb_clauses,
                negated_clauses, bg_clauses, feature_ids,
                id_to_feature, n_bg)

        sorted_bias = sorted(
            remaining_bias,
            key=lambda c_id: priority_fn(c_id, constraint_clauses.get(c_id, [])),
            reverse=True)

        for c_id in sorted_bias:
            neg_c_clauses = negated_clauses.get(c_id)
            if neg_c_clauses is None:
                continue
            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses, bg_clauses=bg_clauses,
                neg_c_clauses=neg_c_clauses, feature_ids=feature_ids,
                id_to_feature=id_to_feature)
            if query_result is not None:
                return query_result, c_id

        return None, None
```

### Step 9: Keep standalone priority functions

At module level (after class), copy from query_generator.py:

```python
def clause_count_priority(c_id, clauses: List[List[int]]) -> int:
    """Priority function based on clause count."""
    return len(clauses)


def literal_count_priority(c_id, clauses: List[List[int]]) -> int:
    """Priority function based on total literal count."""
    return sum(len(c) for c in clauses)
```

## Todo List

- [ ] Create `conacq/example_generators/query_provider.py`
- [ ] Implement `__init__` with pool shuffling
- [ ] Implement `generate_from_pool` with paper filtering
- [ ] Implement `_satisfies_formula` SAT check
- [ ] Implement `generate_from_sat` (copy from QueryGenerator)
- [ ] Implement `generate` (combined pool+SAT)
- [ ] Implement properties (pool_exhausted, pool_remaining)
- [ ] Implement `_try_generate_for_constraint` and `_model_to_config`
- [ ] Implement `generate_with_priority`
- [ ] Add priority functions at module level

## Success Criteria

- QueryProvider class created with all three generate methods
- Pool filtering matches paper condition (SAT check + bias violation)
- SAT generation logic identical to current QueryGenerator
- File ~200 LOC, well-documented
- No circular imports

## Risk Assessment

- **Import coupling**: QueryProvider imports from `conacq.algorithms.quacq.sat_utils` -- acceptable, pure functions, no circular risk
- **Pool filtering performance**: SAT check per pool example adds overhead -- correctness > speed
- **Pool depletion**: With filtering, more pool examples skipped in example_only mode -- expected, documents in docstring

## Security Considerations

- Solver instances properly cleaned up in finally blocks
- No external input validation needed (internal API)

## Next Steps

- Phase 2: Update QuAcq to use QueryProvider
