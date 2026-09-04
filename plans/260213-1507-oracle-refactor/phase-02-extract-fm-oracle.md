# Phase 02: Extract FeatureModelOracle to fm_oracle.py

## Context Links
- Research: [Oracle Code Analysis](research/researcher-01-oracle-code-analysis.md) (lines 46-82)
- Current impl: `acqmss/oracle/oracle.py:59-363` (305 LOC)
- New base: `acqmss/oracle/base.py` (from Phase 01)

## Overview

**Priority**: P1 (blocks all other phases)
**Status**: Complete
**Effort**: 1h

Extract `FeatureModelOracle` from `oracle.py` to `fm_oracle.py`, inherit from unified `Oracle` ABC.

## Key Insights

1. **FM-specific coupling**: Uses flamapy (UVLReader, FmToPysat, AST parsing)
2. **Persistent SAT solver**: Maintains glucose4 instance for incremental queries
3. **Feature ID authority**: Flamapy traversal order determines variable IDs (MUST preserve)
4. **FM-specific methods**: `get_root_feature()`, `get_cnf_clauses()`, `get_constraint_descriptions()`, `get_leaf_features()`
5. **Generic oracle interface**: `is_valid()`, `get_features()`, `get_feature_ids()` from ABC
6. **No need for `classify()`**: Used internally for `Example` objects, not part of public interface

## Requirements

### Functional
- Move `FeatureModelOracle` to `fm_oracle.py`
- Inherit from `base.Oracle` (not old `Oracle`)
- Implement three abstract methods from ABC
- Preserve all FM-specific methods
- Keep feature ID generation logic unchanged
- Maintain persistent solver behavior
- Remove `classify()` entirely — inline logic where used
<!-- Updated: Validation Session 1 - classify() removed entirely per user decision -->

### Non-Functional
- File ~280 LOC acceptable (current: 305 LOC, target: ~280 LOC after classify() removal)
<!-- Updated: Validation Session 1 - 280 LOC accepted, no further splitting -->
- Full type hints
- Strict mypy compliance
- No behavior changes

## Architecture

### Class Structure

```python
# acqmss/oracle/fm_oracle.py
from pathlib import Path
from typing import Dict, List, Optional, Set
from pysat.solvers import Solver
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from conacq.oracle.base import Oracle


class FeatureModelOracle(Oracle):
    """FM-based oracle using SAT solver for validation.

    Loads feature model from .uvl file, converts to CNF, and validates
    configurations via persistent PySAT solver.
    """

    def __init__(self, fm_path: str | Path) -> None:
        """Initialize oracle from feature model.

        Args:
            fm_path: Path to .uvl feature model file
        """
        # ... initialization logic

    # Oracle ABC implementation (required)
    def is_valid(self, config: Dict[str, bool]) -> bool: ...

    def get_features(self) -> Set[str]: ...

    def get_feature_ids(self) -> Dict[str, int]: ...

    # FM-specific extensions (optional, not in ABC)
    def get_root_feature(self) -> str: ...

    def get_cnf_clauses(self) -> List[List[int]]: ...

    def get_num_constraints(self) -> int: ...

    def get_constraint_descriptions(self) -> Set[str]: ...

    def get_leaf_features(self) -> Set[str]: ...

    def get_valid_configuration(self, assumptions: List[int]) -> Optional[Dict[str, bool]]: ...

    # Internal helpers (private)
    def _load_fm(self, fm_path: str | Path) -> None: ...

    def _extract_features(self) -> None: ...

    def _extract_leaf_features(self) -> None: ...

    def _build_feature_ids(self) -> None: ...

    def _build_cnf(self) -> None: ...

    def _parse_ctc_to_description(self, ctc) -> Optional[str]: ...

    def _get_feature_name(self, ast_op) -> Optional[str]: ...
```

### State Management
```python
# Instance attributes
self.fm_path: str
self.fm: FeatureModel
self.features: Set[str]
self.leaf_features: Set[str]
self.feature_ids: Dict[str, int]
self.cnf_clauses: List[List[int]]
self.solver: Solver  # Persistent glucose4
```

## Related Code Files

### Create
- `acqmss/oracle/fm_oracle.py` — extracted FM oracle

### Read
- `acqmss/oracle/oracle.py:59-363` — source implementation
- `acqmss/oracle/base.py` — new ABC to inherit

### Delete (next phase)
- `acqmss/oracle/oracle.py` — remove entire file after extraction

## Implementation Steps

1. **Create fm_oracle.py**
   ```bash
   touch acqmss/oracle/fm_oracle.py
   ```

2. **Copy module docstring and imports**
   - Copy imports from `oracle.py:1-13`
   - Add `from acqmss.oracle.base import Oracle`
   - Remove old `from abc import ABC, abstractmethod`

3. **Copy `FeatureModelOracle` class**
   - Copy lines 59-363 from `oracle.py`
   - Change inheritance: `class FeatureModelOracle(Oracle):`
   - Remove `@abstractmethod` decorators (already satisfied by implementation)

4. **Remove classify() entirely**
   - Delete `classify()` method (lines ~160-180)
   - Find where classify() is called internally, inline the logic (SAT check + ExampleType return)
   - Do NOT keep as private method
<!-- Updated: Validation Session 1 - hard removal of classify() -->

5. **Update type hints**
   - Change `fm_path: str` to `fm_path: str | Path` for flexibility
   - Ensure all methods have return type annotations

6. **Verify feature ID generation preserved**
   - Check `_build_feature_ids()` uses flamapy traversal order
   - Ensure `get_feature_ids()` returns same mapping as before

7. **Verify syntax and types**
   ```bash
   python -m py_compile acqmss/oracle/fm_oracle.py
   mypy acqmss/oracle/fm_oracle.py --strict
   ```

8. **Test instantiation**
   ```python
   from conacq.oracle.fm_oracle import FeatureModelOracle
   oracle = FeatureModelOracle("data/fms/REAL-FM-1.uvl")
   assert oracle.get_variables()
   assert oracle.get_feature_ids()
   assert oracle.is_valid({})  # Should validate
   ```

## Todo List

- [ ] Create `acqmss/oracle/fm_oracle.py`
- [ ] Copy module docstring from `oracle.py`
- [ ] Import from `acqmss.oracle.base import Oracle`
- [ ] Copy all flamapy, pysat, acqmss imports
- [ ] Copy `FeatureModelOracle` class (lines 59-363)
- [ ] Change inheritance to `Oracle` (from base.py)
- [ ] Remove or privatize `classify()` method
- [ ] Add type hints to `__init__` parameter
- [ ] Verify `_build_feature_ids()` logic unchanged
- [ ] Verify `is_valid()`, `get_features()`, `get_feature_ids()` satisfy ABC
- [ ] Run `python -m py_compile acqmss/oracle/fm_oracle.py`
- [ ] Run `mypy acqmss/oracle/fm_oracle.py --strict`
- [ ] Test instantiation with sample FM

## Success Criteria

- [x] `fm_oracle.py` exists with `FeatureModelOracle` class
- [x] Inherits from `base.Oracle`
- [x] Implements three abstract methods: `is_valid()`, `get_features()`, `get_feature_ids()`
- [x] Preserves all FM-specific methods: `get_root_feature()`, `get_cnf_clauses()`, etc.
- [x] Feature ID generation logic unchanged (flamapy traversal order)
- [x] File under 200 LOC (or close)
- [x] Strict mypy passes
- [x] Can instantiate and query oracle

## Risk Assessment

**Medium risk** — large class extraction, must preserve behavior.

**Potential issues:**
1. **Feature ID inconsistency**: If `_build_feature_ids()` logic changes, breaks eval metrics
   - *Mitigation*: Copy logic exactly, verify with test FM
2. **Import circular dependencies**: If base.py imports fm_oracle.py
   - *Mitigation*: base.py has no concrete imports, only ABC
3. **Solver lifecycle**: Persistent solver must survive refactor
   - *Mitigation*: Copy `__init__`, `__del__` exactly

**Testing needs:**
- Verify feature IDs match old implementation for same FM
- Verify SAT queries return same results
- Verify CNF extraction identical

## Security Considerations

- File path validation: Ensure `fm_path` is valid .uvl file
- Solver resource cleanup: Ensure `__del__` releases solver

## Next Steps

**Immediate**: Phase 03 — Refactor `UserPromptOracle`, `CachedOracle`, `ExampleProvider` to separate files

**Dependencies**: Phase 03 can proceed after this phase completes
