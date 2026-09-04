# Phase 2: Update Algorithm Params & Callers

## Context Links

- [Impact Analysis](reports/impact-analysis.md)
- [Phase 1](phase-01-update-congen-task.md) (prerequisite)

## Overview

- **Priority**: High (required for tests to pass after phase 1)
- **Status**: complete
- **Description**: Rename `set_ne` parameter to `set_neg_tv` in ConGen, AcqMSS, Reduce APIs and update all caller sites.

## Key Insights

- `explanation/` algorithms (KBDiag, QuickXPlain) already use `set_neg_tv` as param name
- Renaming `set_ne` -> `set_neg_tv` in `acqmss/` algorithms aligns naming with `explanation/` layer
- All callers access `task.set_ne` — must change to `task.set_neg_tv`
- QuAcq passes `set_ne=[]` to Reduce — must change to `set_neg_tv=[]`

## Requirements

### Functional
- Rename `set_ne` param in ConGen.acquire(), AcqMSS.find_mss(), Reduce.reduce(), Reduce.find_non_redundant()
- Update all caller sites passing `set_ne=...`
- Update log messages referencing `NE=` to use consistent naming

### Non-Functional
- Parameter names consistent with `explanation/` layer conventions
- No behavioral changes

## Architecture

```
ConGen.acquire(set_b, set_bg, set_tc, set_neg_tv, neg_c_map, assumption_to_constraint)
  -> AcqMSS.find_mss(delta, set_b, set_neg_tv, set_e_pos, set_bg)
  -> Reduce.reduce(set_b_prime, set_neg_tv, set_bg, neg_map)
```

## Related Code Files

### Modify — Algorithm APIs
- `acqmss/algorithms/congen.py` — acquire() param + body refs
- `acqmss/algorithms/acqmss.py` — find_mss() param + body refs
- `acqmss/algorithms/reduce.py` — reduce() + find_non_redundant() param + body refs

### Modify — Caller Sites
- `acqmss/eval/congen_runner.py` — line 179
- `apps/run_congen.py` — line 129
- `acqmss/algorithms/interactive/quacq.py` — line 436
- `acqmss/algorithms/congen.py` — internal calls to AcqMSS and Reduce (lines 128, 138)

## Implementation Steps

### Step 1: Rename in ConGen.acquire() (congen.py)

Replace all `set_ne` occurrences:
- Line 72: param `set_ne: Optional[List[int]] = None` -> `set_neg_tv`
- Line 86: docstring `set_ne:` -> `set_neg_tv:`
- Line 93: `set_ne = set_ne or []` -> `set_neg_tv = set_neg_tv or []`
- Line 98: log message `len(set_ne)` -> `len(set_neg_tv)`
- Line 102: `set_ne + set_bg` -> `set_neg_tv + set_bg`
- Line 128: `set_ne=set_ne` -> `set_neg_tv=set_neg_tv`
- Line 138: `set_ne=set_ne` -> `set_neg_tv=set_neg_tv`
- Line 162: `'n_ne': len(set_ne)` -> `'n_neg_tv': len(set_neg_tv)`
- Line 8: module docstring `ConGen receives pre-computed NE via task.set_ne` -> `task.set_neg_tv`

### Step 2: Rename in AcqMSS.find_mss() (acqmss.py)

Replace all `set_ne` occurrences:
- Line 52: param `set_ne: List` -> `set_neg_tv: List`
- Line 60: docstring `set_ne:` -> `set_neg_tv:`
- Line 68: log message
- Line 77: `set_b + set_ne + set_bg` -> `set_b + set_neg_tv + set_bg`
- Line 94: recursive call `set_ne` -> `set_neg_tv`
- Line 98: recursive call `set_ne` -> `set_neg_tv`

### Step 3: Rename in Reduce (reduce.py)

Replace all `set_ne` occurrences:
- Line 44: param `set_ne: List[int]` -> `set_neg_tv: List[int]`
- Line 53: docstring
- Line 60: log message
- Line 63: `set(set_ne)` -> `set(set_neg_tv)`
- Line 97: find_non_redundant param
- Line 100: forwarding call

### Step 4: Update caller sites

**congen_runner.py:179**:
```python
set_neg_tv=task.set_neg_tv,
```

**run_congen.py:129**:
```python
set_neg_tv=task.set_neg_tv,
```

**quacq.py:436**:
```python
set_neg_tv=[],
```

## Todo List

- [ ] Rename `set_ne` -> `set_neg_tv` in ConGen.acquire() (param, body, docstring, log)
- [ ] Rename `set_ne` -> `set_neg_tv` in AcqMSS.find_mss() (param, body, docstring, log)
- [ ] Rename `set_ne` -> `set_neg_tv` in Reduce.reduce() (param, body, docstring, log)
- [ ] Rename `set_ne` -> `set_neg_tv` in Reduce.find_non_redundant()
- [ ] Update congen_runner.py caller
- [ ] Update run_congen.py caller
- [ ] Update quacq.py caller (set_ne=[] -> set_neg_tv=[])
- [ ] Update ConGen internal calls to AcqMSS and Reduce

## Success Criteria

- All `set_ne` references in `acqmss/algorithms/` replaced with `set_neg_tv`
- `grep -r "set_ne" acqmss/` returns zero matches (excluding plan files)
- No import errors or attribute errors

## Risk Assessment

- **Low**: Mechanical rename. All params are keyword arguments at call sites.
- **Medium**: Must do phases 1 & 2 atomically or tests fail between phases.
  - **Mitigation**: Implement both phases in same commit.

## Security Considerations

- None

## Next Steps

Phase 3: Update tests and documentation.
