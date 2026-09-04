# Phase 1: Create Oracle Package and Move Files

## Context Links
- Source 1: `acqmss/testcases/oracle.py` (Oracle ABC + FeatureModelOracle)
- Source 2: `acqmss/algorithms/interactive/user_interface.py` (InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider)
- Code standards: `docs/code-standards.md`

## Overview
- **Priority**: P3
- **Status**: complete
- **Description**: Create `acqmss/oracle/` package, copy source files, fix internal imports within moved files.

## Key Insights
- `oracle.py` imports from `acqmss.testcases.data_structures` (Example, ExampleType) — must update to absolute import
- `user_interface.py` imports `from acqmss.testcases.oracle import FeatureModelOracle` — must become sibling import `from .oracle import FeatureModelOracle`
- No circular dependencies: oracle depends on data_structures (testcases), not vice versa

## Related Code Files

**Create:**
- `acqmss/oracle/__init__.py`
- `acqmss/oracle/oracle.py` (copy of `acqmss/testcases/oracle.py`)
- `acqmss/oracle/interactive.py` (copy of `acqmss/algorithms/interactive/user_interface.py`)

## Implementation Steps

1. Create directory `acqmss/oracle/`

2. Copy `acqmss/testcases/oracle.py` → `acqmss/oracle/oracle.py`
   - Change import:
     ```python
     # OLD
     from .data_structures import Example, ExampleType
     # NEW
     from conacq.examples.data_structures import Example, ExampleType
     ```

3. Copy `acqmss/algorithms/interactive/user_interface.py` → `acqmss/oracle/interactive.py`
   - Change import:
     ```python
     # OLD
     from conacq.examples.oracle import FeatureModelOracle
     # NEW
     from .oracle import FeatureModelOracle
     ```

4. Create `acqmss/oracle/__init__.py`:
   ```python
   """
   Oracle package for constraint acquisition.

   Provides ground truth interfaces for classifying configurations:
   - Oracle: Abstract base class for configuration validation
   - FeatureModelOracle: Validates against a feature model (SAT-based)
   - InteractiveOracle: Abstract interface for membership queries
   - AutomatedOracle: Automated oracle using FeatureModelOracle
   - UserPromptOracle: Human-in-the-loop oracle
   - CachedOracle: Wrapper caching oracle answers
   - ExampleProvider: Provides examples for example-based learning
   """

   from .oracle import Oracle, FeatureModelOracle
   from .interactive import (
       InteractiveOracle,
       AutomatedOracle,
       UserPromptOracle,
       CachedOracle,
       ExampleProvider,
   )

   __all__ = [
       'Oracle',
       'FeatureModelOracle',
       'InteractiveOracle',
       'AutomatedOracle',
       'UserPromptOracle',
       'CachedOracle',
       'ExampleProvider',
   ]
   ```

5. Verify new package imports resolve:
   ```bash
   PYTHONPATH=. python -c "from acqmss.oracle import Oracle, FeatureModelOracle, AutomatedOracle, ExampleProvider"
   ```

## Todo List
- [x] Create `acqmss/oracle/` directory
- [x] Copy and fix `oracle.py` (update relative import to absolute)
- [x] Copy and fix `interactive.py` (update FeatureModelOracle import to sibling)
- [x] Create `__init__.py` with all re-exports
- [x] Verify imports resolve

## Success Criteria
- `from acqmss.oracle import Oracle, FeatureModelOracle` works
- `from acqmss.oracle import AutomatedOracle, ExampleProvider` works
- Old files still exist (not deleted yet — Phase 2)

## Risk Assessment
- **Low risk**: Phase 1 only adds files, doesn't modify existing code
- If import of `acqmss.testcases.data_structures` fails from new location, fix with absolute import path
