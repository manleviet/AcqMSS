# Phase 2: Update QuAcq Algorithm

## Context Links
- [Parent Plan](plan.md) | [Phase 1](phase-01-create-quacq-task-and-model.md)
- Source: `conacq/algorithms/interactive/quacq.py` (439 LOC)
- Pattern: `conacq/algorithms/acqmss/reduce.py` (direct REDUCE call)

## Overview
- **Priority**: P1
- **Status**: completed
- **Depends on**: Phase 1
- **Description**: Update QuAcq to accept QuAcqTask, operate on `int` assumption IDs, and call REDUCE directly (remove _reduce_kb conversion layer).

## Key Insights
1. `_reduce_kb()` (lines 376-446) builds temporary assumption IDs, calls Reduce, maps back to strings. With QuAcqTask, this entire method is replaced by a direct `Reduce.reduce()` call.
2. `_prune_rejecting_constraints()` (lines 268-282) iterates `task.bias` (Set[str]), looks up clauses via `task.constraint_map[c_id]`. With QuAcqTask: iterate `task.bias` (Set[int]), look up via `task.constraint_clauses[aid]`.
3. `_find_conflict()` (lines 285-313) builds bg_clauses from KB + background, runs `_quickxplain_constraints()` on string IDs. With QuAcqTask: same logic but constraint_ids are `int`.
4. `_quickxplain_constraints()` (lines 315-352) is generic — just change `List[str]` to `List[int]` and `constraint_map` lookup to `constraint_clauses`.
5. `learn()` and `learn_from_examples()` change task type parameter; internal logic changes are minimal.
6. QueryGenerator still returns `(config, tested_c_id)` — but `tested_c_id` must change meaning. See "QueryGenerator Changes" below.

## Requirements

### Functional
- `QuAcq.learn(task: QuAcqTask, oracle, ...)` — accept QuAcqTask
- `QuAcq.learn_from_examples(task: QuAcqTask, ...)` — accept QuAcqTask
- REDUCE called directly via `Reduce.reduce(set_b_prime, set_neg_tv=[], set_bg, negation_map)`
- All constraint operations use `int` assumption IDs
- QueryGenerator must work with QuAcqTask (separate concern, but called from QuAcq)

### Non-functional
- Delete `_reduce_kb()` method entirely
- No string-to-int conversion anywhere in QuAcq

## Architecture

### Before (string IDs)
```
QuAcq.learn(InteractiveTask) → loop with str IDs
  _prune_rejecting_constraints() → iterate bias: Set[str]
  _find_conflict() → quickxplain on List[str]
  _reduce_kb() → build temp assumption IDs → Reduce → map back to str
  → InteractiveResult(kb_constraints: List[str])
```

### After (assumption IDs)
```
QuAcq.learn(QuAcqTask) → loop with int IDs
  _prune_rejecting_constraints() → iterate bias: Set[int]
  _find_conflict() → quickxplain on List[int]
  _build_result() → direct Reduce.reduce() call
  → InteractiveResult(kb_assumption_ids: List[int])
```

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `conacq/algorithms/interactive/quacq.py` | Major: all methods updated, _reduce_kb deleted |
| `conacq/example_generators/query_generator.py` | Accept QuAcqTask, return `(config, Optional[int])` |

### Files to Read
| File | Why |
|------|-----|
| `conacq/algorithms/acqmss/reduce.py` | Reduce.reduce() signature |
| `conacq/algorithms/interactive/quacq_task.py` | QuAcqTask API (from Phase 1) |

## Implementation Steps

### Step 1: Update QuAcq imports and constructor
```python
# Add imports
from .quacq_task import QuAcqTask
# Keep InteractiveTask import for backward compat (deprecated path)

# Constructor unchanged (solver_name, profiler)
```

### Step 2: Update `learn()` method (line 45)
Change signature:
```python
def learn(self, task: QuAcqTask, oracle: Oracle, max_queries: int = 1000) -> InteractiveResult:
```

Body changes:
- `task.bias` is now `Set[int]` — loop logic unchanged (while task.bias)
- `self.query_generator.generate(task)` — QueryGenerator must accept QuAcqTask
- `query, tested_c_id` — tested_c_id is now `Optional[int]`
- `task.add_to_kb(c_id)` — c_id is now `int`
- `task.remove_from_bias(conflict)` — conflict is `List[int]`

### Step 3: Update `learn_from_examples()` method (line 106)
Change signature:
```python
def learn_from_examples(self, task: QuAcqTask, example_provider: ExampleProvider,
                        fm_clauses: List[List[int]], ...) -> InteractiveResult:
```

Body changes:
- `all_variables = set(task.feature_ids.keys())` — unchanged
- `find_scope(...)` — Phase 3 handles this
- `find_c(...)` — Phase 3 handles this
- `c_id` return from find_c is now `int`

### Step 4: Update `_prune_rejecting_constraints()` (line 268)
```python
def _prune_rejecting_constraints(self, task: QuAcqTask,
                                 positive_example: Dict[str, bool]) -> List[int]:
    """Remove constraints from Bias that reject the positive example."""
    assumptions = task.config_to_assumptions(positive_example)
    assignment = {abs(lit): lit > 0 for lit in assumptions}

    pruned = []
    for aid in list(task.bias):
        clauses = task.constraint_clauses.get(aid, [])
        if task.violates_clauses(clauses, assignment):
            pruned.append(aid)

    task.remove_from_bias(pruned)
    return pruned
```

### Step 5: Update `_find_conflict()` (line 285)
```python
def _find_conflict(self, task: QuAcqTask,
                   negative_example: Dict[str, bool]) -> List[int]:
    """Find minimal conflict set using QuickXPlain on assumption IDs."""
    example_clauses = []
    for name, value in negative_example.items():
        if name in task.feature_ids:
            fid = task.feature_ids[name]
            example_clauses.append([fid if value else -fid])

    # KB clauses from learned constraints
    bg_clauses = task.get_kb_clauses()

    # BG assumptions as unit clauses
    for bg_id in task.background:
        bg_clauses.append([bg_id])

    bg_clauses.extend(example_clauses)

    bias_constraints = list(task.bias)
    conflict = self._quickxplain_constraints(
        constraint_ids=[],
        remaining=bias_constraints,
        background=bg_clauses,
        task=task
    )
    return conflict
```

### Step 6: Update `_quickxplain_constraints()` (line 315)
```python
def _quickxplain_constraints(
        self,
        constraint_ids: List[int],
        remaining: List[int],
        background: List[List[int]],
        task: QuAcqTask
) -> List[int]:
    """QuickXPlain adapted for assumption IDs."""
    if constraint_ids and not self._is_consistent(background):
        return []
    if not remaining:
        return []
    if len(remaining) == 1:
        return remaining

    k = len(remaining) // 2
    c1 = remaining[:k]
    c2 = remaining[k:]

    c2_clauses = self._get_clauses_for_constraints(c2, task)
    cs1 = self._quickxplain_constraints(c2, c1, background + c2_clauses, task)

    cs1_clauses = self._get_clauses_for_constraints(cs1, task)
    cs2 = self._quickxplain_constraints(cs1, c2, background + cs1_clauses, task)

    return cs1 + cs2
```

### Step 7: Update `_get_clauses_for_constraints()` (line 354)
```python
def _get_clauses_for_constraints(self, constraint_ids: List[int],
                                 task: QuAcqTask) -> List[List[int]]:
    """Get raw clauses for assumption IDs."""
    clauses = []
    for aid in constraint_ids:
        clauses.extend(task.constraint_clauses.get(aid, []))
    return clauses
```

### Step 8: Delete `_reduce_kb()` and update `_build_result()`
Delete `_reduce_kb()` entirely (lines 376-446).

Update `_build_result()`:
```python
def _build_result(self, task: QuAcqTask, start_time: float,
                  convergence_reason: str) -> InteractiveResult:
    """Build InteractiveResult with REDUCE applied directly."""
    # Direct REDUCE call (no conversion layer)
    final_kb = self._apply_reduce(task)
    runtime_ms = (time.perf_counter() - start_time) * 1000
    # ... rest unchanged but kb_constraints -> kb_assumption_ids (Phase 4)
```

New `_apply_reduce()`:
```python
def _apply_reduce(self, task: QuAcqTask) -> List[int]:
    """Apply REDUCE directly using assumption IDs."""
    if not task.learned_kb:
        return []

    checker = NonIncrementalPySATChecker(
        task.set_kb, task.assumptions, self.solver_name, self.profiler)
    try:
        reduce = Reduce(checker, self.profiler)
        redundant, non_redundant = reduce.reduce(
            set_b_prime=task.learned_kb,
            set_neg_tv=[],
            set_bg=task.background,
            negation_map=task.negation_map
        )
        return non_redundant
    except Exception as e:
        logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
        return list(task.learned_kb)
```

### Step 9: Update QueryGenerator (query_generator.py)

QueryGenerator.generate() currently accepts `InteractiveTask` and returns `(config, tested_c_id: str)`.

Changes needed:
- Accept `QuAcqTask` (duck-typing is fine — both have `bias`, `learned_kb`, `constraint_map`/`constraint_clauses`, `negated_constraint_map`, etc.)
- But QuAcqTask doesn't have `negated_constraint_map` by string key — it has negation_map by int.
- **Solution**: Add `negated_clauses: Dict[int, List[List[int]]]` to QuAcqTask that maps `assumption_id -> negated clauses` (raw, without guards). Populated during preparation alongside constraint_clauses.
- QueryGenerator iterates bias (Set[int]), looks up negated clauses, builds SAT formula.
- Return type: `Tuple[Optional[Dict[str, bool]], Optional[int]]`

Alternative simpler approach: QueryGenerator can accept a Union type or we create a new method. Given KISS, recommend making QueryGenerator work with QuAcqTask by adding `negated_clauses` dict to QuAcqTask.

Update to `quacq_task.py` (from Phase 1):
```python
# Add field:
negated_clauses: Dict[int, List[List[int]]] = field(default_factory=dict)
```

Update `interactive_task_preparation.py` to populate it:
```python
# After prepare_kb(), for each bias assumption_id:
for aid in result.bias:
    name = provider.get_description(aid)
    neg_key = f"NOT({name})"
    if neg_key in model.negated_constraint_map:
        result.negated_clauses[aid] = model.negated_constraint_map[neg_key]
```

QueryGenerator changes:
```python
def generate(self, task: QuAcqTask) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
    kb_clauses = task.get_kb_clauses()
    for aid in task.bias:
        neg_c_clauses = task.negated_clauses.get(aid)
        if neg_c_clauses is None:
            continue
        query_result = self._try_generate_for_constraint(
            kb_clauses=kb_clauses,
            bg_clauses=[bg_id for bg_id in task.background],  # unit literals
            neg_c_clauses=neg_c_clauses,
            feature_ids=task.feature_ids,
            id_to_feature=task.id_to_feature
        )
        if query_result is not None:
            return query_result, aid
    return None, None
```

## Todo List
- [ ] Update QuAcq.learn() signature and body for QuAcqTask
- [ ] Update QuAcq.learn_from_examples() signature and body
- [ ] Update _prune_rejecting_constraints() for int IDs
- [ ] Update _find_conflict() for int IDs
- [ ] Update _quickxplain_constraints() for int IDs
- [ ] Update _get_clauses_for_constraints() for int IDs
- [ ] Delete _reduce_kb() entirely
- [ ] Create _apply_reduce() with direct Reduce.reduce() call
- [ ] Update _build_result() to use _apply_reduce()
- [ ] Add negated_clauses field to QuAcqTask (Phase 1 update)
- [ ] Populate negated_clauses in InteractiveTaskPreparation (Phase 1 update)
- [ ] Update QueryGenerator.generate() for QuAcqTask
- [ ] Update QueryGenerator.generate_with_priority() for QuAcqTask

## Success Criteria
- QuAcq.learn() accepts QuAcqTask and returns result with int IDs
- _reduce_kb() deleted; REDUCE called directly
- No string constraint IDs in QuAcq methods
- QueryGenerator works with QuAcqTask

## Risk Assessment
1. **QuickXPlain correctness**: The adapted QuickXPlain must produce the same conflict sets. Constraint ID type change (str->int) doesn't affect algorithm logic. Verify with test.
2. **REDUCE direct call**: Current _reduce_kb builds its own set_kb with assumption guards. With QuAcqTask, set_kb already has guards from prepare_kb(). The learned_kb contains assumption IDs that are already in set_kb. Direct call should work. Verify background handling.

## Security Considerations
- No changes to external input handling

## Next Steps
- Phase 3: Update FindScope + FindC for QuAcqTask
