# Phase 2: Update Task and CONGEN

## Context Links

- Task: `acqmss/algorithms/task.py`
- CONGEN: `acqmss/algorithms/congen.py`
- Phase 1: `phase-01-modify-generate-ne.md`

## Overview

- **Priority**: P1 (blocks phases 3-5)
- **Status**: completed
- **Description**: Add `set_ne` field to `CONGENTask`. Simplify `CONGEN.acquire()` to use pre-computed `task.set_ne` instead of calling GenerateNE internally.

## Key Insights

- CONGEN currently: creates GenerateNE, calls generate(), updates task mappings, then runs ACQMSS/REDUCE
- After refactor: CONGEN assumes `task.set_ne`, `task.neg_c_map`, `task.assumption_to_constraint` are already populated by caller
- CONGEN becomes simpler: just ACQMSS + REDUCE (steps 3-9 of paper algorithm)
- `e_neg_literals` and `next_assumption_id` fields in task become unused by CONGEN (but kept for callers)

## Requirements

### Functional
- `CONGENTask` gains `set_ne: List[int]` field (default empty)
- `CONGEN.acquire()` reads `task.set_ne` directly, no GenerateNE call
- CONGEN no longer imports or instantiates GenerateNE

### Non-functional
- `CONGENTask` backward compatible (set_ne defaults to empty list)

## Architecture

```
Before: CONGEN.acquire(task) -> GenerateNE -> ACQMSS -> REDUCE
After:  CONGEN.acquire(task) -> ACQMSS(task.set_ne) -> REDUCE(task.set_ne)
```

## Related Code Files

- **Modify**: `acqmss/algorithms/task.py`
- **Modify**: `acqmss/algorithms/congen.py`

## Implementation Steps

### Step 1: Add `set_ne` field to `CONGENTask` in `task.py`

```python
@dataclass
class CONGENTask(TestCaseTask):
    """Base task for ConGen algorithm.
    ...
    Additional ConGen-specific fields:
    - set_ne: NE assumption IDs (pre-computed by caller)
    - e_neg_literals: Raw E- literals for GenerateNE (used by callers)
    ...
    """
    set_ne: List[int] = field(default_factory=list)                  # NEW
    e_neg_literals: List[List[int]] = field(default_factory=list)
    assumption_to_constraint: Dict[int, str] = field(default_factory=dict)
    constraint_to_assumption: Dict[str, int] = field(default_factory=dict)
    next_assumption_id: int = 1000
```

### Step 2: Simplify `CONGEN.acquire()` in `congen.py`

Remove the entire GenerateNE block (lines 86-101 in current code). Replace with reading `task.set_ne`.

**Remove** these lines from `acquire()`:

```python
# Step 1: NE <- GENERATENE(E-)
generate_ne = GenerateNE(self.checker, self.profiler)
ne_result = generate_ne.generate(
    set_tv=task.e_neg_literals,
    set_bg=task.set_b,
    start_assumption_id=task.next_assumption_id
)

set_ne = ne_result.assumption_ids
# Update task mappings for result formatting
for ne_id in ne_result.assumption_ids:
    task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"

# Merge NE neg_map into task for REDUCE
task.neg_c_map.update(ne_result.neg_map)

logging.debug('GENERATENE: %d NE constraints', len(set_ne))
```

**Replace** with:
```python
# NE is pre-computed by caller and stored in task.set_ne
set_ne = task.set_ne
logging.debug('Using pre-computed NE: %d constraints', len(set_ne))
```

### Step 3: Update logging in `acquire()`

Change the opening log line to not reference `e_neg_literals`:

```python
logging.debug('>>> ConGen [B=%d, NE=%d, E+=%d, BG=%d]',
              len(task.set_c), len(task.set_ne),
              len(task.set_tc), len(task.set_b))
```

### Step 4: Remove unused imports from `congen.py`

Remove:
```python
from .generate_ne import GenerateNE, NEResult
```

Keep `NEResult` import if needed elsewhere; check and remove if unused.

### Step 5: Update `congen.py` docstring

Update module and class docstrings to reflect new flow:
- Module: "CONGEN receives pre-computed NE via task.set_ne"
- Method: Remove "1: NE <- GENERATENE(E-)" from algorithm reference, note NE is pre-computed
- Update `acquire()` docstring Args to mention `task.set_ne`

### Step 6: Update metadata in `CONGENResult`

The metadata dict currently sets `n_e_neg` from `task.e_neg_literals`. Keep it but note it may be 0 if caller doesn't populate e_neg_literals. Update:

```python
metadata={
    'n_ne': len(set_ne),
    'n_e_pos': len(task.set_tc),
}
```

Remove `n_e_neg` from metadata since CONGEN no longer knows about raw E- literals.

## Todo List

- [ ] Add `set_ne: List[int]` field to `CONGENTask` (before `e_neg_literals`)
- [ ] Remove GenerateNE instantiation and call from `CONGEN.acquire()`
- [ ] Use `task.set_ne` directly in `acquire()`
- [ ] Remove `GenerateNE` import from `congen.py`
- [ ] Update logging lines
- [ ] Update module/class/method docstrings
- [ ] Update metadata dict (remove `n_e_neg`)

## Success Criteria

- `CONGEN.acquire()` no longer calls `GenerateNE`
- `CONGEN.acquire()` reads `task.set_ne` for NE assumption IDs
- No import of `GenerateNE` in `congen.py`
- `CONGENTask` has `set_ne` field

## Risk Assessment

- **Medium risk**: Callers (phase 3) must populate `task.set_ne` before calling `CONGEN.acquire()`
- **Mitigation**: Phase 3 implements this immediately; tests will catch if set_ne is empty
- After this phase, existing callers will break until phase 3 is applied

## Security Considerations

None -- internal refactoring only.

## Next Steps

Phase 3: Update callers (`run_congen.py`, `congen_runner.py`) to run GenerateNE before CONGEN and populate `task.set_ne`.
