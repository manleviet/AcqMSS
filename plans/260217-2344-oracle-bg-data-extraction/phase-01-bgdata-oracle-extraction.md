# Phase 1: Create BGData + Oracle Extraction

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260217-2344-oracle-bg-data-extraction.md)

## Overview
- **Priority**: High (foundation for Phase 2)
- **Status**: complete
- **Description**: Create `BGData` frozen dataclass and add post-extraction logic to `OracleTaskPreparation.prepare()`

## Key Insights
- Root BG is always the first pair in Part 3 (constraint_map iteration order from FmToDiagPysat)
- `OracleTaskPreparation.prepare()` remains unchanged in logic — only adds extraction after existing work
- `DescriptionProvider` needs a method to extract descriptions by assumption IDs

## Requirements
- `BGData` dataclass with: `set_kb`, `assumptions`, `negation_map`, `descriptions`, `next_available_id`
- Post-extraction in `OracleTaskPreparation.prepare()` after all Parts 3+4 complete
- Expose `bg_data` property on `FMOracleModel`
- Expose `get_bg_data()` method on `FeatureModelOracle`
- Add assertion that root is first in constraint_map
- Rename `_start_id_assignments` → `_assignments_index` in `FMOracleModel` (clarify it's an index, not an ID value)

## Related Code Files
- **Create**: `conacq/oracle/bg_data.py`
- **Modify**: `conacq/oracle/fm_oracle_model.py` (OracleTaskPreparation.prepare + FMOracleModel property)
- **Modify**: `conacq/oracle/fm_oracle.py` (add get_bg_data)
- **Modify**: `explanation/models/task_preparation.py` (add get_descriptions_for to DescriptionProvider)
- **Modify**: `conacq/oracle/__init__.py` (export BGData)

## Implementation Steps

### 1. Check DescriptionProvider API
Read `explanation/models/task_preparation.py` DescriptionProvider class to see if bulk-read method exists.

### 2. Add `get_descriptions_for()` to DescriptionProvider (if missing)
```python
def get_descriptions_for(self, ids: List[int]) -> Dict[int, str]:
    """Extract descriptions for given assumption IDs."""
    return {aid: self.get_description(aid) for aid in ids if self.get_description(aid)}
```

### 3. Create `conacq/oracle/bg_data.py`
```python
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass(frozen=True)
class BGData:
    """Background knowledge data extracted from Oracle (root BG constraint pair).

    Contains the first assumption pair from Part 3 (FM constraints)
    and the next available ID after Part 4 (variable assignments).
    """
    set_kb: List[List[int]]          # root clause + NOT(root) clause
    assumptions: Tuple[int, int]     # (root_assumption_id, negated_root_assumption_id)
    negation_map: Dict[int, int]     # {root_id: negated_root_id}
    descriptions: Dict[int, str]     # {root_id: "root=true", neg_id: "NOT(root=true)"}
    next_available_id: int           # first free ID after Oracle Parts 3+4
```

### 4. Add BGData extraction to `OracleTaskPreparation.prepare()`
After existing prepare logic completes (all Parts 3+4 done), extract:
```python
# Post-extract root BG data for ConGen consumption
model._bg_data = BGData(
    set_kb=result.set_kb[:2],
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={result.assumptions[0]: result.assumptions[1]},
    descriptions=provider.get_descriptions_for([result.assumptions[0], result.assumptions[1]]),
    next_available_id=id_assumption
)
```

### 5. Add `bg_data` property to `FMOracleModel`
```python
@property
def bg_data(self) -> 'BGData':
    """Root BG data for ConGen. Call prepare() first."""
    if self._bg_data is None:
        raise RuntimeError("Call prepare() first")
    return self._bg_data
```
Initialize `self._bg_data = None` in `__init__`.

### 6. Add `get_bg_data()` to `FeatureModelOracle`
```python
def get_bg_data(self) -> 'BGData':
    """Return BG assumption data (root constraints) for ConGen."""
    return self._oracle_model.bg_data
```

### 7. Update `conacq/oracle/__init__.py`
Add `BGData` to exports.

### 8. Rename `_start_id_assignments` → `_assignments_index`
In `FMOracleModel`: rename `_start_id_assignments` to `_assignments_index` and property `start_id_assignments` to `assignments_index`. Update all references in `_compute_base_set_c()` and `OracleTaskPreparation.prepare()`.

### 9. Add root-first assertion
In `OracleTaskPreparation.prepare()`, after `prepare_kb` returns:
```python
# Verify root constraint is first (invariant from FmToDiagPysat tree-traversal order)
first_key = next(iter(model.constraint_map))
assert 'root' in first_key.lower() or len(model.constraint_map) == 0, \
    f"Expected root as first constraint, got: {first_key}"
```

## Todo
- [ ] Check DescriptionProvider for existing bulk-read method
- [ ] Add get_descriptions_for() if missing
- [ ] Create bg_data.py with BGData dataclass
- [ ] Add extraction logic to OracleTaskPreparation.prepare()
- [ ] Add bg_data property to FMOracleModel
- [ ] Add get_bg_data() to FeatureModelOracle
- [ ] Update oracle __init__.py exports
- [ ] Rename `_start_id_assignments` → `_assignments_index` in FMOracleModel
- [ ] Add root-first assertion

## Success Criteria
- `BGData` dataclass created and populated after `OracleTaskPreparation.prepare()`
- `oracle.get_bg_data()` returns valid BGData with correct root BG entries
- All existing oracle tests pass unchanged

## Risk Assessment
- **Root ordering**: Mitigated by assertion in prepare()
- **DescriptionProvider coupling**: Low risk — adding a simple delegation method

## Next Steps
- Phase 2 consumes `BGData` in `ConGenTaskPreparation`
