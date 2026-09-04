# Phase 2: QuAcq Negation to Build Time

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-congen-negation-build-time.md) (same pattern)

## Overview
- Priority: High
- Status: complete
- Review: complete
- Move negation from `QuAcqTaskPreparation.prepare()` to `QuAcqModelBuilder.build()`

## Key Insights
- `QuAcqModelBuilder` already requires oracle — `_validate()` checks it
- `QuAcqModelBuilder.build()` already calls `model.prepare(oracle)` — negation must happen BEFORE that call
- QuAcqRunner builds fresh model each `run()` — so negation at build time runs each run anyway, but now `prepare()` is idempotent

## Related Code Files
- `conacq/algorithms/quacq/quacq_model_builder.py` — add negation to `build()`
- `conacq/algorithms/quacq/task_preparation.py` — remove negation from `prepare()`

## Implementation Steps

### Step 1: Update QuAcqModelBuilder.build()

Add negation before `model.prepare()`:

```python
def build(self) -> QuAcqModel:
    self._validate()

    from conacq.bias import BiasIO
    from explanation.operations.algorithms.utils import negate_cnf_tseitin

    bias = BiasIO.load_from_json(self._bias_path)

    model = QuAcqModel()
    model.constraint_map = bias.to_constraint_map()
    model.variables = bias.feature_ids
    model.use_incremental = self._use_incremental

    # Compute negation at build time (before prepare)
    next_tseitin_var = self._oracle.get_bg_data().next_available_id
    for key, c in model.constraint_map.items():
        neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
        model.negated_constraint_map[f"NOT({key})"] = neg_clauses
    model.next_available_id = next_tseitin_var

    model.prepare(self._oracle)
    return model
```

### Step 2: Update QuAcqTaskPreparation.prepare()

Remove negation loop (Step 1 in current code):

**Before (lines 183-187):**
```python
# Step 1: Negate bias constraints using Tseitin transformation
next_tseitin_var = id_assumption
for key, c in model.constraint_map.items():
    neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
    model.negated_constraint_map[f"NOT({key})"] = neg_clauses

# Step 2: Assign assumption IDs via prepare_kb()
id_assumption = next_tseitin_var
```

**After:**
```python
# Step 1: Assign assumption IDs (negated forms from builder)
id_assumption = model.next_available_id
```

Also remove `negate_cnf_tseitin` import if no longer needed.

### Step 3: QuAcqRunner — no change needed

QuAcqRunner already passes oracle to builder in `run()`:
```python
model = (QuAcqModelBuilder
         .from_bias(self.bias_path)
         .with_oracle(self.oracle)
         .use_incremental(self._use_incremental)
         .build())
```

## Todo
- [x] Update `QuAcqModelBuilder.build()` — add negation computation
- [x] Update `QuAcqTaskPreparation.prepare()` — remove negation loop
- [x] Verify `negate_cnf_tseitin` import cleanup in task_preparation.py
- [x] Verify QuAcqRunner unchanged

## Success Criteria
- `QuAcqModelBuilder.build()` computes `negated_constraint_map` and `next_available_id`
- `QuAcqTaskPreparation.prepare()` reads without writing
- QuAcqRunner works unchanged

## Risk Assessment
- **Low**: Same risk as Phase 1 — ID offset, caught by tests

## Next Steps
→ Phase 3: Run full test suite
