# Phase 3: Remove `from_bias_and_examples` + Cleanup

## Context Links
- [ConGenModel](../../conacq/algorithms/congen_model.py)
- [README](../../README.md) | [CLAUDE.md](../../CLAUDE.md)
- [codebase-summary.md](../../docs/codebase-summary.md) | [system-architecture.md](../../docs/system-architecture.md)
- [Phase 2](phase-02-migrate-callers.md) | [Plan](plan.md)

## Overview
- **Priority**: P2
- **Status**: complete
- **Description**: Remove `from_bias_and_examples()` from ConGenModel, update documentation to show builder pattern exclusively.

## Key Insights

1. After Phase 2, no callers use `from_bias_and_examples()` — safe to delete
2. Docs (README, CLAUDE.md, codebase-summary, system-architecture) reference old API
3. `_examples_to_testsuite` static method stays — still used by builder and `prepare()`

## Requirements

### Functional
- `from_bias_and_examples()` classmethod removed from ConGenModel
- All docs updated to show builder pattern

### Non-functional
- No references to removed method anywhere in codebase (excluding old plans)

## Related Code Files

- **Modify**: `acqmss/algorithms/congen_model.py` — remove `from_bias_and_examples()`
- **Modify**: `README.md` — update code example
- **Modify**: `CLAUDE.md` — update API patterns section
- **Modify**: `docs/codebase-summary.md` — update factory pattern reference
- **Verify**: `docs/system-architecture.md` — remove any stale refs

## Implementation Steps

### Step 1: Remove `from_bias_and_examples()` from ConGenModel

Delete lines 134-175 in `congen_model.py` (the entire classmethod).

### Step 2: Update README.md

```python
# BEFORE:
from conacq.algorithms import ConGen, ConGenModel

model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias, positive_examples=E_plus, ...)

# AFTER:
from conacq.algorithms import ConGen, ConGenModelBuilder

model = (ConGenModelBuilder
         .from_bias_and_fm_uvl('data/bias/model.json', 'data/fms/model.uvl')
         .with_examples('data/examples/examples.json')
         .build())
```

### Step 3: Update CLAUDE.md

The "Alternative: Direct model construction" section references `ConGenModel.from_bias_and_examples`. Replace with note about CV fold pattern:

```python
# For CV folds (build once, reuse per fold):
model = (ConGenModelBuilder
    .from_bias_and_fm_uvl('data/bias/model.json', 'data/fms/model.uvl')
    .use_incremental(True)
    .with_solver('glucose4')
    .build())  # No examples → unprepared model

# Per fold:
task = model.prepare(
    positive_examples=fold_pos,
    negative_examples=fold_neg,
    profiler=profiler
)
```

### Step 4: Update docs/codebase-summary.md

Replace `ConGenModel.from_bias_and_examples()` factory reference with:
```
- `ConGenModelBuilder.from_bias_and_fm_uvl()` / `from_bias_and_fm_fide()` — Builder-pattern model construction
```

### Step 5: Verify docs/system-architecture.md

Search for any remaining `from_bias_and_examples` references and remove.

### Step 6: Final grep verification

```bash
grep -r "from_bias_and_examples" --include="*.py" --include="*.md" \
    --exclude-dir=plans .
```

Should return zero matches (excluding plans/).

## Todo List

- [x] Remove `from_bias_and_examples()` from `congen_model.py`
- [x] Update `README.md` code example
- [x] Update `CLAUDE.md` API patterns section
- [x] Update `docs/codebase-summary.md`
- [x] Verify `docs/system-architecture.md` — no stale refs
- [x] Run final grep to confirm zero remaining references
- [x] Run all tests

## Success Criteria

- `grep -r "from_bias_and_examples" --include="*.py" .` returns zero matches
- All tests pass
- Docs show builder pattern exclusively

## Risk Assessment

- **Very low**: method already unused after Phase 2
- If any caller was missed, tests will fail immediately with `AttributeError`

## Security Considerations

None — internal cleanup only.

## Next Steps

None — refactor complete after this phase.
