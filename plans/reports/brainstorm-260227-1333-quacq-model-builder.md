# Brainstorm: QuAcqModelBuilder

## Problem Statement
Create QuAcqModelBuilder mirroring ConGenModelBuilder for API consistency and future extensibility.

## Evaluated Approaches

### A: Full Builder (CHOSEN)
Mirror ConGenModelBuilder with `from_bias()`, `with_oracle()`, `use_incremental()`, `build()`.
- **Pros**: Consistent API, ready for future config, familiar pattern
- **Cons**: Only 2 params now (bias_path, use_incremental) — slight overhead

### B: Keep Factory (Deferred)
Keep `from_bias()` classmethod, create builder later when needed.
- **Pros**: YAGNI-compliant, less code
- **Cons**: Inconsistent API between ConGen and QuAcq

### C: Hybrid (Extend from_bias)
Add optional params to `from_bias()` as needed.
- **Pros**: Minimal change
- **Cons**: Factory method grows unwieldy with many params

## Final Recommended Solution

**Approach A** — Create `QuAcqModelBuilder` in `conacq/algorithms/quacq/quacq_model_builder.py`.

### API Design

```python
# Only pattern: always build with oracle, always auto-prepare
oracle = FeatureModelOracle('model.uvl')
model = (QuAcqModelBuilder
         .from_bias('bias.json')
         .with_oracle(oracle)
         .build())  # → prepared model with task ready
```

`with_oracle()` is **required**. `build()` raises ValueError if oracle not set.
Runner rebuilds model each run (no model reuse pattern).

### Method Mapping (ConGen → QuAcq)

| ConGenModelBuilder | QuAcqModelBuilder | Notes |
|---|---|---|
| `from_bias(path)` | `from_bias(path)` | Same |
| `with_oracle(oracle)` | `with_oracle(oracle)` | **Required** (not optional) |
| `with_examples(path)` | N/A | QuAcq = interactive |
| `with_examples_data(pos, neg)` | N/A | No batch examples |
| `use_incremental(bool)` | `use_incremental(bool)` | Same |
| `build()` | `build()` | **Always** auto-prepares |
| `get_examples()` | N/A | No examples |
| `_validate()` | `_validate()` | Validates bias_path + oracle required |

### Key Differences from ConGenModelBuilder
- No `with_examples*()` methods — QuAcq learns interactively, no batch examples
- `with_oracle()` **required** (ConGen: optional, enables auto-prepare)
- `build()` **always** auto-prepares (ConGen: only when oracle+examples set)
- No model reuse pattern — runner rebuilds model each run via builder

## Implementation Considerations

### Files to Create
- `conacq/algorithms/quacq/quacq_model_builder.py` (~60 lines)

### Files to Modify
- `conacq/algorithms/quacq/__init__.py` — export QuAcqModelBuilder
- `conacq/algorithms/__init__.py` — export QuAcqModelBuilder
- `conacq/runners/quacq_runner.py` — rebuild model each run via builder (no model reuse)
- `tests/test_quacq.py` — update fixture to use builder

### QuAcqModel.from_bias() Removal
- Remove `from_bias()` — builder is the only entry point (matches ConGenModel pattern)
- QuAcqModel becomes internal; callers use QuAcqModelBuilder exclusively

### Runner Impact
- QuAcqRunner stores builder config (bias_path, oracle, use_incremental) instead of model
- `run()` calls `builder.build()` each invocation → fresh model + fresh task
- Eliminates `model.prepare()` re-call pattern

### Risks
- **Low risk**: Simple wrapper, no logic changes
- **Test coverage**: Existing tests cover model behavior; builder tests = construction verification

## Success Criteria
- QuAcqModelBuilder API mirrors ConGenModelBuilder (minus examples)
- All existing tests pass unchanged
- QuAcqRunner uses builder
- Exports available from `conacq.algorithms`

## Next Steps
1. Create `quacq_model_builder.py`
2. Update exports in `__init__.py` files
3. Update QuAcqRunner to use builder
4. Update test fixture
5. Add builder-specific tests
