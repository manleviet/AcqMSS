# Phase 1: ConGen Negation to Build Time

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260227-2316-negation-build-time-refactor.md)

## Overview
- Priority: High
- Status: complete
- Review: complete
- Move negation computation from `ConGenTaskPreparation.prepare()` to `ConGenModelBuilder.build()`

## Key Insights
- `ConGenModelBuilder.build()` currently does NOT require oracle — after refactor it MUST
- `ConGenRunner.__init__()` has oracle available (from `BaseRunner.__init__()` via `super()`)
- Negation uses `oracle.get_bg_data().next_available_id` as starting tseitin var
- `model.next_available_id` must store final tseitin var for prepare() to use

## Related Code Files
- `conacq/algorithms/acqmss/congen_model_builder.py` — add negation to `build()`
- `conacq/algorithms/acqmss/task_preparation.py` — remove negation from `prepare()`
- `conacq/runners/congen_runner.py` — pass oracle to builder

## Implementation Steps

### Step 1: Update ConGenModelBuilder.build()

Add negation computation after loading bias, before auto-prepare:

```python
def build(self) -> ConGenModel:
    self._validate()  # now validates oracle too

    from conacq.bias import BiasIO
    from explanation.operations.algorithms.utils import negate_cnf_tseitin

    bias = BiasIO.load_from_json(self._bias_path)

    model = ConGenModel()
    model.constraint_map = bias.to_constraint_map()
    model.variables = bias.feature_ids
    model._use_incremental = self._use_incremental

    # Compute negation at build time (requires oracle for next_available_id)
    next_tseitin_var = self._oracle.get_bg_data().next_available_id
    for key, c in model.constraint_map.items():
        neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
        model.negated_constraint_map[f"NOT({key})"] = neg_clauses
    model.next_available_id = next_tseitin_var

    # Auto-prepare when oracle + examples present
    if self._oracle and self._has_examples():
        pos, neg = self._resolve_examples()
        model.prepare(
            oracle=self._oracle,
            positive_examples=pos,
            negative_examples=neg or []
        )

    return model
```

### Step 2: Update ConGenModelBuilder._validate()

Require oracle:

```python
def _validate(self) -> None:
    if self._bias_path is None:
        raise ValueError("Bias path required (use from_bias())")
    if self._oracle is None:
        raise ValueError("Oracle required (use with_oracle())")
```

### Step 3: Update ConGenTaskPreparation.prepare()

Remove negation loop (Step 1 in current code). Replace with reading from model:

**Before (lines 97-103):**
```python
# Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
bias_start_pos = len(result.assumptions)
next_tseitin_var = id_assumption
for key, c in model.constraint_map.items():
    neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
    model.negated_constraint_map[f"NOT({key})"] = neg_clauses

id_assumption = next_tseitin_var
```

**After:**
```python
# Step 1: Prepare bias constraints as set_c (negated forms from builder)
bias_start_pos = len(result.assumptions)
id_assumption = model.next_available_id
```

Also remove `negate_cnf_tseitin` import if no longer needed in this file.

### Step 4: Update ConGenRunner.__init__()

Pass oracle to builder:

**Before:**
```python
self.model = (ConGenModelBuilder
              .from_bias(bias_path)
              .use_incremental(use_incremental)
              .build())
```

**After:**
```python
self.model = (ConGenModelBuilder
              .from_bias(bias_path)
              .with_oracle(self.oracle)
              .use_incremental(use_incremental)
              .build())
```

## Todo
- [x] Update `ConGenModelBuilder.build()` — add negation computation
- [x] Update `ConGenModelBuilder._validate()` — require oracle
- [x] Update `ConGenTaskPreparation.prepare()` — remove negation loop
- [x] Update `ConGenRunner.__init__()` — pass oracle to builder
- [x] Verify `negate_cnf_tseitin` import cleanup in task_preparation.py

## Success Criteria
- `ConGenModelBuilder.build()` computes `negated_constraint_map` and `next_available_id`
- `ConGenTaskPreparation.prepare()` reads `negated_constraint_map` without writing
- `ConGenRunner.__init__()` passes oracle to builder

## Risk Assessment
- **Low**: `next_available_id` offset — test suite catches ID misalignment
- **Low**: Import cleanup — check if `negate_cnf_tseitin` used elsewhere in file

## Next Steps
→ Phase 2: Same refactoring for QuAcq
