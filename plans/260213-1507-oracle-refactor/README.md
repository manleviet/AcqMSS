# Oracle Package Refactor — Implementation Plan

**Status**: Ready for Implementation
**Effort**: 6 hours
**Priority**: P2 (Architectural improvement)

---

## Quick Navigation

- **[Plan Overview](plan.md)** — Main plan with YAML frontmatter, phase summary
- **[Executive Summary](SUMMARY.md)** — Comprehensive summary, decisions, testing strategy

### Implementation Phases

1. **[Phase 01: Unified Oracle ABC](phase-01-unified-oracle-abc.md)** (1h)
   - Create `base.py` with merged `Oracle` ABC
   - Define `is_valid()`, `get_features()`, `get_feature_ids()`
   - Add `ask()` alias for backward compatibility

2. **[Phase 02: Extract FM Oracle](phase-02-extract-fm-oracle.md)** (1h)
   - Move `FeatureModelOracle` to `fm_oracle.py`
   - Inherit from new `Oracle` ABC
   - Preserve feature ID generation logic

3. **[Phase 03: Refactor Helpers](phase-03-refactor-helpers.md)** (1h)
   - Extract `UserPromptOracle` → `user_prompt.py`
   - Extract `CachedOracle` → `cached.py`
   - Extract `ExampleProvider` → `example_provider.py`
   - Rename `oracle_extractor.py` → `extractor.py`

4. **[Phase 04: Update Init](phase-04-update-init.md)** (0.5h)
   - Rewrite `__init__.py` with new imports
   - Add deprecation aliases via `__getattr__()`
   - Export all public names

5. **[Phase 05: Update Consumers](phase-05-update-consumers.md)** (2h)
   - Update 14 consumer files
   - Change `InteractiveOracle` → `Oracle`
   - Change `AutomatedOracle` → `FeatureModelOracle`
   - Delete old files

6. **[Phase 06: Testing & Validation](phase-06-testing-validation.md)** (0.5h)
   - Run all tests
   - Verify feature ID consistency
   - Test deprecation warnings
   - End-to-end validation

### Research Reports

- **[Oracle Code Analysis](research/researcher-01-oracle-code-analysis.md)** — Current architecture, issues, classes
- **[Oracle References](research/researcher-02-oracle-references.md)** — Consumer usage patterns, 14 affected files

---

## Architecture Changes

### Before
```
acqmss/oracle/
├── __init__.py
├── oracle.py              # 363 LOC: Oracle ABC + FeatureModelOracle
├── interactive.py         # 298 LOC: InteractiveOracle + 4 classes
└── oracle_extractor.py    # 103 LOC: OracleData
```

### After
```
acqmss/oracle/
├── __init__.py           # ~80 LOC: Re-exports + deprecations
├── base.py               # ~60 LOC: Unified Oracle ABC
├── fm_oracle.py          # ~200 LOC: FeatureModelOracle
├── user_prompt.py        # ~100 LOC: UserPromptOracle
├── cached.py             # ~80 LOC: CachedOracle
├── example_provider.py   # ~50 LOC: ExampleProvider
└── extractor.py          # ~100 LOC: OracleData
```

---

## Key Benefits

1. **Unified Interface**: Single `Oracle` ABC, no more dual abstractions
2. **Better Organization**: Each class in focused file under 200 LOC
3. **Improved Extensibility**: Easy to add non-FM oracles (DB, API, ML)
4. **Eliminated Redundancy**: Remove `AutomatedOracle` wrapper
5. **Backward Compatible**: All old imports work with deprecation warnings

---

## Consumer Impact

**14 Files Affected** (see [Phase 05](phase-05-update-consumers.md)):
- `acqmss/algorithms/interactive/` — QuAcq, InteractiveLearner
- `apps/` — run_interactive_eval.py, run_congen.py, etc.
- `tests/` — test_interactive.py, test_congen.py
- `acqmss/testcases/generators/` — base.py, nwise_coverage.py, etc.

**Migration Pattern**:

```python
# Before
from conacq.oracle import InteractiveOracle, AutomatedOracle

oracle = AutomatedOracle(fm_path)

# After
from conacq.oracle import Oracle, FeatureModelOracle

oracle = FeatureModelOracle(fm_path)
```

---

## Critical Invariants

1. **Feature ID Generation**: Flamapy traversal order MUST be preserved
2. **SAT Query Results**: Must match old implementation exactly
3. **CNF Extraction**: Clause ordering and variable IDs unchanged
4. **Method Availability**: Both `ask()` and `is_valid()` available on all oracles

---

## Testing Checklist

- [ ] All existing tests pass
- [ ] Feature IDs match old implementation
- [ ] SAT queries produce same results
- [ ] Deprecation warnings work correctly
- [ ] Mypy strict passes
- [ ] No runtime warnings in normal usage
- [ ] End-to-end CONGEN/QuAcq validation

---

## Implementation Tips

1. **Start with Phase 01**: Foundation for all other phases
2. **Test incrementally**: After each phase, verify compilation and imports
3. **Preserve feature ID logic**: Copy `_build_feature_ids()` exactly
4. **Use deprecation period**: Keep aliases for smooth migration
5. **Verify with grep**: Search for deprecated names before declaring done

---

## Getting Started

```bash
# 1. Read research reports
cd /Users/manleviet/Development/GitHub/AcqMSS
cat plans/260213-1507-oracle-refactor/research/researcher-01-oracle-code-analysis.md
cat plans/260213-1507-oracle-refactor/research/researcher-02-oracle-references.md

# 2. Start with Phase 01
cat plans/260213-1507-oracle-refactor/phase-01-unified-oracle-abc.md

# 3. Execute phase steps
# ... follow todo list in phase-01-unified-oracle-abc.md

# 4. Verify phase completion
python -m py_compile acqmss/oracle/base.py
mypy acqmss/oracle/base.py --strict

# 5. Move to next phase
cat plans/260213-1507-oracle-refactor/phase-02-extract-fm-oracle.md
```

---

## Questions?

All major architectural decisions documented in [SUMMARY.md](SUMMARY.md).

**Unresolved questions**: None — all design questions answered during research phase.

---

**Plan Created**: 2026-02-13
**Plan Location**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260213-1507-oracle-refactor/`
