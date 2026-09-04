# Brainstorm: ConGenModelBuilder Auto-Prepare

## Problem Statement

`ConGenModelBuilder` stores examples via `with_examples()`/`with_examples_data()` but `build()` ignores them. Callers must manually call `get_examples()` + `model.prepare()`. This creates a leaky abstraction and verbose boilerplate for the common single-run case.

**Goal**: Support two clean patterns:
1. **Single run** — builder handles everything, `build()` returns prepared model
2. **CV mode** — build once (bias only), `prepare()` per fold

## Evaluated Approaches

### A) Auto-prepare in build() (CHOSEN)
- `build()` detects oracle + examples → calls `prepare()` internally
- CV path unchanged — build without oracle, prepare per fold
- **Pros**: Minimal API change, backward compatible, KISS
- **Cons**: `build()` does two things (construct + prepare) — acceptable trade-off

### B) Separate PreparedConGenModel type
- Different return type signals state at compile time
- **Pros**: Type safety
- **Cons**: Type proliferation, YAGNI for this project

### C) Explicit prepare_and_build() method
- New method alongside `build()` that also prepares
- **Pros**: Clear intent
- **Cons**: Unnecessary API surface, DRY violation

## Final Design

### API

```python
# Pattern 1: Auto-prepare from file
model = (ConGenModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(FeatureModelOracle('data/fms/model.uvl'))
         .with_examples('data/examples/REAL-FM-7_ff.json')
         .build())

# Pattern 2: Auto-prepare from raw data
model = (ConGenModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(FeatureModelOracle('data/fms/model.uvl'))
         .with_examples_data(positive_examples=pos, negative_examples=neg)
         .build())

# Pattern 3: CV mode (build once, prepare per fold)
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
oracle = FeatureModelOracle('data/fms/model.uvl')
for fold_pos, fold_neg in folds:
    model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
```

### build() Logic

```python
def build(self):
    self._validate()
    bias = BiasIO.load_from_json(self._bias_path)
    model = ConGenModel(constraint_map=bias.constraint_map,
                        variables=bias.variables,
                        use_incremental=self._use_incremental)

    # Auto-prepare when oracle + examples both present
    if self._oracle and self._has_examples():
        pos, neg = self._resolve_examples()
        model.prepare(oracle=self._oracle,
                      positive_examples=pos,
                      negative_examples=neg)

    return model
```

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Return type | Same `ConGenModel` | No type proliferation, KISS |
| File loading | Lazy in `build()` | Builder stays cheap until commit |
| Negative examples | Optional | Only positive required for `_has_examples()` |
| Re-prepare | Allowed (idempotent) | CV loop pattern works as-is |
| Oracle wiring | Instance via `with_oracle(oracle)` | Caller controls oracle config |
| with_examples vs with_examples_data conflict | Last one wins | Simpler, no error handling needed |

## Implementation Changes

### 1. Add `with_oracle()` method
- New field: `_oracle: Optional[FeatureModelOracle] = None`
- Method stores oracle instance, returns self for chaining

### 2. Modify `build()`
- After model construction, check `self._oracle and self._has_examples()`
- If true: resolve examples (lazy-load JSON if path), call `model.prepare()`
- If false: return unprepared model (current behavior)

### 3. Validation updates
- `_has_examples()`: checks positive_examples is not None (negative optional)
- `with_examples()` sets path, clears raw data fields
- `with_examples_data()` sets raw data, clears path field
- Last call wins — no conflict error

### 4. No changes to ConGenModel.prepare()
- `prepare()` remains idempotent, supports re-prepare for CV
- No signature changes needed

## Risk Assessment

- **Low risk**: Backward compatible — existing `build()` without oracle returns unprepared model as before
- **Edge case**: Calling `build()` with oracle but no examples → unprepared model (same as no oracle)
- **Edge case**: Calling `build()` with examples but no oracle → unprepared model, examples stored but unused

## Success Criteria

- [ ] All 3 API patterns work as documented
- [ ] Existing tests pass without modification
- [ ] CV mode (ConGenRunner) continues to work
- [ ] New tests cover auto-prepare path
