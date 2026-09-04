# Brainstorm: Bias Package Improvements

**Date**: 2026-02-16
**Status**: Agreed
**Scope**: Internal refactoring — extract methods, constants, caching

## Problem Statement

The `acqmss/bias/` package (1,157 LOC, 6 files) has 3/6 files exceeding the 200 LOC threshold. Key pain points: monolithic methods, magic numbers, inefficient statistics, no caching.

No specific functional pain points. No new operators planned. Goal: code health and maintainability.

## Evaluated Approaches

### Approach A: Focused Code Cleanup (Selected)
- Extract helper methods from 3 oversized files
- Cache constraints for statistics reuse
- Extract magic numbers as named constants
- **Effort**: ~2h | **Risk**: Low | **Impact**: High readability improvement

### Approach B: Full Structural Split (Rejected)
- Split files into separate modules (reader/writer, hierarchical/cross-tree)
- **Why rejected**: User prefers minimal file restructuring. Current structure is functional.

### Approach C: Extensibility Patterns (Rejected)
- Protocol/ABC, Strategy pattern for CrossTreeMode, DI
- **Why rejected**: YAGNI — no new operators planned. Over-engineering.

## Final Agreed Solution

### 1. `bias_generator.py` (282 LOC → ~260 LOC)

**Extract methods from `generate_cross_tree_constraints()` (93 LOC)**:
- `_generate_from_specific_pairs(config, features)` — handle explicit pair list
- `_generate_from_feature_combinations(features, operators)` — handle all/leaf/extracted modes
- `_create_cross_tree_constraint(feat_a, feat_b, operator)` — single constraint creation

**Cache constraints for `get_statistics()`**:
- Store generated constraints in `self._cached_constraints` during `generate_bias()`
- `get_statistics()` reuses cache instead of regenerating

**Extract constants**:
- None identified in this file (constraint naming is sequential c1..cN)

### 2. `config_loader.py` (203 LOC → ~190 LOC)

**Extract methods from `load()` (107 LOC)**:
- `_parse_hierarchical_candidates(raw_data)` → List[HierarchicalCandidate]
- `_parse_cross_tree_config(raw_data)` → CrossTreeConfig

**Extract constants**:
- `MAX_CROSS_TREE_FEATURES_WARNING = 20` (line 190 magic number)

### 3. `bias_io.py` (222 LOC → ~210 LOC)

**Extract helpers**:
- `_build_feature_json(features)` — feature array construction
- `_build_constraint_json(constraint)` — single constraint serialization

**No split into reader/writer** — current static methods are clear enough.

### 4. `data_structures.py` (213 LOC — no changes)
Stable, well-structured. No improvements needed.

### 5. `clause_generator.py` (199 LOC — no changes)
Clean, under threshold. No improvements needed.

### 6. `__init__.py` (38 LOC — update exports if needed)

## Implementation Considerations

**Risk**: Low — internal method extraction doesn't change public API
**Testing**: Existing tests cover all generation/IO flows. Run `PYTHONPATH=. pytest tests/test_bias_module.py -v` after changes.
**Backward compatibility**: 100% — no public API changes
**Feature ID consistency**: Must preserve — flamapy tree traversal order is critical

## Success Metrics

- [ ] All 6 files ≤200 LOC (or close, with justified exceptions)
- [ ] No method >50 LOC (extract if longer)
- [ ] All magic numbers extracted as named constants
- [ ] `get_statistics()` uses cached constraints (no regeneration)
- [ ] All existing tests pass unchanged
- [ ] No public API changes

## Unresolved Questions

None.
