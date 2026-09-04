# Brainstorm: Extract Task Preparation from FMOracleModel

## Problem Statement
`FMOracleModel` mixes model state with task preparation logic. Specifically, `_compute_base_set_c()` and set_c computation in `with_configuration()` are preparation concerns that should live in `FMOracleTaskPreparation`.

## Agreed Design

### 1. FMOracleTaskPreparation.prepare(model, configuration=None)
- Compute `base_set_c` (stride through assumptions for FM constraint IDs)
- Assign directly: `model._base_set_c = base_set_c`
- If `configuration` provided → compute full `set_c = base_set_c + assignment_assumptions`
- If not → `set_c = base_set_c`
- PreparationOutput unchanged

### 2. FMOracleModel changes
- Add `_base_set_c: list = []` in `__init__`
- **Remove** `_compute_base_set_c()` entirely
- `prepare(configuration=None)` → delegates to TaskPreparation with config param
- `with_configuration(config)`:
  - Convert config → assignment assumptions (using existing `_pos/_neg_assignment_to_assumption` maps)
  - `set_c = self._base_set_c + assignment_assumptions`
  - Update `self._task.set_c = set_c`
  - **Return self** (fluent chaining)

### 3. Caller impact
- `FeatureModelOracle.is_valid()` — minor update: `with_configuration` now returns `FMOracleModel` instead of `list`. Current code already calls `get_c()` separately, so minimal change.
- Tests — update assertions for return type change

## Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| with_configuration return | `self` (mutate) | Fluent chaining, simple |
| _compute_base_set_c | Remove, cache in prepare | Computed once, no need to recompute |
| base_set_c storage | Direct model assignment | Consistent with existing pattern (model._assignments_start_index, etc.) |
| Config→assumptions logic | Keep in FMOracleModel | Uses model state, simpler than passing many params |
| prepare() signature | Add `configuration=None` | Compute full set_c upfront when config known |

## Risk Assessment
- **Low risk**: Changes are internal to oracle package, well-tested
- Callers of `with_configuration` need return type update (list → FMOracleModel)
- Tests verify correctness via checker integration
