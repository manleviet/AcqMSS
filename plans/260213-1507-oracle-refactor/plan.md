---
title: "Oracle Package Architecture Refactor"
description: "Unify oracle ABC, separate FM logic, improve extensibility"
status: completed
priority: P2
effort: 5h
branch: main
tags: [refactor, oracle, architecture, extensibility]
created: 2026-02-13
---

# Oracle Package Architecture Refactor

## Overview

Refactor `acqmss/oracle/` to unify dual ABC abstractions (`Oracle` + `InteractiveOracle`), separate FM-specific logic, eliminate redundant adapters, and enable non-FM oracle implementations.

## Context

**Current Issues:**
- Dual ABCs: `Oracle.is_valid()` vs `InteractiveOracle.ask()` — same concept, different names
- FM coupling: `FeatureModelOracle` mixes generic interface with FM-specific methods
- Unnecessary adapter: `AutomatedOracle` thin wrapper just renames methods
- Poor extensibility: Hard to add non-FM oracles (API, DB, validators)

**Research Reports:**
- [Oracle Code Analysis](research/researcher-01-oracle-code-analysis.md)
- [Oracle References](research/researcher-02-oracle-references.md)

## Goals

1. **Unified interface**: Single `Oracle` ABC with `is_valid()` primary, `ask()` alias
2. **FM separation**: Extract flamapy logic into `FeatureModelOracle` as implementation
3. **Remove adapter**: Eliminate `AutomatedOracle`, let `FeatureModelOracle` implement ABC directly
4. **Extensibility**: New oracle types need only implement ABC
5. **Clean files**: Each class in own file (~280 LOC max for FM oracle)
6. **Hard removal**: No deprecation aliases — clean break, update all consumers atomically

## Architecture

### Unified Oracle ABC (`base.py`)
```python
class Oracle(ABC):
    @abstractmethod
    def is_valid(self, config: Dict[str, bool]) -> bool: ...
    @abstractmethod
    def get_features(self) -> Set[str]: ...
    @abstractmethod
    def get_feature_ids(self) -> Dict[str, int]: ...

    def ask(self, query: Dict[str, bool]) -> bool:
        """Alias for is_valid() for backward compatibility."""
        return self.is_valid(query)
```

### FM Implementation (`fm_oracle.py`)
```python
class FeatureModelOracle(Oracle):
    # Generic Oracle interface
    def is_valid(self, config: Dict[str, bool]) -> bool: ...
    def get_features(self) -> Set[str]: ...
    def get_feature_ids(self) -> Dict[str, int]: ...

    # FM-specific extensions
    def get_root_feature(self) -> str: ...
    def get_cnf_clauses(self) -> List[List[int]]: ...
    def get_constraint_descriptions(self) -> Set[str]: ...
    def get_leaf_features(self) -> Set[str]: ...
```

### File Structure
```
acqmss/oracle/
├── __init__.py          # Re-exports (no deprecated aliases)
├── base.py              # Oracle ABC (~60 LOC)
├── fm_oracle.py         # FeatureModelOracle (~280 LOC)
├── user_prompt.py       # UserPromptOracle (~100 LOC)
├── cached.py            # CachedOracle (~80 LOC)
├── example_provider.py  # ExampleProvider (~50 LOC)
└── extractor.py         # OracleData (~100 LOC)
```

## Implementation Phases

| Phase | Description | Effort | Status |
|-------|-------------|--------|--------|
| [01](phase-01-unified-oracle-abc.md) | Define unified Oracle ABC | 1h | Pending |
| [02](phase-02-extract-fm-oracle.md) | Extract FeatureModelOracle to fm_oracle.py (no classify()) | 1h | Pending |
| [03](phase-03-refactor-helpers.md) | Refactor helper classes to separate files | 1h | Pending |
| [04](phase-04-update-init-and-consumers.md) | Update __init__.py + all 14 consumers + delete old files | 2h | Pending |
| [05](phase-05-testing-validation.md) | Testing and validation | 0.5h | Pending |

## Success Criteria

- [x] Single `Oracle` ABC with unified interface
- [x] `FeatureModelOracle` implements ABC directly (no adapter)
- [x] All oracle classes in separate files
- [x] No `InteractiveOracle` or `AutomatedOracle` in codebase (hard removal)
- [x] No `classify()` method (removed entirely)
- [x] All 14 consumer files updated with new imports
- [x] All tests pass (QuAcq, CONGEN, interactive, evaluation)
- [x] Old oracle.py and interactive.py deleted

## Risks

- **Import breakage**: 14 files update atomically in Phase 4
  - *Mitigation*: Grep verification, incremental testing
- **Feature ID consistency**: Flamapy traversal order must be preserved
  - *Mitigation*: Keep `_build_feature_ids()` logic unchanged
- **SAT solver state**: Persistent solver in `FeatureModelOracle`
  - *Mitigation*: No changes to solver logic

## Dependencies

- Phases 1-3 sequential (create new files)
- Phase 4 atomic (update __init__.py + consumers + delete old files)
- Phase 5 depends on phase 4 complete

## Validation Log

### Session 1 — 2026-02-13
**Trigger:** Initial plan creation validation
**Questions asked:** 7

#### Questions & Answers

1. **[Architecture]** The plan merges Oracle + InteractiveOracle into a single ABC with is_valid() as primary and ask() as alias. This means FeatureModelOracle directly implements the unified Oracle (eliminating AutomatedOracle). Do you agree with this approach?
   - Options: Yes, unify and eliminate adapter | Keep both ABCs separate | Merge ABCs but keep AutomatedOracle
   - **Answer:** Yes, unify and eliminate adapter (Recommended)
   - **Rationale:** Eliminates unnecessary abstraction layer. Single ABC simplifies extensibility.

2. **[Deprecation]** The plan uses __getattr__() for lazy deprecation warnings on InteractiveOracle and AutomatedOracle. How aggressive should the deprecation be?
   - Options: Deprecation warnings via __getattr__ | Hard removal — no aliases | Silent aliases — no warnings
   - **Answer:** Hard removal — no aliases
   - **Rationale:** Clean break. No dead code. All consumers update atomically. Simplifies __init__.py.

3. **[Scope]** classify() method exists only on FeatureModelOracle and is used internally for Example classification. The plan proposes removing it from the ABC. Should it stay?
   - Options: Remove from ABC, keep as private | Keep classify() in ABC as abstract | Remove entirely
   - **Answer:** Remove entirely
   - **Rationale:** Inline classification logic where used. Simpler interface.

4. **[Scope]** ExampleProvider currently lives in the oracle package but is unrelated to the Oracle hierarchy. Where should it go?
   - Options: Keep in oracle/ as separate file | Move to acqmss/testcases/ | Move to acqmss/algorithms/interactive/
   - **Answer:** Keep in oracle/ as separate file (Recommended)
   - **Rationale:** Co-located with oracles for QuAcq convenience. Avoids unnecessary import churn.

5. **[Risk]** With hard removal, all 14 consumer files MUST update simultaneously. Should we collapse phases 4+5 into one atomic phase?
   - Options: Yes, collapse phases 4+5 | No, keep phases separate
   - **Answer:** Yes, collapse phases 4+5 (Recommended)
   - **Rationale:** No deprecation buffer needed. Single atomic update avoids broken intermediate state.

6. **[Scope]** FeatureModelOracle is 305 LOC, will be ~280 after classify() removal. Plan targets <200 LOC. How to handle?
   - Options: Accept ~280 LOC | Extract FM parsing helpers | Extract CNF building to separate module
   - **Answer:** Accept ~280 LOC — good enough
   - **Rationale:** Single responsibility (FM oracle). Further splitting over-fragments. 280 LOC manageable.

7. **[Risk]** Should old oracle.py and interactive.py be deleted immediately or kept as safety net?
   - Options: Delete immediately in same phase | Keep old files for one release cycle
   - **Answer:** Delete immediately in same phase (Recommended)
   - **Rationale:** Clean break. Git history preserves files. No dead code in repo.

#### Confirmed Decisions
- **Unified ABC**: Merge Oracle + InteractiveOracle → single Oracle ABC
- **Hard removal**: No deprecation aliases for InteractiveOracle/AutomatedOracle
- **classify() removed**: Inline where used, not part of any interface
- **ExampleProvider stays**: Remains in oracle/ package as separate file
- **Phases collapsed**: Old phases 4+5 merged into single atomic phase 4
- **FM oracle ~280 LOC**: Acceptable, no further splitting
- **Immediate deletion**: Old files removed in same phase as consumer updates

#### Action Items
- [x] Update plan.md phases (collapsed 4+5, renumbered 6→5)
- [ ] Update phase-02 to remove classify() entirely (not just privatize)
- [ ] Rewrite phase-04 as combined init+consumers+deletion phase
- [ ] Remove phase-05 (consumers) — merged into phase-04
- [ ] Rename phase-06 → phase-05 (testing)
- [ ] Remove deprecation __getattr__() code from phase-04

#### Impact on Phases
- Phase 02: Remove classify() entirely instead of privatizing
- Phase 04: Collapsed with old Phase 05 — update __init__.py + all consumers + delete old files atomically
- Phase 05 (old): Merged into Phase 04
- Phase 06 → Phase 05: Renumbered to testing-validation
