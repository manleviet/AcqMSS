# Documentation Update: QuAcq Dependency Injection Refactor

**Date**: 2026-02-28
**Commit**: 260228-0119
**Status**: Complete

## Summary

Updated documentation to reflect QuAcq DI refactor (commit 260228). QuAcq now uses dependency injection pattern with explicit factory methods, and learn() signature changed from task-based to direct parameter passing with 3-mode dispatch.

## Changes Made

### 1. docs/quacq.md

**Sections**:
- Relation to Codebase
- Removed Classes → Usage Patterns

**Updates**:
- Updated Relation to Codebase:
  - Added `sat_utils.py` (NEW) — Standalone utility functions extracted from QuAcqTask
  - Updated file descriptions to reflect DI pattern (was "QuAcq(solver_name, profiler)")
  - Updated FindScope/FindC LOC counts (correct to actual file sizes)

- Replaced old usage patterns:
  - REMOVED: `QuAcq(solver_name, profiler)` constructor with internal QueryGenerator
  - REMOVED: `quacq.learn(task, oracle, description_provider, max_queries)` signature
  - REMOVED: `quacq.learn_from_examples(task, example_provider, oracle, description_provider, query_mode, max_queries)` signature
  - ADDED: Factory pattern with `QuAcq.for_oracle(oracle, query_gen, discrim_gen, profiler)`
  - ADDED: Factory pattern with `QuAcq.for_examples(oracle, example_provider, discrim_gen, profiler)`
  - ADDED: New learn() signature with 13 direct parameters + mode dispatch

- Updated code examples to show:
  - DI construction of QueryGenerator and DiscriminatingGenerator
  - use of factory methods (for_oracle, for_examples)
  - Direct parameter passing to learn()
  - 3 modes: 'oracle', 'example_only', 'example_first'

**Rationale**: Accurately document public API changes from task-based to parameter-based with full DI pattern.

### 2. docs/system-architecture.md

**Section**: conacq/algorithms/ — Acquisition Algorithms (API examples)

**Updates**:
- Replaced old QuAcq usage example:
  ```python
  quacq = QuAcq('glucose4')
  result = quacq.learn(model.task, oracle_mode='automated')
  ```

- With new DI-based example:
  ```python
  query_gen = QueryGenerator(max_query_size=10)
  discrim_gen = DiscriminatingGenerator()
  quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen)
  result = quacq.learn(set_c=..., set_b=..., ..., mode='oracle', ...)
  ```

**Rationale**: API documentation must reflect current constructor and method signatures.

### 3. docs/codebase-summary.md

**Section**: conacq/algorithms/quacq/ — QuAcq Sub-package

**Updates**:
- Updated QuAcq file table:
  - Added `sat_utils.py` (93 LOC) — NEW utility functions
  - Updated learn() description: "DI pattern, mode dispatch, 3-arg learn()" → clarifies new signature style

- Updated Changes section (This Session):
  - Documented DI refactor changes:
    - QuAcq.__init__() now takes oracle, query_generator, example_provider, discriminating_generator, profiler
    - Added QuAcq.for_oracle() factory (discrim_gen required)
    - Added QuAcq.for_examples() factory (example_provider required)
    - learn() refactored to direct parameter signature (set_c, set_b, ..., mode='oracle'|'example_only'|'example_first')
  - learn() supports 3 modes via single parameter (was separate methods)

**Rationale**: Accurate tracking of session changes (QuAcq DI refactor) vs prior session (FindScope/FindC refactoring).

### 4. docs/code-standards.md

**Section**: Design Patterns → 3. Facade Pattern & 5. Dependency Injection

**Updates**:

#### Facade Pattern (QuAcqRunner example)
- BEFORE: `QuAcq(self.solver_name)` + `quacq.learn(model.task, oracle_mode='automated')`
- AFTER:
  - Create QueryGenerator and DiscriminatingGenerator
  - Use `QuAcq.for_oracle(oracle, query_gen, discrim_gen)`
  - Call learn() with 13 direct parameters + mode='oracle'
  - Example clarifies DI pattern for high-level facades

#### Dependency Injection section
- Split into two examples:
  - ConGen: Simple DI (checker + profiler)
  - QuAcq: Advanced DI with factories (oracle, query_gen, example_provider, discrim_gen, profiler)
- Added factory method documentation:
  - `for_oracle()`: oracle mode requires query_gen and discrim_gen
  - `for_examples()`: example modes require example_provider
- Clarified learn() signature as complex due to full task exposure (assumption-based semantics)

**Rationale**: Code standards should show real patterns (QuAcq factories) not idealized versions. Helps developers understand why certain dependencies are required for different modes.

## Verification

All changes verified against actual code:
- ✓ QuAcq.__init__() signature (conacq/algorithms/quacq/quacq.py lines 155-164)
- ✓ QuAcq.for_oracle() factory (lines 166-169)
- ✓ QuAcq.for_examples() factory (lines 171-175)
- ✓ learn() signature with 13 parameters (lines 193-207)
- ✓ sat_utils.py exists and exports standalone functions (conacq/algorithms/quacq/sat_utils.py)
- ✓ Mode dispatch in learn(): 'oracle', 'example_only', 'example_first' (line 204)

## Files Updated

1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` (lines 145-160, 293-348)
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (lines 91-110)
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` (lines 29-61)
4. `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` (lines 188-222, 241-288)

## Key Concepts Documented

### Dependency Injection Pattern
- All collaborators (oracle, query_gen, example_provider, discrim_gen, profiler) passed at construction
- Factory methods (`for_oracle`, `for_examples`) enforce required dependencies per mode
- Mode validation happens in learn() — raises ValueError if missing required collaborators

### Mode Dispatch
- Single learn() method with mode parameter instead of separate methods
- Modes: 'oracle' (SAT-based), 'example_only' (pool only), 'example_first' (pool + SAT fallback)
- Different factory methods required for different modes:
  - for_oracle(): requires query_gen + discrim_gen
  - for_examples(): requires example_provider (optional discrim_gen for example_first)

### Parameter Exposure
- learn() takes full task parameters (set_c, set_b, set_kb, ..., constraint_clauses, negated_clauses, feature_ids, id_to_feature)
- Mirrors ConGen's direct parameter passing approach
- Enables flexibility: same learn() function used for oracle mode, example batch mode, hybrid mode

### SAT Utilities Extraction
- sat_utils.py contains pure functions extracted from QuAcqTask
- Shared by FindScope, FindC, DiscriminatingGenerator, and QuAcq.learn()
- Utility functions: config_to_assumptions, violates_clauses, get_kb_clauses, get_constraint_vars, get_constraints_with_scope

## Documentation Accuracy

All referenced patterns verified:
- QuAcq constructor requires oracle at minimum ✓
- for_oracle() requires query_gen and discrim_gen ✓
- for_examples() requires example_provider ✓
- learn() signature has 13 required parameters (set_c through negated_clauses) ✓
- learn() has 3 optional parameters (mode, max_queries, description_provider) ✓
- Mode parameter is Literal['oracle', 'example_only', 'example_first'] ✓

## Impact

**Documentation Coverage**: QuAcq public API fully documented with actual signatures and usage patterns.

**Clarity**: Examples show real DI construction patterns, not simplified pseudo-code. Helps developers understand dependency requirements per mode.

**Maintainability**: Documentation aligned with current refactor (DI pattern), making future changes easier to track.
