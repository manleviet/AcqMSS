# Phase 2: Internalize Mutable State in QuAcq Algorithm

## Context Links

- [Plan overview](plan.md)
- [Phase 1: Make task immutable](phase-01-make-task-immutable.md)
- [QuAcq algorithm source](../../conacq/algorithms/quacq/quacq.py)
- [FindScope source](../../conacq/algorithms/quacq/findscope.py)
- [FindC source](../../conacq/algorithms/quacq/findc.py)
- [QueryGenerator source](../../conacq/example_generators/query_generator.py)

## Overview

- **Date**: 2026-02-27
- **Priority**: P2
- **Status**: pending
- **Description**: Move mutable learning state (`remaining_bias`, `learned_kb`, `n_queries`, `query_history`) into QuAcq's `learn()` and `learn_from_examples()` as local variables. Thread `remaining_bias` and a `record_query` callback through FindScope, FindC, and QueryGenerator.

## Key Insights

1. **4 mutation points** exist across 4 files: `quacq.py` (learn/learn_from_examples), `findscope.py` (_prune_rejecting_partial), `findc.py` (_narrow_with_pool/_narrow_with_sat)
2. `QueryGenerator.generate()` reads `task.bias` (line 71) and `task.learned_kb` (line 67) — must change to accept `remaining_bias` and `learned_kb` params
3. FindScope mutates `task.bias` via `task.remove_from_bias(pruned)` (line 118) — needs `remaining_bias` passed as mutable set
4. FindC mutates `task.bias` via `task.remove_from_bias([c_id])` (line 134) and calls `task.record_query()` (lines 127, 172) — needs `remaining_bias` set + `record_query` callback
5. `_build_result()` and `_apply_reduce()` read `task.learned_kb` and `task.n_queries` — must accept these as params

## Requirements

### Functional
- `learn()` and `learn_from_examples()`: create local `remaining_bias = set(task.set_c)`, `learned_kb = []`, `n_queries = 0`, `query_history = []`
- Replace all `task.bias` reads with `remaining_bias`
- Replace all `task.add_to_kb(x)` with `learned_kb.append(x)`
- Replace all `task.remove_from_bias(x)` with `remaining_bias -= set(x)`
- Replace all `task.record_query(c, a, s)` with `n_queries += 1; query_history.append(...)`
- Replace all `task.n_queries` reads with `n_queries`
- Thread `remaining_bias` through FindScope/FindC/QueryGenerator
- Thread `record_query` callback or `(n_queries, query_history)` through FindC

### Non-Functional
- No behavioral change — same algorithm, same results
- Keep function signatures minimal (pass only what's needed)

## Architecture

### Mutable State Threading Pattern

```
QuAcq.learn(task):
    remaining_bias = set(task.set_c)   # Local copy
    learned_kb = []                     # Local accumulator
    n_queries = 0                       # Local counter
    query_history = []                  # Local history

    def record_query(config, answer, source='main'):
        nonlocal n_queries
        n_queries += 1
        query_history.append((config.copy(), answer, source))

    while remaining_bias:
        query, c_id = query_generator.generate(
            task, remaining_bias, learned_kb)  # Pass state

        record_query(query, answer)

        if positive:
            pruned = _prune(task, remaining_bias, query)
            remaining_bias -= set(pruned)
        else:
            conflict = _find_conflict(task, remaining_bias, query)
            for c_id in conflict:
                learned_kb.append(c_id)
            remaining_bias -= set(conflict)

    return _build_result(task, learned_kb, n_queries, query_history, ...)
```

### FindScope/FindC Threading

FindScope receives `remaining_bias` (mutable set) and mutates it directly for pruning (same semantics as before, just not via task).

FindC receives `remaining_bias` (mutable set) and `record_query` callback. The callback lets FindC record discriminating queries without knowing about n_queries/query_history internals.

## Related Code Files

### Modify
- `conacq/algorithms/quacq/quacq.py` — learn(), learn_from_examples(), _build_result(), _apply_reduce(), _prune_rejecting_constraints(), _find_conflict()
- `conacq/algorithms/quacq/findscope.py` — find_scope(), _prune_rejecting_partial()
- `conacq/algorithms/quacq/findc.py` — find_c(), _narrow_with_pool(), _narrow_with_sat()
- `conacq/example_generators/query_generator.py` — generate(), generate_with_priority()

## Implementation Steps

### Step 1: Update QueryGenerator.generate() signature

In `conacq/example_generators/query_generator.py`:

**Before** (line 56):
```python
def generate(self, task) -> Tuple[Optional[Dict[str, bool]], Any]:
```

**After**:
```python
def generate(self, task, remaining_bias: set, learned_kb: list) -> Tuple[Optional[Dict[str, bool]], Any]:
```

**Change line 67** from:
```python
logging.debug('QueryGenerator: KB=%d, Bias=%d, BG=%d',
              len(task.learned_kb), len(task.bias), len(task.set_b))
```
To:
```python
logging.debug('QueryGenerator: KB=%d, Bias=%d, BG=%d',
              len(learned_kb), len(remaining_bias), len(task.set_b))
```

**Change line 69** from:
```python
kb_clauses = task.get_kb_clauses()
```
To:
```python
kb_clauses = task.get_kb_clauses(learned_kb)
```

**Change line 71** from:
```python
for c_id in task.bias:
```
To:
```python
for c_id in remaining_bias:
```

**Update generate_with_priority() similarly** (lines 131-164):
- Add `remaining_bias` and `learned_kb` params
- Change `task.bias` refs to `remaining_bias`
- Change `task.get_kb_clauses()` to `task.get_kb_clauses(learned_kb)`

### Step 2: Update find_scope() signature

In `conacq/algorithms/quacq/findscope.py`:

**Add `remaining_bias` parameter** to `find_scope()` (line 21):
```python
def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        fm_clauses: List[List[int]],
        task,
        remaining_bias: set,          # NEW
        solver_name: str = 'glucose4',
        profiler: AbstractProfiler = None
) -> List[str]:
```

**Thread `remaining_bias` to recursive calls** (lines 73-74):
```python
S1 = find_scope(e, R | Y1, Y2, True, fm_clauses, task, remaining_bias, solver_name, profiler)
S2 = find_scope(e, R | set(S1), Y1, len(S1) > 0, fm_clauses, task, remaining_bias, solver_name, profiler)
```

**Update `_prune_rejecting_partial()`** (line 94):
```python
def _prune_rejecting_partial(task, remaining_bias: set, e: dict, R: set) -> None:
```

**Change line 107** from `for c_id in list(task.bias):` to `for c_id in list(remaining_bias):`.

**Change line 118** from `task.remove_from_bias(pruned)` to `remaining_bias -= set(pruned)`.

**Update call site** (line 59): pass `remaining_bias`.

### Step 3: Update find_c() signature

In `conacq/algorithms/quacq/findc.py`:

**Add `remaining_bias` and `record_query` params** (line 24):
```python
def find_c(
        e: dict,
        scope: set,
        task,
        remaining_bias: set,                              # NEW
        record_query,                                      # NEW: callback(config, answer, source)
        fm_clauses: List[List[int]],
        example_provider: Optional[ExampleProvider],
        solver_name: str = 'glucose4',
        query_mode: str = 'example_only',
        profiler: AbstractProfiler = None
):
```

**Update `_narrow_with_pool()`** (line 101): add `remaining_bias` and `record_query` params.

**Change line 127** from `task.record_query(disc_e, is_valid)` to `record_query(disc_e, is_valid, 'findc')`.

**Change lines 133-134** from:
```python
if c_id in task.bias:
    task.remove_from_bias([c_id])
```
To:
```python
if c_id in remaining_bias:
    remaining_bias.discard(c_id)
```

**Update `_narrow_with_sat()`** (line 146): add `record_query` param.

**Change line 172** from `task.record_query(disc_e, is_valid)` to `record_query(disc_e, is_valid, 'findc')`.

### Step 4: Update QuAcq.learn() — create local state

In `conacq/algorithms/quacq/quacq.py`:

**After** `start_time = time.perf_counter()` (line 176), add:
```python
remaining_bias = set(task.set_c)
learned_kb: List[int] = []
n_queries = 0
query_history: List[Tuple[Dict[str, bool], bool, str]] = []

def record_query(config: Dict[str, bool], answer: bool, source: str = 'main'):
    nonlocal n_queries
    n_queries += 1
    query_history.append((config.copy(), answer, source))
```

**Replace all task mutation calls in learn()**:

| Line | Before | After |
|------|--------|-------|
| 179 | `len(task.bias)` | `len(remaining_bias)` |
| 181 | `while task.bias:` | `while remaining_bias:` |
| 182 | `task.n_queries >= max_queries` | `n_queries >= max_queries` |
| 187 | `self.query_generator.generate(task)` | `self.query_generator.generate(task, remaining_bias, learned_kb)` |
| 195 | `task.record_query(query, answer)` | `record_query(query, answer)` |
| 198 | `task.n_queries` | `n_queries` |
| 207 | `task.add_to_kb(c_id)` | `if c_id not in learned_kb: learned_kb.append(c_id)` |
| 208 | `task.remove_from_bias(conflict)` | `remaining_bias -= set(conflict)` |
| 213 | `task.add_to_kb(tested_c_id)` | `if tested_c_id not in learned_kb: learned_kb.append(tested_c_id)` |
| 214 | `task.remove_from_bias([tested_c_id])` | `remaining_bias.discard(tested_c_id)` |
| 216 | `if not task.bias:` | `if not remaining_bias:` |
| 220 | `self._build_result(task, ...)` | `self._build_result(task, learned_kb, n_queries, query_history, remaining_bias, ...)` |

### Step 5: Update QuAcq.learn_from_examples() — same pattern

Same local state creation as learn(). Replace all task mutation calls. Thread `remaining_bias` and `record_query` into find_scope/find_c calls.

**Key call site changes** (lines 297-318):
```python
scope_vars = find_scope(
    e=query, R=set(), Y=all_variables,
    ask_query=False, fm_clauses=fm_clauses,
    task=task, remaining_bias=remaining_bias,
    solver_name=self.solver_name, profiler=self.profiler
)

c_id = find_c(
    e=query, scope=scope, task=task,
    remaining_bias=remaining_bias,
    record_query=record_query,
    fm_clauses=fm_clauses,
    example_provider=example_provider,
    solver_name=self.solver_name,
    query_mode=query_mode, profiler=self.profiler
)
```

### Step 6: Update _build_result() and _apply_reduce()

**Change _build_result() signature** (line 357):
```python
def _build_result(self, task: QuAcqTask, learned_kb: List[int],
                  n_queries: int, query_history: list,
                  remaining_bias: set,
                  start_time: float, convergence_reason: str,
                  description_provider: DescriptionProvider) -> QuAcqResult:
```

Replace `task.learned_kb` → `learned_kb`, `task.n_queries` → `n_queries`, `task.query_history` → `query_history`, `task.bias` → `remaining_bias`.

**Change _apply_reduce() signature** (line 395):
```python
def _apply_reduce(self, task, learned_kb: List[int]) -> List[int]:
```

Replace `task.learned_kb` → `learned_kb`.

### Step 7: Update _prune_rejecting_constraints()

**Change signature** (line 424):
```python
def _prune_rejecting_constraints(self, task: QuAcqTask,
                                 remaining_bias: set,
                                 positive_example: Dict[str, bool]) -> List[int]:
```

**Change line 432** from `for aid in list(task.bias):` to `for aid in list(remaining_bias):`.

**Remove line 437** (`task.remove_from_bias(pruned)`) — caller handles removal.

### Step 8: Update _find_conflict()

**Change signature** (line 441):
```python
def _find_conflict(self, task: QuAcqTask,
                   remaining_bias: set,
                   negative_example: Dict[str, bool],
                   learned_kb: List[int]) -> List[int]:
```

**Change line 451** from `task.get_kb_clauses()` to `task.get_kb_clauses(learned_kb)`.

**Change line 457** from `list(task.bias)` to `list(remaining_bias)`.

## Todo List

- [ ] Update QueryGenerator.generate() to accept `remaining_bias`, `learned_kb`
- [ ] Update QueryGenerator.generate_with_priority() similarly
- [ ] Update find_scope() to accept and thread `remaining_bias`
- [ ] Update _prune_rejecting_partial() to use `remaining_bias` param
- [ ] Update find_c() to accept `remaining_bias` and `record_query` callback
- [ ] Update _narrow_with_pool() to use `remaining_bias` and `record_query`
- [ ] Update _narrow_with_sat() to use `record_query`
- [ ] Rewrite QuAcq.learn() with local state variables
- [ ] Rewrite QuAcq.learn_from_examples() with local state variables
- [ ] Update _build_result() to accept state as params
- [ ] Update _apply_reduce() to accept learned_kb as param
- [ ] Update _prune_rejecting_constraints() to accept remaining_bias
- [ ] Update _find_conflict() to accept remaining_bias and learned_kb
- [ ] Verify no remaining references to task.bias, task.learned_kb, task.n_queries, task.query_history

## Success Criteria

- `grep -r "task\.bias\|task\.learned_kb\|task\.n_queries\|task\.query_history\|task\.add_to_kb\|task\.remove_from_bias\|task\.record_query" conacq/` returns zero matches in source files
- QuAcq.learn() and learn_from_examples() produce identical results to pre-refactoring
- All mutable state is local to algorithm methods

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| FindScope/FindC signature changes break callers | High | Only 2 call sites (learn_from_examples) — update together |
| QueryGenerator backward compat | Medium | Only called from QuAcq + tests — update all |
| record_query callback complexity | Low | Simple closure, 3 lines |
| remaining_bias passed by reference | Low | Python sets are mutable — mutations visible to caller (desired behavior for FindScope/FindC pruning) |

## Security Considerations

None — pure refactoring, no I/O or auth changes.

## Next Steps

Phase 3 updates consumers (runner, CV, tests) and verifies all tests pass.
