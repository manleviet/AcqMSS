# Phase 01: Define Unified Oracle ABC

## Context Links
- Research: [Oracle Code Analysis](research/researcher-01-oracle-code-analysis.md)
- Current impl: `acqmss/oracle/oracle.py:15-57`
- Interactive ABC: `acqmss/oracle/interactive.py:16-40`

## Overview

**Priority**: P1 (foundation for all other phases)
**Status**: Complete
**Effort**: 1h

Create unified `Oracle` ABC in `base.py` merging `Oracle` and `InteractiveOracle` concepts with consistent naming.

## Key Insights

1. **Overlapping abstractions**: `Oracle.is_valid()` ≈ `InteractiveOracle.ask()` — same membership query, different names
2. **Shared requirements**: Both need `get_features()`, `get_feature_ids()`, membership query
3. **QuAcq expects `ask()`**: 14 consumer files use `ask()` for interactive mode
4. **CONGEN expects `is_valid()`**: Generators and CONGEN use `is_valid()`
5. **Feature count vs features**: `get_feature_count()` redundant — can derive from `len(get_features())`

## Requirements

### Functional
- Merge `Oracle` + `InteractiveOracle` into single ABC
- Primary method: `is_valid(config)` for membership query
- Alias method: `ask(config)` delegates to `is_valid()` for backward compat
- Required abstracts: `is_valid()`, `get_features()`, `get_feature_ids()`
- Optional concrete: `ask()`, `get_feature_count()`

### Non-Functional
- File under 200 LOC (target: ~60 LOC)
- Full type hints (Python 3.13+)
- Docstrings for all public methods

## Architecture

### Base ABC Structure
```python
# acqmss/oracle/base.py
from abc import ABC, abstractmethod
from typing import Dict, Set

class Oracle(ABC):
    """Unified oracle interface for membership queries.

    Validates configurations against ground truth (FM, DB, API, etc).
    """

    @abstractmethod
    def is_valid(self, config: Dict[str, bool]) -> bool:
        """Check if configuration is valid.

        Args:
            config: Feature assignments {feature_name: bool}

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    def get_features(self) -> Set[str]:
        """Get all feature names."""
        pass

    @abstractmethod
    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping."""
        pass

    # Concrete methods with default implementations
    def ask(self, query: Dict[str, bool]) -> bool:
        """Alias for is_valid() (interactive compatibility)."""
        return self.is_valid(query)

    def get_feature_count(self) -> int:
        """Get number of features."""
        return len(self.get_features())
```

### Design Rationale

1. **`is_valid()` primary**: More descriptive than `ask()`, used by CONGEN/generators
2. **`ask()` alias**: Preserves QuAcq interface, no consumer changes needed
3. **`get_feature_count()` concrete**: Derived from `get_features()`, no need to abstract
4. **No `classify()` method**: Only used internally in `FeatureModelOracle`, not part of interface

## Related Code Files

### Create
- `acqmss/oracle/base.py` — new unified ABC

### Read (reference)
- `acqmss/oracle/oracle.py:15-57` — current `Oracle` ABC
- `acqmss/oracle/interactive.py:16-40` — current `InteractiveOracle` ABC

### Modify (next phase)
- `acqmss/oracle/__init__.py` — will import from base.py

## Implementation Steps

1. **Create base.py**
   ```bash
   touch acqmss/oracle/base.py
   ```

2. **Define imports**
   ```python
   from abc import ABC, abstractmethod
   from typing import Dict, Set
   ```

3. **Implement Oracle ABC**
   - Define class with docstring
   - Add abstract methods: `is_valid()`, `get_features()`, `get_feature_ids()`
   - Add concrete method: `ask()` delegates to `is_valid()`
   - Add concrete method: `get_feature_count()` returns `len(get_features())`

4. **Add type hints and docstrings**
   - Full parameter/return annotations
   - Google-style docstrings for all methods
   - Module-level docstring

5. **Verify syntax**
   ```bash
   python -m py_compile acqmss/oracle/base.py
   mypy acqmss/oracle/base.py --strict
   ```

## Todo List

- [ ] Create `acqmss/oracle/base.py`
- [ ] Define module docstring
- [ ] Import ABC, abstractmethod, typing
- [ ] Define `Oracle` class inheriting from ABC
- [ ] Implement `is_valid()` as abstractmethod
- [ ] Implement `get_features()` as abstractmethod
- [ ] Implement `get_feature_ids()` as abstractmethod
- [ ] Implement `ask()` as concrete delegation to `is_valid()`
- [ ] Implement `get_feature_count()` as concrete delegation
- [ ] Add type hints to all methods
- [ ] Add docstrings to all methods
- [ ] Verify with `python -m py_compile`
- [ ] Verify with `mypy --strict`

## Success Criteria

- [x] `base.py` exists with unified `Oracle` ABC
- [x] Three abstract methods: `is_valid()`, `get_features()`, `get_feature_ids()`
- [x] Two concrete methods: `ask()`, `get_feature_count()`
- [x] File under 100 LOC
- [x] Full type hints, strict mypy passes
- [x] No imports from other oracle modules (standalone)

## Risk Assessment

**Low risk** — creating new file, no existing code changes.

**Potential issues:**
- None — phase 2 will migrate `FeatureModelOracle` to use this ABC

## Security Considerations

None — abstract interface only, no data handling.

## Next Steps

**Immediate**: Phase 02 — Extract `FeatureModelOracle` to `fm_oracle.py`, inherit from new `Oracle` ABC

**Dependencies**: Phase 02 depends on this phase completing
