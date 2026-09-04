# Phase 3: Simplify Algorithms (Remove _is_incremental)

## Context Links
- [Phase 2: Task Unification](phase-02-task-unification.md)
- Source: `acqmss/algorithms/congen.py`, `acqmss/algorithms/generate_ne.py`
- Source: `acqmss/algorithms/acqmss.py`, `acqmss/algorithms/reduce.py`

## Overview
- **Priority**: High
- **Status**: COMPLETE
- **Description**: Remove all `_is_incremental` branching from CONGEN,
  GenerateNE, ACQMSS, Reduce. Algorithms become mode-agnostic since both
  modes now use assumption IDs.

## Key Insights
- After Phase 2, both modes produce identical data structures:
  `set_c`, `set_b`, `set_tc`, `set_ne` are all `List[int]`.
  `neg_c_map` is `Dict[int, int]`.
- `CONGEN.acquire()` has branches for incremental vs non-incremental
  at lines 126-137 (NE handling) and lines 197-207 (BG extraction).
  These collapse into one path.
- `GenerateNE.generate()` has two branches (lines 108-170):
  incremental adds clauses to solver, non-incremental stores clause lists.
  Both now use `checker.add_clause()` + `checker.add_assumption()`.
- `Reduce.reduce()` has `isinstance(c, list)` branching (lines 113-124)
  plus `name_lookup`, `clauses_to_id`, `id_to_neg_clauses` params.
  All removed -- `c` is always `int`, `neg_c_map[c]` is always `int`.
- `ACQMSS.find_mss()` is already mode-agnostic (operates on lists).
  No changes needed.

## Requirements
1. Remove `_is_incremental` property/checks from CONGEN, GenerateNE
2. GenerateNE uses `checker.add_clause()` + `checker.add_assumption()`
3. Reduce accepts only `neg_map: Dict[int, int]`, no side maps
4. Remove `name_lookup`, `clauses_to_id`, `id_to_neg_clauses` params
5. Remove `_to_hashable()` from reduce.py (no longer needed)

## Related Code Files
- **Modify**: `acqmss/algorithms/congen.py` -- `CONGEN` class
- **Modify**: `acqmss/algorithms/generate_ne.py` -- `GenerateNE`, `NEResult`
- **Modify**: `acqmss/algorithms/reduce.py` -- `Reduce`
- **No change**: `acqmss/algorithms/acqmss.py` -- already mode-agnostic

## Implementation Steps

### Step 1: Simplify `NEResult` dataclass
File: `acqmss/algorithms/generate_ne.py`

Remove non-incremental-only fields:
```python
@dataclass
class NEResult:
    """Result of NE generation."""
    assumption_ids: List[int]      # NE assumption IDs
    neg_map: Dict[int, int]        # original_id -> negated_id
    original_literals: List[List[int]]  # raw literals for debugging
```

Remove `clause_lists`, `ne_names`, `id_to_clauses`, `id_to_neg_clauses`,
`clauses_to_id` -- no longer needed.

### Step 2: Simplify `GenerateNE.generate()`
File: `acqmss/algorithms/generate_ne.py`

Remove `_is_incremental` branching. Single unified path:

```python
def generate(self, set_e_neg, set_bg,
             start_assumption_id=1000) -> NEResult:
    assumption_ids = []
    neg_map = {}
    original_literals = []
    current_id = start_assumption_id

    for e_neg in set_e_neg:
        if not e_neg:
            continue

        # QuickXPlain: pass literals directly as assumption IDs
        minimal_conflict = self.quickxplain.find_conflict(e_neg, set_bg)
        if len(minimal_conflict) == 0:
            minimal_conflict = e_neg

        original_literals.append(minimal_conflict)

        # Blocking clause: -(l1 ^ l2 ^ ...) = (-l1 v -l2 v ...)
        blocking_clause = [-lit for lit in minimal_conflict]

        # Add with assumption via checker interface
        assumption_id = current_id
        current_id += 1
        self.checker.add_clause([-assumption_id] + blocking_clause)
        self.checker.add_assumption(assumption_id)

        # Negated form for REDUCE
        neg_assumption_id = current_id
        current_id += 1
        for lit in minimal_conflict:
            self.checker.add_clause([-neg_assumption_id, lit])
        self.checker.add_assumption(neg_assumption_id)

        assumption_ids.append(assumption_id)
        neg_map[assumption_id] = neg_assumption_id

    return NEResult(
        assumption_ids=assumption_ids,
        neg_map=neg_map,
        original_literals=original_literals
    )
```

Remove `start_synthetic_id` param, remove `clause_lists`/`ne_names` tracking.

### Step 3: Remove `_is_incremental` from `GenerateNE.__init__`
Remove the property entirely. GenerateNE no longer cares about mode.

### Step 4: Simplify `CONGEN.acquire()`
File: `acqmss/algorithms/congen.py`

Remove `_is_incremental` branching. Unified path:

```python
# Step 1: GenerateNE
generate_ne = GenerateNE(self.checker, self.profiler)
ne_result = generate_ne.generate(
  set_tv=task.e_neg_literals,
  set_bg=task.set_b,
  start_assumption_id=task.next_assumption_id
)
set_ne = ne_result.assumption_ids

# Update task mappings
for ne_id in ne_result.assumption_ids:
  task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"
task.neg_c_map.update(ne_result.neg_map)

# Step 2: Check E+ consistency
inconsistent = self.checker.is_consistent_test_cases(
  set_ne + task.set_b, task.set_tc, stop_at_first_violation=True)

# Step 3: AcqMSS
b_prime = acqmss.find_mss(
  delta=[], set_b=task.set_c, set_ne=set_ne,
  set_tc=task.set_tc, set_bg=task.set_b)

# Step 4: REDUCE (simplified call)
redundant, kb = reduce.reduce(
  set_b_prime=b_prime, set_ne=set_ne,
  set_bg=task.set_b, neg_map=task.neg_c_map)

# BG extraction (unified)
bg_clauses = [[lit] for lit in task.set_b]
```

Remove `_is_incremental` property from CONGEN class.

### Step 5: Simplify `Reduce.reduce()`
File: `acqmss/algorithms/reduce.py`

Remove `name_lookup`, `clauses_to_id`, `id_to_neg_clauses` params.
Remove `isinstance(c, list)` branching:

```python
def reduce(self, set_b_prime, set_ne, set_bg,
           neg_map: Dict[int, int]) -> Tuple[List, List]:
    kb = _unique_union(set_b_prime, set_ne)
    kb_delta = kb.copy()
    redundant = []

    for c in kb:
        if c not in kb_delta:
            continue
        kb_without_c = diff(kb_delta, [c])

        if c not in neg_map:
            logging.warning('No negated form for %s, skipping', c)
            continue
        neg_c = neg_map[c]

        # Check: inconsistent(BG u (KB-{c}) u {-c})
        test_set = set_bg + kb_without_c + [neg_c]
        is_consistent = self.checker.is_consistent(test_set)

        if not is_consistent:
            kb_delta.remove(c)
            redundant.append(c)

    return redundant, kb_delta
```

### Step 6: Simplify `Reduce.find_non_redundant()`
```python
def find_non_redundant(self, set_b_prime, set_ne, set_bg,
                       neg_map: Dict[int, int]):
    _, non_redundant = self.reduce(
        set_b_prime, set_ne, set_bg, neg_map)
    return non_redundant
```

### Step 7: Remove `_to_hashable()` from reduce.py
Only keep if `_unique_union()` still needs it. If all elements are now `int`,
`_unique_union` can use simple set operations. Simplify accordingly.

### Step 8: Remove `_is_incremental` property from CONGEN
File: `acqmss/algorithms/congen.py`

Remove the property and the `isinstance(self.checker, IncrementalPySATChecker)`
check.

## Todo List
- [x] Simplify `NEResult` dataclass
- [x] Rewrite `GenerateNE.generate()` -- single path using `add_clause()`
- [x] Remove `_is_incremental` from GenerateNE
- [x] Simplify `CONGEN.acquire()` -- remove mode branching
- [x] Remove `_is_incremental` from CONGEN
- [x] Simplify `Reduce.reduce()` -- remove side map params
- [x] Simplify `Reduce.find_non_redundant()`
- [x] Clean up `_to_hashable()`, `_unique_union()` in reduce.py
- [x] Verify ACQMSS needs no changes

## Success Criteria
- Zero `_is_incremental` checks in CONGEN, GenerateNE, Reduce
- Zero `isinstance(c, list)` branching in Reduce
- `neg_c_map` consumed as `Dict[int, int]` everywhere
- Algorithms work identically regardless of checker type

## Risk Assessment
- **QuickXPlain in GenerateNE**: currently has incremental vs non-incremental
  branching for `qx_set_c` format. After unification, QX always receives
  assumption IDs (ints). Verify QX handles int lists correctly.
- **`_unique_union` with ints**: much simpler -- can use `set()` directly.
  But verify no edge cases with int dedup.
