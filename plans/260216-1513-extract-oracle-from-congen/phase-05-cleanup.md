# Phase 5: Cleanup Dead Code

## Context Links
- [plan.md](./plan.md)
- [phase-04-update-runner-and-tests.md](./phase-04-update-runner-and-tests.md)
- [data_structures.py](../../conacq/bias/data_structures.py)

## Overview
- **Date**: 2026-02-16
- **Description**: Remove dead code (`bias.root_feature` property), update documentation and docstrings to reflect new architecture.
- **Priority**: P2
- **Implementation Status**: Pending
- **Review Status**: Pending

## Key Insights
- `Bias.root_feature` property (data_structures.py:96-102) only used by builder (line 122: `model.root_feature = bias.root_feature`). After Phase 3, no callers remain.
- `Bias.to_constraint_maps_with_negation()` (data_structures.py:128-147) -- check if still used. Was commented out in builder (line 116). If no callers, remove.
- Documentation files reference old builder API (`from_bias_and_fm_uvl`, `from_bias_and_fm_fide`) -- must update.

## Requirements

### Functional
- Remove `Bias.root_feature` property if no remaining callers
- Remove `Bias.to_constraint_maps_with_negation()` if no remaining callers
- Update documentation to reflect new API

### Non-Functional
- Cleaner codebase, no dead code

## Architecture

No structural changes -- cleanup only.

## Related Code Files

### Files to Modify
| File | Change |
|------|--------|
| `acqmss/bias/data_structures.py` | Remove dead properties/methods |
| `docs/system-architecture.md` | Update builder examples, ConGen flow |
| `docs/code-standards.md` | Update builder usage pattern |
| `docs/codebase-summary.md` | Update file descriptions, builder pattern |
| `README.md` | Update quick-start example if using old API |

### Files to Verify (grep for remaining callers)
| Pattern | Expected Result |
|---------|----------------|
| `bias.root_feature` | No callers after Phase 3 |
| `to_constraint_maps_with_negation` | No callers (was commented out) |
| `from_bias_and_fm_uvl` | No callers after Phase 4 |
| `from_bias_and_fm_fide` | No callers after Phase 4 |
| `model._oracle` | No references after Phase 2 |
| `model._fm_path` | No references after Phase 2 |
| `model.num_fm_constraints` | No references after Phase 2 |

## Implementation Steps

### Step 1: Verify no remaining callers

```bash
# Check for remaining references to dead code
PYTHONPATH=. grep -rn "bias\.root_feature" acqmss/ apps/ tests/
PYTHONPATH=. grep -rn "to_constraint_maps_with_negation" acqmss/ apps/ tests/
PYTHONPATH=. grep -rn "from_bias_and_fm_uvl\|from_bias_and_fm_fide" acqmss/ apps/ tests/
PYTHONPATH=. grep -rn "model\._oracle\|model\.oracle\|model\._fm_path\|model\.num_fm_constraints" acqmss/ apps/ tests/
```

### Step 2: Remove dead code from `data_structures.py`

1. **Remove `Bias.root_feature`** property (lines 96-102):
   ```python
   # DELETE:
   @property
   def root_feature(self) -> Optional[str]:
       """Assume the root feature is the one with ID 1 (if exists)"""
       for f in self.features:
           if f.id == 1:
               return f.name
       return self.features[0].name if self.features else None
   ```

2. **Remove `Bias.to_constraint_maps_with_negation()`** (lines 128-147) if grep confirms no callers:
   ```python
   # DELETE if unused:
   def to_constraint_maps_with_negation(self) -> Tuple[...]:
       ...
   ```
   Also remove `Tuple` from typing imports if no longer needed.

### Step 3: Update documentation

1. **`docs/system-architecture.md`**:
   - Update ConGen Data Flow diagram (lines ~326-351) -- show oracle created externally
   - Update Core API example (lines ~57-77) -- use `from_bias()` + oracle
   - Update builder pattern description

2. **`docs/code-standards.md`**:
   - Update builder pattern example (lines ~273-295) -- use new `from_bias()` API
   - Update oracle usage examples if needed

3. **`docs/codebase-summary.md`**:
   - Update `congen_model.py` description (line 24) -- "pure data container"
   - Update `congen_model_builder.py` description (line 25) -- "bias-only builder"
   - Update builder pattern reference (line 293)
   - Update GenerateNE description (line 85) -- oracle injected at prepare time

4. **`README.md`**:
   - Update quick-start example if it uses `from_bias_and_fm_uvl()`

### Step 4: Run full test suite
```bash
PYTHONPATH=. pytest tests/ -v
```

## Todo List
- [ ] Grep for remaining callers of dead code
- [ ] Remove `Bias.root_feature` property
- [ ] Remove `Bias.to_constraint_maps_with_negation()` if unused
- [ ] Update `docs/system-architecture.md` -- builder examples, data flow
- [ ] Update `docs/code-standards.md` -- builder pattern
- [ ] Update `docs/codebase-summary.md` -- file descriptions
- [ ] Update `README.md` -- quick-start example
- [ ] Run full test suite

## Success Criteria
- Zero dead code references (grep clean)
- All documentation reflects new oracle-injection pattern
- All tests pass
- `from_bias_and_fm_*` pattern gone from entire codebase (except old plans/)

## Risk Assessment
- **Very Low**: Removing verified-dead code; documentation-only changes
- **Low**: If `to_constraint_maps_with_negation()` has hidden callers, keep it

## Security Considerations
- None

## Next Steps
- Refactoring complete. Update `docs/project-roadmap.md` with completion status.
