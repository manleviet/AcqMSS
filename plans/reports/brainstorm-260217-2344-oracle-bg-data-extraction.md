# Brainstorm: Oracle BG Data Extraction for ConGen

## Problem Statement
`ConGenTaskPreparation._prepare_bg` duplicates root BG constraint logic that Oracle already computes. Additionally, `FMData` and manual ID skip arithmetic in ConGenTaskPreparation are redundant because `FMOracleModel` already owns this data.

## Shared Assumption ID Layout (Critical Context)
```
Part 1: Feature variable IDs (1..n)               ← FmToDiagPysat
Part 2: Tseitin vars (negated FM constraints)      ← FmToDiagPysat
Part 3: FM constraint assumptions (paired)         ← OracleTaskPreparation
        [root, NOT(root), c2, NOT(c2), ...]
Part 4: Variable assignment assumptions            ← OracleTaskPreparation
        [f1=true, f1=false, f2=true, ...]
Part 5: Tseitin vars (negated bias constraints)    ← ConGenTaskPreparation
Part 6: Bias constraints (paired)                  ← ConGenTaskPreparation
Part 7: Positive test cases (paired)               ← ConGenTaskPreparation
Part 8: NE + negated NE                            ← ConGenTaskPreparation

Oracle owns Parts 1-4. ConGen owns Parts 5-8.
ConGen needs from Oracle: Part 3's first pair (root BG) + end-of-Part-4 ID.
```

## Approaches Evaluated

### Approach A (Original): Copy BG — Pre-separate root from constraint_map
- Oracle separates root constraint before prepare_kb, prepares it individually
- Pro: Full DRY. Con: Oracle prepare() restructured, ~25-30 lines new code

### Approach B: Keep `_prepare_bg`, get inputs from Oracle
- ConGen keeps _prepare_bg, gets root_feature + next_available_id from Oracle
- Pro: Minimal Oracle changes (~5 lines). Con: 15-line DRY violation on trivial code

### Approach A2 (Chosen): Post-extract into dataclass
- Oracle prepare() runs unchanged. After completion, extract root BG entries into a frozen dataclass.
- Pro: Full DRY, Oracle prepare() unchanged, ~10 lines new code. Con: Depends on root being first in constraint_map (confirmed by shared ID layout).

## Final Recommendation: Approach A2

1. Create `BGData` frozen dataclass (set_kb, assumptions, negation_map, descriptions, next_available_id)
2. After `OracleTaskPreparation.prepare()`, extract first pair from Part 3 into `BGData`
3. Expose `BGData` via `FMOracleModel` (or `FeatureModelOracle`)
4. `ConGenTaskPreparation.prepare()` copies BGData entries → eliminates `_prepare_bg` + skip arithmetic + `FMData` parameter
5. Document shared ID layout in both Oracle and ConGen classes

## Implementation Scope
- **Remove**: `_prepare_bg` function, `FMData` from ConGenTaskPreparation.prepare() signature, skip arithmetic
- **Add**: `BGData` dataclass, extraction in OracleTaskPreparation, ID layout documentation
- **Modify**: ConGenTaskPreparation.prepare(), ConGenModel.prepare(), callers passing FMData
- **Verify**: FMData still used by InteractiveLearner._build_task_from_bias (keep FMData class)
