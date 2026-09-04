# Phase 4: Refactor QuAcq — learn() + learn_from_examples()

## Context

- Brainstorm: `plans/reports/brainstorm-260227-1614-findscope-findc-oracle-refactor.md`
- Paper: IJCAI 2013 Algorithm 1 — main loop uses FindScope+FindC on negative answers
- Depends on: Phase 2 (FindScope), Phase 3 (FindC)

## Overview

- **Priority**: P1
- **Status**: completed
- **Effort**: 45min

Two changes in `quacq.py`:
1. **learn()**: Replace `_find_conflict()` (QuickXPlain) with FindScope+FindC on negative answers
2. **learn_from_examples()**: Replace `_check_consistency_with_fm()` with `oracle.is_valid()`; update FindScope/FindC call sites to new signatures

## Key Changes

### learn() (oracle mode)

| Before | After |
|--------|-------|
| Negative answer -> `_find_conflict()` (QuickXPlain) | Negative answer -> `find_scope()` + `find_c()` |
| No DiscriminatingGenerator | Create DiscriminatingGenerator at start |
| No all_variables computation | Compute `all_variables = set(task.feature_ids.keys())` |

### learn_from_examples() (example mode)

| Before | After |
|--------|-------|
| `_check_consistency_with_fm(fm_clauses, e_assumptions)` | `oracle.is_valid(query)` |
| `fm_clauses` param | `oracle` param |
| FindScope called with `fm_clauses`, `solver_name` | FindScope called with `oracle`, `record_query` |
| FindC called with `fm_clauses`, `example_provider`, `solver_name`, `query_mode` | FindC called with `oracle`, `learned_kb`, `generator` |
| Fallback to `_find_conflict` when scope empty | Keep fallback (scope empty = degenerate case) |

## Requirements

### Functional
- `learn()` uses FindScope+FindC (paper-faithful) on negative oracle answers
- `learn_from_examples()` uses `oracle.is_valid()` for main loop validity check
- Both modes pass oracle and record_query to FindScope/FindC
- DiscriminatingGenerator created once per learn call

### Non-functional
- Delete: `_check_consistency_with_fm()`, `_find_conflict()`, `_quickxplain_constraints()`, `_get_clauses_for_constraints()`, `_is_consistent()`
- Remove dead imports: `OneShotModel`, `Solver` (if no longer used)
- File ~350 LOC (down from 551)

## Related Code Files

### Modify
- `conacq/algorithms/quacq/quacq.py` (551 LOC -> ~350 LOC)

### Dependencies
- `conacq/algorithms/quacq/findscope.py` (Phase 2 signature)
- `conacq/algorithms/quacq/findc.py` (Phase 3 signature)
- `conacq/algorithms/quacq/discriminating_generator.py` (Phase 1)

## Signature Changes

### learn()
No signature change. Internally switches from QuickXPlain to FindScope+FindC.

### learn_from_examples()
```python
def learn_from_examples(
        self,
        task: QuAcqTask,
        example_provider: ExampleProvider,
        oracle,                    # NEW: replaces fm_clauses
        description_provider: DescriptionProvider,
        query_mode: Literal['example_only', 'example_first'] = 'example_only',
        max_queries: int = 10000
) -> QuAcqResult:
```

**Removed**: `fm_clauses: List[List[int]]`
**Added**: `oracle`
**Note**: `query_mode` retained — controls pool exhaustion vs SAT fallback for the main loop query source. Not passed to FindC anymore.

## Implementation Steps

### Step 1: Update imports

Add:
```python
from .discriminating_generator import DiscriminatingGenerator
```

Remove (after all deletions):
```python
from conacq.oracle.fm_oracle_model import OneShotModel
```

Check if `Solver` still needed — only used by `_is_consistent()` which is being deleted. Remove if no other usage.

### Step 2: Refactor learn() (lines 161-238)

Replace the `else` branch (negative answer, lines 217-230):

```python
else:
    scope_vars = find_scope(
        e=query, R=set(), Y=all_variables,
        ask_query=False, oracle=oracle, task=task,
        remaining_bias=remaining_bias,
        record_query=record_query, profiler=self.profiler
    )

    scope = set(scope_vars)
    if scope:
        c_id = find_c(
            e=query, scope=scope, task=task,
            remaining_bias=remaining_bias,
            record_query=record_query, oracle=oracle,
            learned_kb=learned_kb, generator=generator,
            profiler=self.profiler
        )

        if c_id is not None:
            if c_id not in learned_kb:
                learned_kb.append(c_id)
            remaining_bias.discard(c_id)
            logging.debug('FindScope/FindC added constraint: %s', c_id)
        else:
            logging.warning('FindC returned no constraint for scope %s', scope)
    else:
        logging.warning('FindScope returned empty scope for negative example')
        # Fallback: add tested constraint directly
        if tested_c_id:
            if tested_c_id not in learned_kb:
                learned_kb.append(tested_c_id)
            remaining_bias.discard(tested_c_id)
```

Add before the while loop:
```python
all_variables = set(task.feature_ids.keys())
generator = DiscriminatingGenerator(task, self.solver_name)
```

### Step 3: Refactor learn_from_examples() (lines 242-380)

**3a.** Update signature: replace `fm_clauses` with `oracle`.

**3b.** Add at start (after local state init):
```python
generator = DiscriminatingGenerator(task, self.solver_name)
```

**3c.** Replace main loop validity check (line 309):
```python
# Before:
e_assumptions = task.config_to_assumptions(query)
is_valid = self._check_consistency_with_fm(fm_clauses, e_assumptions)

# After:
is_valid = oracle.is_valid(query)
```

**3d.** Update find_scope call (lines 324-334):
```python
scope_vars = find_scope(
    e=query, R=set(), Y=all_variables,
    ask_query=False, oracle=oracle, task=task,
    remaining_bias=remaining_bias,
    record_query=record_query, profiler=self.profiler
)
```

**3e.** Update find_c call (lines 338-349):
```python
c_id = find_c(
    e=query, scope=scope, task=task,
    remaining_bias=remaining_bias,
    record_query=record_query, oracle=oracle,
    learned_kb=learned_kb, generator=generator,
    example_provider=example_provider,
    query_mode=query_mode,
    profiler=self.profiler
)
```

<!-- Updated: Validation Session 1 - No QuickXPlain fallback confirmed -->
**3f.** Remove QuickXPlain fallback (lines 359-368). Replace with simple log warning (FindScope empty = degenerate case, skip). This removes the last usage of `_find_conflict`.

### Step 4: Delete dead methods

Delete these methods from QuAcq class:
- `_check_consistency_with_fm()` (lines 382-390)
- `_find_conflict()` (lines 472-498)
- `_quickxplain_constraints()` (lines 500-527)
- `_get_clauses_for_constraints()` (lines 529-536)
- `_is_consistent()` (lines 538-551)

### Step 5: Clean up imports

Remove:
- `from conacq.oracle.fm_oracle_model import OneShotModel`
- `from pysat.solvers import Solver` (if no other usage)
- `from ._task_compat import get_bg_clauses` (only used by deleted `_find_conflict`)

Keep:
- `from ._task_compat import get_clause_map` (still used by `_prune_rejecting_constraints`)

### Step 6: Update docstrings

Update class docstring, `learn()` docstring, `learn_from_examples()` docstring.

## Todo

- [x] Add `DiscriminatingGenerator` import
- [x] Refactor `learn()`: create generator + all_variables; replace `_find_conflict` with FindScope+FindC
- [x] Refactor `learn_from_examples()`: replace `fm_clauses` param with `oracle`; replace `_check_consistency_with_fm` with `oracle.is_valid()`; update FindScope/FindC call sites
- [x] Remove QuickXPlain fallback in `learn_from_examples()`; use simple tested_c_id addition
- [x] Delete 5 dead methods: `_check_consistency_with_fm`, `_find_conflict`, `_quickxplain_constraints`, `_get_clauses_for_constraints`, `_is_consistent`
- [x] Remove dead imports: `OneShotModel`, `Solver`, `get_bg_clauses`
- [x] Update docstrings
- [x] Verify file compiles: `python -c "from conacq.algorithms.quacq.quacq import QuAcq"`

## Success Criteria

- `learn()` uses FindScope+FindC (not QuickXPlain) on negative answers
- `learn_from_examples()` uses `oracle.is_valid()` (not `_check_consistency_with_fm`)
- All 5 dead methods deleted
- No `OneShotModel`, `Solver` imports in quacq.py
- File compiles without errors

## Risk Assessment

- **Medium risk**: Behavioral change in `learn()` — switching from QuickXPlain to FindScope+FindC. QuickXPlain finds minimal conflict sets; FindScope+FindC finds single constraints. This is the paper-correct behavior but may affect learning dynamics.
- **Low risk**: `learn_from_examples()` changes are mostly mechanical (oracle replaces SAT check).
- **Note**: `learn_from_examples` no longer passes `example_provider` to FindC. Pool examples consumed only by main loop. This is paper-faithful but changes pool consumption dynamics.
