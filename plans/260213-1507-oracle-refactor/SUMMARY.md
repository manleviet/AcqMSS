# Oracle Package Refactor — Implementation Summary

**Plan Directory**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260213-1507-oracle-refactor/`
**Created**: 2026-02-13
**Status**: Ready for Implementation
**Total Effort**: 6 hours

---

## Executive Summary

Refactor `acqmss/oracle/` package to unify dual ABC abstractions (`Oracle` + `InteractiveOracle`), separate FM-specific logic from generic interface, eliminate redundant adapter pattern, and improve extensibility for non-FM oracle implementations.

**Key Changes:**
- Merge two ABCs into single `Oracle` interface
- Extract classes into 7 focused files (under 200 LOC each)
- Remove `AutomatedOracle` adapter (redundant wrapper)
- Preserve backward compatibility via deprecation aliases
- Update 14 consumer files to use new structure

---

## Current Architecture Issues

1. **Dual ABCs**: `Oracle.is_valid()` vs `InteractiveOracle.ask()` — same concept, different names
2. **FM coupling**: `FeatureModelOracle` mixes generic interface with FM-specific methods + flamapy imports
3. **Unnecessary adapter**: `AutomatedOracle` thin wrapper just renames `is_valid()` → `ask()`
4. **Poor extensibility**: Hard to add non-FM oracles (API, DB, custom validators)
5. **Monolithic files**: `oracle.py` 363 LOC, `interactive.py` 298 LOC

---

## Target Architecture

### File Structure
```
acqmss/oracle/
├── __init__.py          # Re-exports + backward compat aliases (~80 LOC)
├── base.py              # Oracle ABC (~60 LOC)
├── fm_oracle.py         # FeatureModelOracle (~200 LOC)
├── user_prompt.py       # UserPromptOracle (~100 LOC)
├── cached.py            # CachedOracle (~80 LOC)
├── example_provider.py  # ExampleProvider (~50 LOC)
└── extractor.py         # OracleData (~100 LOC)
```

### Unified Oracle ABC

```python
class Oracle(ABC):
    @abstractmethod
    def is_valid(config: Dict[str, bool]) -> bool: ...

    @abstractmethod
    def get_features() -> Set[str]: ...

    @abstractmethod
    def get_feature_ids() -> Dict[str, int]: ...

    # Concrete methods
    def ask(query: Dict[str, bool]) -> bool:
        return self.is_valid(query)  # Alias for backward compat

    def get_feature_count() -> int:
        return len(self.get_variables())
```

### Class Hierarchy
```
Oracle (ABC)
├── FeatureModelOracle    # FM-based SAT oracle
├── UserPromptOracle      # Terminal prompt oracle
└── CachedOracle          # Wrapper with caching

ExampleProvider           # Standalone iterator (no inheritance)
OracleData               # Dataclass for evaluation
```

---

## Implementation Phases

| Phase | Description | Files | Effort | Priority |
|-------|-------------|-------|--------|----------|
| [01](phase-01-unified-oracle-abc.md) | Define unified `Oracle` ABC | `base.py` | 1h | P1 |
| [02](phase-02-extract-fm-oracle.md) | Extract `FeatureModelOracle` | `fm_oracle.py` | 1h | P1 |
| [03](phase-03-refactor-helpers.md) | Extract helper classes | `user_prompt.py`, `cached.py`, `example_provider.py`, `extractor.py` | 1h | P2 |
| [04](phase-04-update-init.md) | Update `__init__.py` with re-exports | `__init__.py` | 0.5h | P1 |
| [05](phase-05-update-consumers.md) | Update 14 consumer files | All consumers | 2h | P1 |
| [06](phase-06-testing-validation.md) | Comprehensive testing | Test suite | 0.5h | P1 |

**Dependencies**: Sequential execution (01 → 02 → 03 → 04 → 05 → 06)

---

## Key Decisions

### 1. Primary Method Name: `is_valid()`
**Rationale**: More descriptive than `ask()`, used by CONGEN and generators
**Backward Compat**: `ask()` provided as alias delegating to `is_valid()`

### 2. Remove AutomatedOracle
**Rationale**: Thin wrapper with no added value — just renames methods
**Migration**: Direct `FeatureModelOracle` usage, deprecation alias in `__init__.py`

### 3. Feature ID Preservation
**Critical**: Flamapy traversal order must be preserved for evaluation consistency
**Implementation**: Copy `_build_feature_ids()` logic exactly from old code

### 4. Deprecation Strategy
**Approach**: Module-level `__getattr__()` for lazy deprecation warnings
**Advantage**: Warnings only when deprecated names accessed, not on all imports

---

## Consumer Impact

### 14 Files Importing Oracle Classes

**Minimal changes required:**
1. `InteractiveOracle` → `Oracle` (type hints)
2. `AutomatedOracle()` → `FeatureModelOracle()` (instantiation)
3. `oracle.fm_oracle.X` → `oracle.X` (attribute access)

**No changes to:**
- Method calls (`ask()`, `is_valid()` both available)
- Factory methods (`InteractiveLearner.from_files()`)
- Algorithm logic (QuAcq, CONGEN unchanged)

---

## Testing Strategy

### Level 1: Unit Tests
- Oracle ABC cannot be instantiated
- `FeatureModelOracle` loads FM, initializes correctly
- `ask()` delegates to `is_valid()`
- `CachedOracle` caching behavior

### Level 2: Integration Tests
- QuAcq with `FeatureModelOracle`
- CONGEN with example generation
- InteractiveLearner factory methods

### Level 3: Regression Tests
- Feature ID generation matches old implementation
- SAT query results identical
- CNF clause extraction unchanged

### Level 4: Deprecation Tests
- Import `InteractiveOracle` raises `DeprecationWarning`
- Import `AutomatedOracle` raises `DeprecationWarning`
- Aliases work correctly

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Feature ID inconsistency | High — breaks evaluation | Copy logic exactly, verify with test FM |
| Import breakage | Medium — 14 files affected | Phase 4 preserves all old imports |
| Test failures | Medium — delays merge | Incremental testing, immediate debug |
| Circular imports | Low — base imports | base.py has no concrete imports |
| Performance regression | Low — SAT queries | Profile, verify solver initialization |

---

## Success Criteria

- [ ] Single `Oracle` ABC with unified interface
- [ ] All 5 oracle classes in separate files under 200 LOC
- [ ] Backward compatibility via `__init__.py` re-exports
- [ ] All 14 consumer files updated
- [ ] Zero references to deprecated names (except `__init__.py`)
- [ ] All tests pass (QuAcq, CONGEN, interactive, evaluation)
- [ ] Mypy strict passes for all files
- [ ] No runtime warnings (except when testing deprecations)

---

## Quick Start for Implementer

1. **Read research reports**:
   - `research/researcher-01-oracle-code-analysis.md`
   - `research/researcher-02-oracle-references.md`

2. **Review main plan**: `plan.md`

3. **Execute phases sequentially**: Start with `phase-01-unified-oracle-abc.md`

4. **Test incrementally**: After each phase, verify compile and imports

5. **Final validation**: Phase 06 comprehensive testing before merge

---

## Follow-Up Tasks (Post-Merge)

1. Remove deprecation aliases in next major version
2. Add migration guide to documentation
3. Update architecture diagrams in `docs/`
4. Consider adding more oracle types:
   - `DatabaseOracle` — validate against DB constraints
   - `APIOracle` — remote validation service
   - `MLOracle` — learned constraint model

---

## Documentation Updates Required

- `docs/system-architecture.md` — Oracle package structure
- `docs/codebase-summary.md` — Oracle module organization
- `docs/code-standards.md` — Oracle usage patterns
- `CHANGELOG.md` — Note refactor, deprecations

---

## Questions Resolved

1. ✅ Should `Oracle` and `InteractiveOracle` merge? → Yes, single ABC
2. ✅ How to support non-FM oracles? → Clean ABC with minimal requirements
3. ✅ Should FM-specific methods move to separate interface? → Stay in `FeatureModelOracle`, not in ABC
4. ✅ Is `AutomatedOracle` necessary? → No, remove with deprecation alias
5. ✅ Should `ExampleProvider` be in oracle package? → Yes, but standalone class

---

**Ready for Implementation** ✓
