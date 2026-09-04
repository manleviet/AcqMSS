# Phase 1: Extend Oracle ABC

## Context Links
- [Oracle ABC](../../conacq/oracle/base.py) -- current 47-line interface
- [FMOracle](../../conacq/oracle/fm_oracle.py) -- has `get_cnf_clauses()` on line 113
- [CachedOracle](../../conacq/oracle/cached.py) -- wrapper, delegates everything
- [UserPromptOracle](../../conacq/oracle/user_prompt.py) -- human-in-loop, no SAT
- [Code Standards](../../docs/code-standards.md) -- Oracle Module Conventions section

## Overview
- **Priority**: P2
- **Status**: Complete
- **Description**: Add two abstract methods to `Oracle` ABC to formalize the implicit contract

## Key Insights
- `ExampleGenerator` accepts `Oracle` but calls `get_cnf_clauses()` (only on FeatureModelOracle) -- runtime AttributeError for non-FM oracles
- `complete_configuration()` encapsulates SAT-solving logic currently duplicated across generators
- `get_cnf_clauses()` used by extractor.py (typed FeatureModelOracle) and learner.py (also typed FeatureModelOracle), but making it part of ABC formalizes the contract
- UserPromptOracle and CachedOracle need implementations (stub or delegation)

## Requirements

### Functional
- Add `complete_configuration(partial: Dict[str, bool]) -> Optional[Dict[str, bool]]` as abstract method
- Add `get_cnf_clauses() -> List[List[int]]` as abstract method
- Both methods must have Google-style docstrings with type hints

### Non-Functional
- Oracle ABC should stay under ~80 lines
- No breaking changes to existing callers

## Architecture

New Oracle ABC interface:

```python
class Oracle(ABC):
    # Existing
    @abstractmethod
    def is_valid(self, assignments: Dict[str, bool]) -> bool: ...
    @abstractmethod
    def get_features(self) -> Set[str]: ...
    @abstractmethod
    def get_feature_ids(self) -> Dict[str, int]: ...
    def ask(self, query: Dict[str, bool]) -> bool: ...
    def get_feature_count(self) -> int: ...

    # New
    @abstractmethod
    def complete_configuration(self, partial: Dict[str, bool]) -> Optional[Dict[str, bool]]: ...
    @abstractmethod
    def get_cnf_clauses(self) -> List[List[int]]: ...
```

## Related Code Files

### Files to Modify
- `acqmss/oracle/base.py` -- add 2 abstract methods
- `acqmss/oracle/cached.py` -- add delegation for both new methods
- `acqmss/oracle/user_prompt.py` -- add NotImplementedError stubs
- `acqmss/oracle/__init__.py` -- no change needed (exports Oracle)

### Files NOT Modified (yet)
- `acqmss/oracle/fm_oracle.py` -- Phase 2
- `acqmss/example_generators/base.py` -- Phase 3

## Implementation Steps

1. **Edit `acqmss/oracle/base.py`**
   - Add `Optional, List` to typing imports
   - Add `complete_configuration()` abstract method after `get_feature_ids()`
   - Add `get_cnf_clauses()` abstract method after `complete_configuration()`
   - Docstrings: describe purpose, args, returns

2. **Edit `acqmss/oracle/cached.py`**
   - Add `complete_configuration()` -- delegate to `self.base_oracle.complete_configuration(partial)`
   - Add `get_cnf_clauses()` -- delegate to `self.base_oracle.get_cnf_clauses()`
   - Add necessary imports (`Optional, List`)

3. **Edit `acqmss/oracle/user_prompt.py`**
   - Add `complete_configuration()` -- `raise NotImplementedError("UserPromptOracle cannot complete configurations")`
   - Add `get_cnf_clauses()` -- `raise NotImplementedError("UserPromptOracle has no CNF representation")`
   - Add necessary imports (`Optional, List`)

4. **Run type check**: `PYTHONPATH=. python -c "from acqmss.oracle import Oracle, CachedOracle, UserPromptOracle"`

## Todo List

- [x] Add `complete_configuration()` to Oracle ABC
- [x] Add `get_cnf_clauses()` to Oracle ABC
- [x] Add delegation in CachedOracle
- [x] Add NotImplementedError stubs in UserPromptOracle
- [x] Verify imports resolve

## Success Criteria
- `Oracle` ABC has both new abstract methods
- `CachedOracle` delegates both methods
- `UserPromptOracle` raises `NotImplementedError` for both
- No import errors
- Existing tests still pass (FeatureModelOracle already has `get_cnf_clauses()`)

## Risk Assessment
- **Low risk**: FeatureModelOracle already implements `get_cnf_clauses()`, so no runtime breakage
- **UserPromptOracle**: Adding abstract methods to ABC means UserPromptOracle must implement them (even as stubs). Acceptable since UserPromptOracle is never used with ExampleGenerators.

## Security Considerations
- None (interface-only change, no new I/O)

## Next Steps
- Phase 2: Implement `complete_configuration()` in FeatureModelOracle
