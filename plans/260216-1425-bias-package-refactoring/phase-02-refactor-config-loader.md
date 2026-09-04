# Phase 2: Refactor config_loader.py

## Context Links
- Parent plan: `plans/260216-1425-bias-package-refactoring/plan.md`
- Source: `acqmss/bias/config_loader.py` (203 LOC → target ~190 LOC)

## Overview
- **Priority**: P2
- **Status**: pending
- **Description**: Extract parsing helpers from `load()` (107 LOC monolith) and extract magic numbers.

## Key Insights
- `load()` (lines 27-133) has 3 distinct parsing sections: features (lines 71-83), hierarchical candidates (lines 85-106), cross-tree config (lines 108-125). Last two are good extraction candidates.
- Magic number `20` on line 190 in `validate_config()` — warning threshold for large feature sets.
- `validate_config()` (lines 135-203) is already well-structured, but the 20-feature threshold should be a named constant.

## Related Code Files
- **Modify**: `acqmss/bias/config_loader.py`
- **Read**: `acqmss/bias/data_structures.py` (BiasConfig, HierarchicalCandidate, CrossTreeConfig)

## Implementation Steps

### Step 1: Extract constant
Add at module level (after imports, before class):
```python
_MAX_CROSS_TREE_FEATURES_WARNING = 20
```
Replace line 190 `> 20` with `> _MAX_CROSS_TREE_FEATURES_WARNING`.

### Step 2: Extract `_parse_hierarchical_candidates()` (lines 86-106)
```python
@staticmethod
def _parse_hierarchical_candidates(data: dict) -> list:
```
Move lines 87-106 into this method. Takes raw `data` dict, returns list of `HierarchicalCandidate`.

### Step 3: Extract `_parse_cross_tree_config()` (lines 108-125)
```python
@staticmethod
def _parse_cross_tree_config(data: dict) -> CrossTreeConfig:
```
Move lines 109-125 into this method. Takes raw `data` dict, returns `CrossTreeConfig`.

### Step 4: Simplify `load()`
After extraction, `load()` becomes:
```python
@staticmethod
def load(config_path: str) -> BiasConfig:
    # File loading + YAML parsing (lines 64-69) — keep as-is
    # Feature parsing (lines 71-83) — keep inline (simple)
    hierarchical_candidates = BiasConfigLoader._parse_hierarchical_candidates(data)
    cross_tree_config = BiasConfigLoader._parse_cross_tree_config(data)
    return BiasConfig(...)
```

## Todo
- [ ] Extract `_MAX_CROSS_TREE_FEATURES_WARNING` constant
- [ ] Extract `_parse_hierarchical_candidates()` static method
- [ ] Extract `_parse_cross_tree_config()` static method
- [ ] Simplify `load()` to use extracted methods

## Success Criteria
- [ ] `load()` is <50 LOC
- [ ] No magic numbers remain
- [ ] No public API changes
- [ ] File total ≤200 LOC

## Risk Assessment
- **Low**: Pure extraction, same validation logic preserved
