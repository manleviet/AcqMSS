# Phase 05: Run Tests and Verify

## Context Links

- Test file: `tests/test_congen.py`
- All tests: `tests/`
- Run command: `PYTHONPATH=. pytest tests/ -v`

## Overview

- **Priority**: P1
- **Status**: completed
- **Description**: Run full test suite to verify refactoring produces identical behavior. Validate CheckerModel protocol conformance.

## Key Insights

- test_congen.py has 3 ConGen tests (inc RS, non-inc RS, inc FF) + unit tests for AcqMSS, Reduce, GenerateNE, OracleFeatureIds
- test_diagnosis.py tests diagnosis infrastructure (should be unaffected)
- test_evaluation.py tests cross-validation (uses ConGenRunner internally)
- Must verify both incremental and non-incremental paths

## Implementation Steps

### Step 1: Verify CheckerModel protocol

Add a quick assertion in test or verify manually:

```python
from explanation.operations.algorithms.checker import CheckerModel
model = ConGenModel.from_bias_and_examples(...)
model.use_incremental = True
model.prepare()
assert isinstance(model, CheckerModel), "ConGenModel must satisfy CheckerModel protocol"
```

### Step 2: Run ConGen tests

```bash
PYTHONPATH=. pytest tests/test_congen.py -v
```

Expected: all 3 ConGen tests pass with identical KB results.

### Step 3: Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

Expected: no regressions in diagnosis, interactive, evaluation, profiler tests.

### Step 4: Run ConGen app end-to-end

```bash
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v --non-incremental
```

Expected: same output files and constraint counts as before.

### Step 5: Lint check

```bash
ruff check acqmss/algorithms/congen_model.py acqmss/algorithms/congen_model_builder.py acqmss/algorithms/congen_root.py acqmss/algorithms/__init__.py
ruff check acqmss/eval/congen_runner.py apps/run_congen.py tests/test_congen.py
```

## Todo List

- [ ] Verify CheckerModel protocol conformance
- [ ] Run test_congen.py — all pass
- [ ] Run full test suite — no regressions
- [ ] Run run_congen.py incremental — same results
- [ ] Run run_congen.py non-incremental — same results
- [ ] Lint check — no errors

## Success Criteria

- All existing tests pass without modification (beyond Phase 04 changes)
- ConGen output (KB constraints, counts) identical pre/post refactor
- No new lint warnings
- CheckerFactory.create_from_model(congen_model) works in all callers

## Risk Assessment

- **Risk**: Flaky test due to solver non-determinism
  - **Mitigation**: Compare constraint sets (order-independent), not ordered lists
- **Risk**: Memory leak from temp checker in prepare()
  - **Mitigation**: NonIncrementalPySATChecker has no persistent state; verify with tracemalloc in congen_runner

## Security Considerations

- No security impact

## Next Steps

- After all tests pass: update `docs/codebase-summary.md` and `docs/system-architecture.md` to reflect new builder pattern and prepare() changes
- Mark plan as completed
