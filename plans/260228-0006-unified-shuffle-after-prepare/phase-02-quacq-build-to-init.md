# Phase 2: Move QuAcqRunner Build to __init__

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-simplify-congen-shuffle.md) (pattern established)
- File: `conacq/runners/quacq_runner.py`

## Overview
- Priority: P3
- Description: Build model once in __init__, re-prepare per run, shuffle set_c after
- Implementation status: complete
- Review status: complete

## Key Insights
- QuAcqModelBuilder.build() runs expensive negate_cnf_tseitin — should happen once
- QuAcqModel.prepare() creates fresh QuAcqTask each call → safe to re-call
- model.next_available_id stays fixed across prepare() calls
- After refactor: consistent with ConGenRunner pattern

## Requirements
- Build model once in __init__ (not per run)
- Remove _feature_ids cache (use model.variables)
- Remove _use_incremental field
- In run(): re-prepare model, shuffle set_c after
- All references to local `model` → `self.model`

## Related Code Files
- Modify: `conacq/runners/quacq_runner.py`
- Test: `tests/test_quacq.py`

## Implementation Steps

1. In `__init__`: Replace `_use_incremental` + `_feature_ids` with model build:
   ```python
   # DELETE:
   self._use_incremental = use_incremental
   from conacq.bias import BiasIO
   self._feature_ids = BiasIO.load_from_json(bias_path).feature_ids

   # ADD:
   from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
   self.model = (QuAcqModelBuilder
                 .from_bias(bias_path)
                 .with_oracle(self.oracle)
                 .use_incremental(use_incremental)
                 .build())
   ```

2. Update `feature_ids` property (lines 92-95):
   ```python
   # BEFORE:
   return self._feature_ids
   # AFTER:
   return self.model.variables
   ```

3. In `run()`: Replace builder block with re-prepare:
   ```python
   # DELETE (lines ~153-160):
   from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
   model = (QuAcqModelBuilder
            .from_bias(self.bias_path)
            .with_oracle(self.oracle)
            .use_incremental(self._use_incremental)
            .build())
   task = model.task

   # ADD:
   self.model.prepare(self.oracle)
   task = self.model.task
   ```

4. Shuffle stays the same (already shuffles set_c):
   ```python
   if shuffle_seed is not None:
       random.Random(shuffle_seed).shuffle(task.set_c)
       logging.debug('Shuffled bias (set_c) with seed=%d', shuffle_seed)
   ```

5. Update all `model.xxx` → `self.model.xxx` in run():
   - `model.description_provider` → `self.model.description_provider`
   - `model.resolve_kb(...)` → `self.model.resolve_kb(...)`
   - `model.constraint_map` → `self.model.constraint_map`

6. Remove lazy imports from run() that are now in __init__:
   - `QuAcqModelBuilder` import moves to __init__

## Todo List
- [ ] Replace _use_incremental + _feature_ids with model build in __init__
- [ ] Update feature_ids property to use model.variables
- [ ] Replace builder block in run() with model.prepare()
- [ ] Update model references to self.model in run()
- [ ] Clean up imports (move QuAcqModelBuilder import to __init__)
- [ ] Update __init__ docstring

## Success Criteria
- QuAcqRunner builds model once in __init__
- No _feature_ids, _use_incremental fields
- run() calls model.prepare() + shuffles set_c
- Pattern matches ConGenRunner
- All QuAcq tests pass

## Risk Assessment
- Low risk: prepare() verified to create fresh task each call
- model.next_available_id stays fixed (explicit code comment in ConGenTaskPreparation)
- resolve_kb() is read-only — no model state mutation
