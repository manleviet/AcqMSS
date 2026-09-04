# Phase 2: Refactor run_cv.py to Emit Unified JSON

## Context Links
- `apps/run_cv.py` — Current CV runner (216 lines)
- `conacq/eval/report.py` — `generate_unified_cv_dict()` (from Phase 1)
- `conacq/bias/data_structures.py` — `Bias`
- `conacq/bias/bias_io.py` — `BiasIO.load_from_json()`

## Overview
- Priority: P1
- Status: completed
- Replace multi-file output with single unified JSON per (model x strategy x mode)

## Key Insights
- Currently `run_cv.py` writes 3 categories of files per run:
  1. `{model}_cv_{mode}.json` — CV summary (via `cv_result.to_dict()`)
  2. `{model}_{mode}_fold{i}_kb.json` — Per-fold KB (via `save_cv_kb_files()`)
  3. `{model}_{mode}_intersected_kb.json` — Intersected KB (via `save_cv_kb_files()`)
- After refactor: single `{model}_cv_{mode}.json` containing everything
- Need to load `Bias` once per model (shared across solver modes) to resolve descriptions
- Bias is already loaded for interactive algorithm; for congen it's only used as a path currently

## Requirements

### Functional
1. Output single `{model}_cv_{mode}.json` per (model x strategy x mode)
2. File contains fold KB data, intersected KB, evaluation placeholders
3. `kb_constraints` in folds and intersected_kb include `{id, description}` objects
4. Remove `save_cv_kb_files()` call entirely
5. Load Bias once per model iteration (not per solver mode)

### Non-functional
- Keep file under 200 lines
- Maintain same CLI interface (config + args)

## Related Code Files

### Modify
- `apps/run_cv.py`

## Implementation Steps

### Step 1: Update imports

Replace:
```python
from conacq.eval import (
    n_fold_cross_validation,
    n_fold_cross_validation_interactive,
    generate_cv_report,
    save_cv_kb_files,   # REMOVE
    load_folds,
)
```

With:
```python
from conacq.eval import (
    n_fold_cross_validation,
    n_fold_cross_validation_interactive,
    generate_cv_report,
    generate_unified_cv_dict,   # NEW
    load_folds,
)
```

### Step 2: Load Bias once per model

In the model loop (line ~114), after loading examples and before the solver mode loop:

```python
# Load bias for description resolution
bias = BiasIO.load_from_json(model_config.bias)
```

Note: `BiasIO` is already imported for interactive algorithm. Move the import up so it's used for both.

### Step 3: Replace output logic

Replace lines 183-196 (current output block):

```python
# OLD:
cv_dict = cv_result.to_dict()
cv_file = output_dir / f"{model_config.name}_cv_{mode_name}.json"
cv_file.parent.mkdir(parents=True, exist_ok=True)
with open(cv_file, 'w') as f:
    json.dump(cv_dict, f, indent=2)
print(f"  CV result: {cv_file}")

saved_kbs = save_cv_kb_files(cv_result, output_dir, model_config.name, mode_name)
print(f"  Saved {len(saved_kbs['fold_kbs'])} fold KB files")
print(f"  Intersected KB: {len(cv_result.intersected_kb)} constraints")
print(f"  -> {saved_kbs['intersected_kb']}")
```

With:

```python
# NEW: Single unified JSON output
unified = generate_unified_cv_dict(cv_result, bias)
cv_file = output_dir / f"{model_config.name}_cv_{mode_name}.json"
cv_file.parent.mkdir(parents=True, exist_ok=True)
with open(cv_file, 'w') as f:
    json.dump(unified, f, indent=2)
print(f"  Unified CV: {cv_file}")
print(f"  Intersected KB: {len(cv_result.intersected_kb)} constraints")
```

### Step 4: Remove unused BiasIO import guard

Currently `BiasIO` import is at top but Bias is only loaded inside `elif algorithm == 'interactive'`. Move the bias loading before the solver loop so both algorithms use it.

## Full diff summary

```
apps/run_cv.py:
  - Import: replace save_cv_kb_files -> generate_unified_cv_dict
  - Line ~120: Add `bias = BiasIO.load_from_json(model_config.bias)` before solver loop
  - Lines ~183-196: Replace multi-file output with single unified JSON
  - Remove: interactive-specific bias loading (already done above)
```

## Todo List
- [ ] Update imports in `run_cv.py`
- [ ] Load Bias once per model before solver mode loop
- [ ] Replace output block with `generate_unified_cv_dict()` + single JSON write
- [ ] Remove redundant bias loading in interactive branch (keep for `bias.to_constraint_map()` usage)
- [ ] Verify CLI still works with `python -m apps.run_cv apps/conf/run_cv_config.toml -v`

## Success Criteria
- Single JSON file produced per (model x strategy x mode)
- File matches target unified structure from requirements
- No fold KB or intersected KB files produced separately
- `run_cv.py` stays under 200 lines
- `python -m apps.run_cv apps/conf/run_cv_config.toml -v` runs successfully

## Risk Assessment
- **Risk**: Interactive algorithm loads bias differently (for `to_constraint_map()`)
  - **Mitigation**: Load bias once at model level; reuse for both description resolution and interactive runner
