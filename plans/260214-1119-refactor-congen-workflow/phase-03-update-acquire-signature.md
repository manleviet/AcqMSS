# Phase 03: Update ConGen.acquire() Signature

## Context Links

- Current: `acqmss/algorithms/congen.py` lines 66-156
- AcqMSS: `acqmss/algorithms/acqmss.py` — called by acquire(), no changes needed
- Reduce: `acqmss/algorithms/reduce.py` — called by acquire(), no changes needed
- ConGenTask: `acqmss/algorithms/task_preparation.py` lines 27-55

## Overview

- **Priority**: P1
- **Status**: completed
- **Description**: Change `ConGen.acquire()` from accepting `ConGenTask` to accepting direct parameters (`set_b`, `set_bg`, `set_tc`, `set_ne`). Internal logic uses params directly instead of task fields.

## Key Insights

- Current signature: `acquire(self, task: ConGenTask) -> CONGENResult`
- Target signature: `acquire(self, set_b, set_bg, set_tc, set_ne=None, neg_c_map=None, assumption_to_constraint=None) -> CONGENResult`
- Callers extract these from task anyway: `task.set_c`, `task.set_b`, `task.set_tc`, `task.set_ne`, `task.neg_c_map`
- AcqMSS.find_mss() already takes direct params (line 52): `find_mss(delta, set_b, set_ne, set_e_pos, set_bg)`
- Reduce.reduce() already takes direct params (line 44): `reduce(set_b_prime, set_ne, set_bg, neg_map)`
- The mapping `assumption_to_constraint` is only needed for result name resolution

## Requirements

### Functional
- `acquire()` takes `set_b` (bias), `set_bg` (background), `set_tc` (E+), `set_ne` (NE), `neg_c_map`, `assumption_to_constraint`
- Internal logic unchanged (AcqMSS, Reduce calls identical)
- CONGENResult still contains constraint names (via assumption_to_constraint)

### Non-functional
- Signature change is the primary breaking change for callers

## Architecture

```
# OLD
result = congen.acquire(task)
  # internally: task.set_c, task.set_b, task.set_tc, task.set_ne, task.neg_c_map

# NEW
result = congen.acquire(
    set_b=task.set_c,       # Bias constraints
    set_bg=task.set_b,      # Background knowledge
    set_tc=task.set_tc,     # Positive examples
    set_ne=task.set_ne,     # Negated examples
    neg_c_map=task.neg_c_map,
    assumption_to_constraint=task.assumption_to_constraint
)
```

**Naming rationale**: In ConGen's paper algorithm, `B` = bias candidates, `BG` = background, `E+` = positive examples, `NE` = negated examples. The task uses `set_c` for B and `set_b` for BG, which is confusing. The new signature uses clearer names matching the paper.

## Related Code Files

### Files to modify
- `acqmss/algorithms/congen.py` — change acquire() signature + internals

### Files NOT modified (this phase)
- `acqmss/algorithms/acqmss.py` — already takes direct params
- `acqmss/algorithms/reduce.py` — already takes direct params

## Implementation Steps

### Step 1: Update `acquire()` signature and body

Replace lines 66-156 of `congen.py`:

```python
@measure_time('congen_runtime')
@count_calls('congen_calls')
def acquire(
        self,
        set_b: List[int],
        set_bg: List[int],
        set_tc: List[int],
        set_ne: List[int] = None,
        neg_c_map: Dict[int, int] = None,
        assumption_to_constraint: Dict[int, str] = None
) -> CONGENResult:
  """Acquire knowledge base from bias constraints.

  Paper Algorithm 1 (steps 2-9, NE pre-computed):
  2. if IsConsistent(E+, NE, BG) then B' <- AcqMSS(...)
  3. return REDUCE(B', NE, BG)

  Args:
      set_b: Bias constraint assumption IDs (B)
      set_bg: Background knowledge assumption IDs (BG)
      set_tc: Positive example assumption IDs (E+)
      set_ne: Negated example assumption IDs (NE)
      neg_c_map: Mapping constraint ID -> negated ID (for REDUCE)
      assumption_to_constraint: Mapping assumption ID -> constraint name

  Returns:
      CONGENResult with acquired KB
  """
  set_ne = set_ne or []
  neg_c_map = neg_c_map or {}
  assumption_to_constraint = assumption_to_constraint or {}

  logging.debug('>>> ConGen [B=%d, NE=%d, E+=%d, BG=%d]',
                len(set_b), len(set_ne), len(set_tc), len(set_bg))

  # Step 3: if IsConsistent(E+, NE, BG) then
  inconsistent = self.checker.is_consistent_test_cases(
    set_ne + set_bg,  # NE ∪ BG
    set_tc,  # E+
    stop_at_first_violation=True
  )
  self.profiler.increment("paper_consistency_checks")

  if len(inconsistent) > 0:
    logging.debug('<<< ConGen return Phi (E+ inconsistent with NE ∪ BG)')
    bg_clauses = [[lit] for lit in set_bg]
    self.result = CONGENResult(
      kb_constraints=[],
      kb_assumption_ids=[],
      redundant_constraints=[],
      n_bias=len(set_b),
      n_mss=0,
      n_kb=0,
      bg_clauses=bg_clauses,
      metadata={'error': 'E+ inconsistent with NE ∪ BG'}
    )
    return self.result

  # Step 4: B' <- AcqMSS(empty, B, NE, E+, BG)
  acqmss = AcqMSS(self.checker, m=1, profiler_instance=self.profiler)
  b_prime = acqmss.find_mss(
    delta=[],
    set_b=set_b,
    set_ne=set_ne,
    set_tc=set_tc,
    set_bg=set_bg
  )
  logging.debug('AcqMSS: MSS size = %d', len(b_prime))

  # Step 9: return REDUCE(B', NE, BG)
  reduce = Reduce(self.checker, self.profiler)
  redundant, kb = reduce.reduce(
    set_b_prime=b_prime,
    set_ne=set_ne,
    set_bg=set_bg,
    neg_map=neg_c_map
  )
  logging.debug('REDUCE: %d redundant, %d in final KB', len(redundant), len(kb))

  # Map back to constraint names
  def _get_name(a):
    return assumption_to_constraint.get(a, f'unknown_{a}')

  kb_names = [_get_name(a) for a in kb]
  redundant_names = [_get_name(a) for a in redundant]

  bg_clauses = [[lit] for lit in set_bg]

  self.result = CONGENResult(
    kb_constraints=kb_names,
    kb_assumption_ids=kb,
    redundant_constraints=redundant_names,
    n_bias=len(set_b),
    n_mss=len(b_prime),
    n_kb=len(kb),
    bg_clauses=bg_clauses,
    metadata={
      'n_ne': len(set_ne),
      'n_e_pos': len(set_tc),
    }
  )

  logging.debug('<<< ConGen return KB=%d', len(kb))
  return self.result
```

### Step 2: Remove ConGenTask import

Remove unused import from congen.py:

```python
# REMOVE: from .task_preparation import ConGenTask
```

The file will still import AcqMSS, Reduce, ConsistencyChecker, profiler utils.

### Step 3: Keep `save_result()` unchanged

`save_result()` (lines 158-180) uses `self.result` — no changes needed.

## Todo List

- [ ] Change `acquire()` signature from `(task)` to `(set_b, set_bg, set_tc, set_ne, neg_c_map, assumption_to_constraint)`
- [ ] Update internal logic to use direct params
- [ ] Remove `ConGenTask` import
- [ ] Verify AcqMSS and Reduce calls match current behavior exactly
- [ ] Keep `save_result()` unchanged

## Success Criteria

- `acquire()` produces identical results to old version given same data
- All internal AcqMSS/Reduce calls pass same arguments as before
- CONGENResult structure unchanged
- No ConGenTask dependency in congen.py

## Risk Assessment

- **Risk**: Callers passing wrong param order (positional vs keyword)
  - **Mitigation**: Use keyword-only args after set_b; callers in Phase 04 use keywords
- **Risk**: Missing neg_c_map causes silent REDUCE failures
  - **Mitigation**: Default to empty dict; REDUCE handles missing negations with logging.warning

## Security Considerations

- No security impact

## Next Steps

- Phase 04 updates all callers to use new signature
