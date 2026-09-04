# Phase 02: Update All External References and Verify

## Context Links

- [Plan overview](plan.md)
- [Phase 01: Move files](phase-01-move-files.md)
- Depends on: Phase 01 completed

## Overview

- **Priority**: P2
- **Status**: pending
- **Description**: Update every file that imports `QueryGenerator` or `ExampleProvider` from old paths, remove old re-exports, update docs. Then run full test suite.

## Key Insights

- **7 code files** need import updates (3 `__init__.py` + 3 algorithm files + 1 test file)
- **1 doc file** has an example import referencing `ExampleProvider` from oracle
- No backward-compatibility re-exports; clean break (internal codebase only)
- `ExampleProvider` in `acqmss/oracle/__init__.py` docstring also needs update

## Requirements

### Functional
- All imports resolve to `acqmss.example_generators` as canonical path
- `acqmss.oracle` no longer exports `ExampleProvider`
- `acqmss.algorithms.interactive` no longer exports `QueryGenerator`
- All tests pass

### Non-functional
- No stale re-exports left behind
- Documentation reflects new import paths

## Architecture

Import dependency after refactoring:

```
acqmss/example_generators/
  ├── query_generator.py ──imports──> acqmss.algorithms.interactive.task
  └── example_provider.py ──imports──> (stdlib only)

acqmss/algorithms/interactive/
  ├── quacq.py ──imports──> acqmss.example_generators (QueryGenerator, ExampleProvider)
  ├── findc.py ──imports──> acqmss.example_generators (ExampleProvider)
  ├── learner.py ──imports──> acqmss.example_generators (ExampleProvider)
  └── __init__.py ──imports──> acqmss.example_generators (QueryGenerator, ExampleProvider)
```

## Related Code Files

| # | File | Change |
|---|------|--------|
| 1 | `acqmss/oracle/__init__.py` | Remove `ExampleProvider` import and `__all__` entry |
| 2 | `acqmss/algorithms/interactive/__init__.py` | Import `QueryGenerator`, `ExampleProvider` from `acqmss.example_generators` instead |
| 3 | `acqmss/algorithms/__init__.py` | No change needed (re-exports from interactive, which is updated) |
| 4 | `acqmss/algorithms/interactive/quacq.py` | `ExampleProvider` from `acqmss.example_generators`; `QueryGenerator` from `acqmss.example_generators` |
| 5 | `acqmss/algorithms/interactive/findc.py` | `ExampleProvider` from `acqmss.example_generators` |
| 6 | `acqmss/algorithms/interactive/learner.py` | Remove `ExampleProvider` from oracle import line |
| 7 | `tests/test_interactive.py` | No change needed (imports `QueryGenerator` from `acqmss.algorithms.interactive` which re-exports) |
| 8 | `docs/code-standards.md` | Update oracle import example (line 357) |

## Implementation Steps

### 1. Update `acqmss/oracle/__init__.py`

Remove ExampleProvider:

```python
# REMOVE this line:
from .example_provider import ExampleProvider

# REMOVE from __all__:
'ExampleProvider',
```

Update module docstring: remove `- ExampleProvider: Provides examples for example-based learning` line.

### 2. Update `acqmss/algorithms/interactive/__init__.py`

Change:

```python
# OLD (lines 46-52):
from conacq.oracle import (
    Oracle,
    FeatureModelOracle,
    UserPromptOracle,
    CachedOracle,
    ExampleProvider,
)
from .query_generator import QueryGenerator

# NEW:
from conacq.oracle import (
    Oracle,
    FeatureModelOracle,
    UserPromptOracle,
    CachedOracle,
)
from conacq.example_generators import QueryGenerator, ExampleProvider
```

`__all__` list stays the same (still re-exports both names for convenience).

### 3. Update `acqmss/algorithms/interactive/quacq.py`

Change lines 17-18:

```python
# OLD:
from conacq.oracle import Oracle, ExampleProvider
from .query_generator import QueryGenerator

# NEW:
from conacq.oracle import Oracle
from conacq.example_generators import QueryGenerator, ExampleProvider
```

### 4. Update `acqmss/algorithms/interactive/findc.py`

Change line 16:

```python
# OLD:
from conacq.oracle import ExampleProvider

# NEW:
from conacq.example_generators import ExampleProvider
```

### 5. Update `acqmss/algorithms/interactive/learner.py`

Change line 13:

```python
# OLD:
from conacq.oracle import Oracle, FeatureModelOracle, UserPromptOracle, ExampleProvider

# NEW:
from conacq.oracle import Oracle, FeatureModelOracle, UserPromptOracle
from conacq.example_generators import ExampleProvider
```

### 6. Update `docs/code-standards.md` (line 357)

```python
# OLD:
from conacq.oracle import Oracle, FeatureModelOracle, CachedOracle, ExampleProvider

# NEW:
from conacq.oracle import Oracle, FeatureModelOracle, CachedOracle
from conacq.example_generators import ExampleProvider
```

### 7. Verify no stale references

```bash
# Should return zero code hits (only docs/plans allowed):
grep -rn "from acqmss.oracle.*ExampleProvider" acqmss/ tests/
grep -rn "from .query_generator import" acqmss/algorithms/
grep -rn "from .example_provider import" acqmss/oracle/
```

### 8. Run full verification

```bash
# Import check
PYTHONPATH=. python -c "
from acqmss.example_generators import QueryGenerator, ExampleProvider
from acqmss.algorithms.interactive import QueryGenerator, ExampleProvider, QuAcq
from acqmss.algorithms import QueryGenerator
print('All imports OK')
"

# Full test suite
PYTHONPATH=. pytest tests/ -v
```

## Todo List

- [ ] Update `acqmss/oracle/__init__.py` -- remove ExampleProvider
- [ ] Update `acqmss/algorithms/interactive/__init__.py` -- new import sources
- [ ] Update `acqmss/algorithms/interactive/quacq.py` -- new import paths
- [ ] Update `acqmss/algorithms/interactive/findc.py` -- new import path
- [ ] Update `acqmss/algorithms/interactive/learner.py` -- new import path
- [ ] Update `docs/code-standards.md` -- oracle example import
- [ ] Verify no stale references with grep
- [ ] Run import smoke test
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/ -v`
- [ ] Update `docs/codebase-summary.md` -- move ExampleProvider from oracle table to example_generators, move QueryGenerator from interactive table

## Success Criteria

- `PYTHONPATH=. pytest tests/ -v` passes all tests
- Zero grep hits for old import paths in `acqmss/` and `tests/`
- `from acqmss.example_generators import QueryGenerator, ExampleProvider` works
- Re-exports from `acqmss.algorithms.interactive` and `acqmss.algorithms` still work (convenience paths)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed reference in untested code | Low | Medium | Comprehensive grep in step 7 catches stale imports |
| Circular import via re-exports | Low | Medium | `example_generators/__init__` has no dependency on `algorithms.interactive` |
| Test failure from import mismatch | Low | High | Run full suite in step 8 |

## Security Considerations

N/A -- pure import path refactoring, no logic changes.

## Next Steps

- After both phases pass, commit with message: `refactor(acqmss): move QueryGenerator and ExampleProvider to example_generators package`
- Update `docs/codebase-summary.md` to reflect new file locations
