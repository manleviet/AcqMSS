# Phase 3: Update References, Tests, Exports, Docs

## Context

- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-merge-explanation-strategies.md), [Phase 2](phase-02-merge-congen-strategies.md)

## Overview

- **Date**: 2026-02-13
- **Priority**: P1
- **Description**: Update all references to removed classes, update exports, run tests, update docs
- **Implementation status**: complete
- **Review status**: complete

## Key Insights

1. Strategy classes in `explanation/models/` are NOT exported — only used via `TaskPreparationFactory`
2. CONGEN strategy classes ARE exported from `acqmss/algorithms/__init__.py` and used directly in:
   - `apps/run_congen.py` (lines 27-28, 151-153)
   - `acqmss/eval/congen_runner.py` (lines 20-21, 170-172)
   - `tests/test_congen.py` (lines 17-18, 103-105)
3. Pattern at call sites: `if incremental: Incremental...() else: NonIncremental...()`  → replace with `CONGENTaskPreparation(mode_name)`

## Requirements

- All references to old class names updated
- `__init__.py` exports updated
- All tests pass (219 tests)
- Docs updated to reflect new structure

## Related Code Files

| File | Action |
|------|--------|
| `acqmss/algorithms/__init__.py` | Replace 2 exports → 1 (`CONGENTaskPreparation`) |
| `acqmss/eval/congen_runner.py` | Update import + usage |
| `apps/run_congen.py` | Update import + usage |
| `tests/test_congen.py` | Update import + usage |
| `tests/test_diagnosis.py` | Check for references (likely none) |
| `docs/codebase-summary.md` | Update strategy class descriptions |
| `docs/system-architecture.md` | Update strategy class descriptions |

## Implementation Steps

### Step 1: Update `acqmss/algorithms/__init__.py`

```python
# Before:
from .task_preparation import (
    IncrementalCONGENTaskPreparation,
    NonIncrementalCONGENTaskPreparation
)
# After:
from .task_preparation import CONGENTaskPreparation
```

Update `__all__` accordingly.

### Step 2: Update call sites (3 files, same pattern)

Each file has this pattern:
```python
# Before:
if incremental:
    preparation = IncrementalCONGENTaskPreparation()
else:
    preparation = NonIncrementalCONGENTaskPreparation()

# After:
mode = "incremental-congen_root" if incremental else "non-incremental-congen_root"
preparation = CONGENTaskPreparation(mode)
```

Files: `apps/run_congen.py`, `acqmss/eval/congen_runner.py`, `tests/test_congen.py`

### Step 3: Run tests

```bash
PYTHONPATH=. python -m pytest tests/test_diagnosis.py tests/test_congen.py -v --tb=short
```

Expected: 219 passed, 0 failed.

### Step 4: Update docs

Spawn `docs-manager` subagent to update:
- `docs/codebase-summary.md` — strategy class names
- `docs/system-architecture.md` — strategy hierarchy

### Step 5: Code review

Spawn `code-reviewer` subagent.

## Todo List

- [x] Update `acqmss/algorithms/__init__.py` exports
- [x] Update `apps/run_congen.py`
- [x] Update `acqmss/eval/congen_runner.py`
- [x] Update `tests/test_congen.py`
- [x] Check `tests/test_diagnosis.py` for references
- [x] Run full test suite
- [x] Update docs
- [x] Code review

## Success Criteria

- No references to old class names (`Incremental*Preparation`, `NonIncremental*Preparation`) anywhere in codebase
- 219 tests pass
- Docs reflect new 3-class structure

## Risk Assessment

- **Low**: Simple rename at call sites
- **Medium**: If tests parameterize incremental/non-incremental with different preparation classes — need to update test parametrization

## Security Considerations

None.

## Next Steps

- Ask user to commit
