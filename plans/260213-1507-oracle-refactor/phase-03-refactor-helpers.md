# Phase 03: Refactor Helper Classes to Separate Files

## Context Links
- Research: [Oracle Code Analysis](research/researcher-01-oracle-code-analysis.md)
- Current impl: `acqmss/oracle/interactive.py` (lines 96-298)
- Current impl: `acqmss/oracle/oracle_extractor.py`

## Overview

**Priority**: P2 (parallel with phase 02)
**Status**: Complete
**Effort**: 1h

Split helper classes into separate files: `user_prompt.py`, `cached.py`, `example_provider.py`. Move `OracleData` to `extractor.py`.

## Key Insights

1. **UserPromptOracle**: No FM coupling, generic terminal interface (~85 LOC)
2. **CachedOracle**: Generic wrapper, works with any `Oracle` (~70 LOC)
3. **ExampleProvider**: Unrelated to oracle hierarchy, just shuffled iterator (~40 LOC)
4. **OracleData**: Already in separate file, just rename for consistency (~90 LOC)
5. **All inherit from unified ABC**: Change `InteractiveOracle` → `Oracle` inheritance

## Requirements

### Functional
- Extract `UserPromptOracle` to `user_prompt.py`, inherit from `base.Oracle`
- Extract `CachedOracle` to `cached.py`, wrap `base.Oracle`
- Extract `ExampleProvider` to `example_provider.py` (no inheritance)
- Rename `oracle_extractor.py` → `extractor.py` for consistency
- Update all internal imports

### Non-Functional
- Each file under 200 LOC
- Full type hints
- Strict mypy compliance
- No behavior changes

## Architecture

### UserPromptOracle (`user_prompt.py`)

```python
# acqmss/oracle/user_prompt.py
from typing import Dict, Set
from conacq.oracle.base import Oracle


class UserPromptOracle(Oracle):
    """Human-in-the-loop oracle via terminal prompts."""

    def __init__(self, features: list[str], verbose: bool = True) -> None: ...

    # Oracle ABC implementation
    def is_valid(self, config: Dict[str, bool]) -> bool:
        """Prompt user for validation answer."""
        # Display config, prompt y/n, return bool

    def get_features(self) -> Set[str]: ...

    def get_feature_ids(self) -> Dict[str, int]: ...

    # Helper methods
    def get_query_count(self) -> int: ...

    def _format_query(self, config: Dict[str, bool]) -> str: ...
```

**Change**: Inherit from `base.Oracle` instead of `InteractiveOracle`

### CachedOracle (`cached.py`)

```python
# acqmss/oracle/cached.py
from typing import Dict
from conacq.oracle.base import Oracle


class CachedOracle(Oracle):
    """Caching wrapper for any Oracle implementation."""

    def __init__(self, base_oracle: Oracle) -> None: ...

    # Oracle ABC implementation (delegates to base)
    def is_valid(self, config: Dict[str, bool]) -> bool:
        """Check cache first, delegate on miss."""
        key = self._config_to_key(config)
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        result = self.base_oracle.is_valid(config)
        self._cache[key] = result
        self._cache_misses += 1
        return result

    def get_features(self) -> Set[str]:
        return self.base_oracle.get_variables()

    def get_feature_ids(self) -> Dict[str, int]:
        return self.base_oracle.get_feature_ids()

    # Cache management
    def get_cache_stats(self) -> Dict[str, int]: ...

    def clear_cache(self) -> None: ...
```

**Change**: Wrap `base.Oracle` instead of `InteractiveOracle`

### ExampleProvider (`example_provider.py`)
```python
# acqmss/oracle/example_provider.py
import random
from typing import Dict, List, Optional

class ExampleProvider:
    """Iterator for shuffled example pool (example-based QuAcq)."""

    def __init__(self, examples: List[Dict[str, bool]], seed: int | None = None) -> None: ...

    def next_example(self) -> Optional[Dict[str, bool]]: ...
    def is_exhausted(self) -> bool: ...
    def remaining(self) -> int: ...
```

**No inheritance** — standalone utility class

### OracleData (`extractor.py`)
```python
# acqmss/oracle/extractor.py (renamed from oracle_extractor.py)
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

@dataclass
class OracleData:
    """Package oracle data for evaluation."""

    descriptions: Set[str]
    clauses: List[List[int]]
    clause_set: Set[Tuple[int, ...]]
    feature_map: Dict[str, int]
    root_feature: str

    @staticmethod
    def from_uvl(uvl_path: Path) -> 'OracleData': ...

    @staticmethod
    def from_oracle(oracle: 'FeatureModelOracle') -> 'OracleData': ...
```

**Change**: File rename only, no logic changes

## Related Code Files

### Create
- `acqmss/oracle/user_prompt.py` — extracted UserPromptOracle
- `acqmss/oracle/cached.py` — extracted CachedOracle
- `acqmss/oracle/example_provider.py` — extracted ExampleProvider
- `acqmss/oracle/extractor.py` — renamed from oracle_extractor.py

### Read
- `acqmss/oracle/interactive.py:96-181` — UserPromptOracle source
- `acqmss/oracle/interactive.py:183-254` — CachedOracle source
- `acqmss/oracle/interactive.py:256-298` — ExampleProvider source
- `acqmss/oracle/oracle_extractor.py` — OracleData source

### Delete (next phase)
- `acqmss/oracle/interactive.py` — remove after extraction
- `acqmss/oracle/oracle_extractor.py` — delete after rename

## Implementation Steps

### 1. Extract UserPromptOracle

```bash
touch acqmss/oracle/user_prompt.py
```

1. Copy module docstring
2. Import `from acqmss.oracle.base import Oracle`
3. Copy `UserPromptOracle` class (lines 96-181 from interactive.py)
4. Change inheritance: `class UserPromptOracle(Oracle):`
5. Rename `ask()` → `is_valid()` for ABC compliance
6. Add `ask()` method calling `is_valid()` for backward compat
7. Implement `get_feature_ids()` — return `{f: i+1 for i, f in enumerate(sorted(self.features))}`
8. Verify with mypy

### 2. Extract CachedOracle

```bash
touch acqmss/oracle/cached.py
```

1. Copy module docstring
2. Import `from acqmss.oracle.base import Oracle`
3. Copy `CachedOracle` class (lines 183-254 from interactive.py)
4. Change `base_oracle: InteractiveOracle` → `base_oracle: Oracle`
5. Rename `ask()` → `is_valid()` for ABC compliance
6. Add `ask()` method calling `is_valid()` for backward compat
7. Update delegation: `self.base_oracle.is_valid()` instead of `.ask()`
8. Verify with mypy

### 3. Extract ExampleProvider

```bash
touch acqmss/oracle/example_provider.py
```

1. Copy module docstring
2. Import `random`, typing
3. Copy `ExampleProvider` class (lines 256-298 from interactive.py)
4. No inheritance changes (standalone)
5. Verify with mypy

### 4. Rename OracleData file

```bash
git mv acqmss/oracle/oracle_extractor.py acqmss/oracle/extractor.py
```

1. No code changes, just file rename
2. Update imports in file: `from acqmss.oracle.fm_oracle import FeatureModelOracle`

### 5. Verify all files

```bash
python -m py_compile acqmss/oracle/user_prompt.py
python -m py_compile acqmss/oracle/cached.py
python -m py_compile acqmss/oracle/example_provider.py
python -m py_compile acqmss/oracle/extractor.py
mypy acqmss/oracle/ --strict
```

## Todo List

### UserPromptOracle
- [ ] Create `acqmss/oracle/user_prompt.py`
- [ ] Import from `acqmss.oracle.base`
- [ ] Copy `UserPromptOracle` class from interactive.py
- [ ] Change inheritance to `Oracle`
- [ ] Rename `ask()` → `is_valid()`
- [ ] Add `ask()` alias method
- [ ] Implement `get_feature_ids()`
- [ ] Verify mypy strict

### CachedOracle
- [ ] Create `acqmss/oracle/cached.py`
- [ ] Import from `acqmss.oracle.base`
- [ ] Copy `CachedOracle` class from interactive.py
- [ ] Change `base_oracle` type to `Oracle`
- [ ] Rename `ask()` → `is_valid()`
- [ ] Add `ask()` alias method
- [ ] Update delegation to `is_valid()`
- [ ] Verify mypy strict

### ExampleProvider
- [ ] Create `acqmss/oracle/example_provider.py`
- [ ] Import random, typing
- [ ] Copy `ExampleProvider` class from interactive.py
- [ ] Verify mypy strict

### OracleData
- [ ] Rename `oracle_extractor.py` → `extractor.py` (git mv)
- [ ] Update import to `fm_oracle.py`
- [ ] Verify mypy strict

### Verification
- [ ] Compile all four new files
- [ ] Run mypy on oracle package
- [ ] Test import: `from acqmss.oracle.user_prompt import UserPromptOracle`

## Success Criteria

- [x] Four new files created: `user_prompt.py`, `cached.py`, `example_provider.py`, `extractor.py`
- [x] `UserPromptOracle` and `CachedOracle` inherit from `base.Oracle`
- [x] All files under 200 LOC (target: user_prompt ~100, cached ~80, example_provider ~50, extractor ~100)
- [x] Full type hints, strict mypy passes
- [x] No behavior changes (just reorganization)
- [x] Old `interactive.py` can be deleted in next phase

## Risk Assessment

**Low risk** — straightforward file splits, no logic changes.

**Potential issues:**
1. **UserPromptOracle.get_feature_ids()**: Must generate consistent ID mapping
   - *Mitigation*: Use sorted features: `{f: i+1 for i, f in enumerate(sorted(features))}`
2. **CachedOracle delegation**: Must update all method calls
   - *Mitigation*: Search for all `.ask()` calls in cached.py, replace with `.is_valid()`

## Security Considerations

- **UserPromptOracle**: Input validation for y/n prompts
- **CachedOracle**: Cache size unbounded — consider max size limit (future)

## Next Steps

**Immediate**: Phase 04 — Update `__init__.py` with re-exports and deprecation aliases

**Dependencies**: Phase 04 depends on phases 01-03 completing
