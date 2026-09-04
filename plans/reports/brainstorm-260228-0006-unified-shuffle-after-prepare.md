# Brainstorm: Unified Shuffle-After-Prepare Pattern

## Problem
- ConGenRunner shuffles `constraint_map` before `prepare()` + needs `_original_bias_constraint_order` snapshot
- QuAcqRunner rebuilds model every `run()` call (expensive negation recomputed)
- Two different shuffle patterns for same goal: randomize bias constraint iteration order

## Analysis
- SAT solver doesn't care about clause order in set_kb — only `set_c` iteration order matters
- Both `ConGenTaskPreparation.prepare()` and `QuAcqTaskPreparation.prepare()` create fresh task objects
- `prepare_kb()` derives set_c from constraint_map iteration order
- Shuffling set_c after prepare() = shuffling constraint_map before prepare() → identical algorithmic effect

## Agreed Solution: Shuffle set_c after prepare()

### ConGenRunner changes
- Remove `_original_bias_constraint_order` from `__init__`
- Remove constraint_map shuffle block from `run()`
- Shuffle `task.set_c` after `prepare()` call

### QuAcqRunner changes
- Move `QuAcqModelBuilder.build()` from `run()` to `__init__` (build once, reuse model)
- Remove `_feature_ids` cache — use `model.variables` directly (like ConGenRunner)
- Remove `_use_incremental` field (no longer needed after build moves to __init__)
- In `run()`: call `model.prepare(oracle)` before each run, shuffle `task.set_c` after

### Both runners: consistent pattern
```python
# __init__: build model once (expensive)
self.model = Builder.from_bias(...).with_oracle(...).use_incremental(...).build()

# run(): re-prepare per run (cheap), then shuffle
self.model.prepare(oracle=self.oracle, ...)
task = self.model.task
if shuffle_seed is not None:
    random.Random(shuffle_seed).shuffle(task.set_c)
```

## Risks
| Risk | Mitigation |
|---|---|
| prepare() not fully resetting task state | Verified: creates fresh task objects each call |
| model.next_available_id drift | Verified: explicit NOTE in code not to update |
| Test regression | Full test suite validation required |

## Validation
- All existing tests must pass with identical results
- Same seeds must produce same KB output (deterministic)

## Status
Agreed — ready for implementation plan
