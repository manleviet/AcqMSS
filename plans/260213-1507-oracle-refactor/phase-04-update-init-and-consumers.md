# Phase 04: Update __init__.py, All Consumers, and Delete Old Files

<!-- Updated: Validation Session 1 - Collapsed old phases 04+05, hard removal (no deprecation aliases) -->

## Context Links
- Consumer analysis: [Oracle References](research/researcher-02-oracle-references.md)
- Current __init__.py: `acqmss/oracle/__init__.py`

## Overview

**Priority**: P1 (critical — atomic update)
**Status**: Complete
**Effort**: 2h

Atomic phase: rewrite `__init__.py` with new imports (no aliases), update all 14 consumer files, delete old `oracle.py` and `interactive.py`.

## Key Insights

1. **Hard removal**: No `InteractiveOracle` or `AutomatedOracle` aliases — clean break
2. **14 consumer files** must update simultaneously
3. **Method names preserved**: `ask()` and `is_valid()` both available on unified `Oracle`
4. **Factory methods unchanged**: `InteractiveLearner.from_files()` still works
5. **Attribute access change**: `oracle.fm_oracle.cnf_clauses` → `oracle.cnf_clauses` (FeatureModelOracle direct)

## Requirements

### Functional
- Rewrite `__init__.py` with clean imports from new modules
- No `__getattr__()` — no deprecated aliases
- Update all consumer imports: `InteractiveOracle` → `Oracle`, `AutomatedOracle` → `FeatureModelOracle`
- Update attribute access: remove `.fm_oracle.` indirection
- Delete `oracle.py` and `interactive.py`

### Non-Functional
- Zero references to `InteractiveOracle`/`AutomatedOracle` in codebase after update
- All tests pass
- Mypy strict compliance

## Architecture

### New __init__.py (no aliases)
```python
# acqmss/oracle/__init__.py
"""Oracle package for constraint acquisition."""

from .base import Oracle
from .fm_oracle import FeatureModelOracle
from .user_prompt import UserPromptOracle
from .cached import CachedOracle
from .example_provider import ExampleProvider
from .extractor import OracleData

__all__ = [
    'Oracle',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    'ExampleProvider',
    'OracleData',
]
```

### Import Migration Patterns

**Pattern 1**: `InteractiveOracle` → `Oracle` (type hints)
```python
# Before: from acqmss.oracle import InteractiveOracle
# After:  from acqmss.oracle import Oracle
```

**Pattern 2**: `AutomatedOracle` → `FeatureModelOracle` (instantiation)
```python
# Before: oracle = AutomatedOracle(fide_fm_path)
# After:  oracle = FeatureModelOracle(fide_fm_path)
```

**Pattern 3**: Remove `.fm_oracle.` indirection
```python
# Before: oracle.fm_oracle.cnf_clauses
# After:  oracle.cnf_clauses  (FeatureModelOracle has direct access)
```

## Related Code Files

### Modify
1. `acqmss/oracle/__init__.py` — complete rewrite
2. `acqmss/algorithms/interactive/quacq.py` — `InteractiveOracle` → `Oracle`
3. `acqmss/algorithms/interactive/learner.py` — `AutomatedOracle` → `FeatureModelOracle`, remove `.fm_oracle.`
4. `acqmss/algorithms/interactive/findc.py` — verify (only imports ExampleProvider)
5. `acqmss/oracle/extractor.py` — update import path
6. `apps/run_interactive_eval.py` — verify factory usage
7. `apps/run_congen.py` — verify (already uses FeatureModelOracle)
8. `apps/run_congen_eval.py` — verify
9. `apps/generate_examples.py` — verify
10. `acqmss/testcases/generators/base.py` — verify
11. `acqmss/testcases/generators/nwise_coverage.py` — verify
12. `acqmss/testcases/generators/feature_frequency.py` — verify
13. `tests/test_interactive.py` — `AutomatedOracle` → `FeatureModelOracle`
14. `tests/test_congen.py` — verify

### Delete
- `acqmss/oracle/oracle.py` — old Oracle ABC + FeatureModelOracle
- `acqmss/oracle/interactive.py` — old InteractiveOracle + AutomatedOracle + helpers

## Implementation Steps

### Step 1: Rewrite __init__.py
- Remove all old imports
- Import from new modules (base, fm_oracle, user_prompt, cached, example_provider, extractor)
- Define clean `__all__` — no deprecated names
- No `__getattr__()` function

### Step 2: Update QuAcq consumers
- `quacq.py`: `InteractiveOracle` → `Oracle` in imports and type hints
- `learner.py`: `AutomatedOracle` → `FeatureModelOracle`, `InteractiveOracle` → `Oracle`
- `learner.py`: Change `oracle.fm_oracle.cnf_clauses` → `oracle.cnf_clauses`
- `findc.py`: Verify ExampleProvider import still works

### Step 3: Update Oracle package internal
- `extractor.py`: Update `from .oracle import FeatureModelOracle` → `from .fm_oracle import FeatureModelOracle`

### Step 4: Update apps
- Grep each app for deprecated names
- Most use factory methods — likely no changes needed
- Update any direct `AutomatedOracle`/`InteractiveOracle` references

### Step 5: Update generators
- Verify `Oracle` base type imports work
- Most already use `Oracle` — likely no changes

### Step 6: Update tests
- `test_interactive.py`: `AutomatedOracle` → `FeatureModelOracle`
- `test_congen.py`: Verify imports

### Step 7: Delete old files
```bash
rm acqmss/oracle/oracle.py
rm acqmss/oracle/interactive.py
```

### Step 8: Verify no references remain
```bash
grep -r "InteractiveOracle\|AutomatedOracle" acqmss/ apps/ tests/ --include="*.py"
# Should return ZERO results
```

### Step 9: Type check and test
```bash
PYTHONPATH=. mypy acqmss/oracle/ --strict
PYTHONPATH=. pytest tests/ -v
```

## Todo List

### __init__.py
- [ ] Rewrite with clean imports from new modules
- [ ] Define `__all__` (6 names, no deprecated)
- [ ] No `__getattr__()` function

### QuAcq consumers
- [ ] quacq.py: `InteractiveOracle` → `Oracle`
- [ ] learner.py: `AutomatedOracle` → `FeatureModelOracle`
- [ ] learner.py: `InteractiveOracle` → `Oracle`
- [ ] learner.py: Remove `.fm_oracle.` indirection
- [ ] findc.py: Verify ExampleProvider import

### Oracle internal
- [ ] extractor.py: Update FeatureModelOracle import path

### Apps
- [ ] run_interactive_eval.py: Check for deprecated names
- [ ] run_congen.py: Verify imports
- [ ] run_congen_eval.py: Verify imports
- [ ] generate_examples.py: Verify imports

### Generators
- [ ] base.py: Verify Oracle import
- [ ] nwise_coverage.py: Verify imports
- [ ] feature_frequency.py: Verify imports

### Tests
- [ ] test_interactive.py: `AutomatedOracle` → `FeatureModelOracle`
- [ ] test_congen.py: Verify imports

### Cleanup
- [ ] Delete `oracle.py`
- [ ] Delete `interactive.py`
- [ ] Grep verify zero deprecated references
- [ ] Run mypy strict
- [ ] Run all tests

## Success Criteria

- [x] Zero references to `InteractiveOracle` in codebase
- [x] Zero references to `AutomatedOracle` in codebase
- [x] Old `oracle.py` and `interactive.py` deleted
- [x] All imports use new structure
- [x] All tests pass
- [x] No runtime errors

## Risk Assessment

**Medium risk** — many files update atomically.

**Mitigations:**
1. Grep verification after each batch of updates
2. Run tests incrementally (2-3 files, then test)
3. Git commit after successful test run — easy rollback

## Security Considerations

None — import changes only.

## Next Steps

**Immediate**: Phase 05 — Testing and comprehensive validation
