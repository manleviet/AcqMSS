# Phase 02: Add Tests & Verify

## Context

- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-modify-builder.md)
- Target file: `tests/test_congen.py`

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Add tests for all 3 API patterns, verify existing tests still pass

## Key Insights

- Existing `create_checker_and_task()` helper uses manual prepare pattern → keep unchanged for backward compat tests
- New tests should cover: auto-prepare from file, auto-prepare from raw data, CV re-prepare
- Use same test data (REAL-FM-7) already used by existing tests

## Requirements

### Functional
1. Test Pattern 1: auto-prepare from file path → model is prepared after `build()`
2. Test Pattern 2: auto-prepare from raw data → model is prepared after `build()`
3. Test Pattern 3: CV build-once-prepare-per-fold → model prepared after each `prepare()` call
4. Test edge case: build without oracle → unprepared model
5. Test last-call-wins: `with_examples()` then `with_examples_data()` uses raw data

## Related Code Files

### Modify
- `tests/test_congen.py` — Add new test class `TestConGenModelBuilder`

### Reference
- `conacq/algorithms/acqmss/congen_model_builder.py` — builder under test
- `conacq/oracle/fm_oracle.py` — FeatureModelOracle
- `conacq/examples/io_utils.py` — ExampleIO

## Implementation Steps

### 1. Add `TestConGenModelBuilder` class

New test class in `tests/test_congen.py` with tests:

```python
class TestConGenModelBuilder:
    """Tests for ConGenModelBuilder auto-prepare patterns."""

    def test_auto_prepare_from_file(self):
        """Pattern 1: with_oracle + with_examples → build returns prepared model."""
        oracle = FeatureModelOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle(oracle)
                 .with_examples(str(EXAMPLES_FF_PATH))
                 .build())
        assert model.task is not None
        assert len(model.get_kb()) > 0

    def test_auto_prepare_from_data(self):
        """Pattern 2: with_oracle + with_examples_data → build returns prepared model."""
        # Load examples manually
        examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        oracle = FeatureModelOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle(oracle)
                 .with_examples_data(positive_examples=pos, negative_examples=neg)
                 .build())
        assert model.task is not None

    def test_build_without_oracle_returns_unprepared(self):
        """build() without oracle → unprepared model."""
        model = ConGenModelBuilder.from_bias(str(BIAS_PATH)).build()
        assert model.task is None

    def test_cv_re_prepare(self):
        """Pattern 3: build once, prepare per fold."""
        model = ConGenModelBuilder.from_bias(str(BIAS_PATH)).build()
        oracle = FeatureModelOracle(str(FM_PATH), use_incremental=False)
        examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        # First prepare
        model.prepare(oracle, positive_examples=pos, negative_examples=neg)
        task1_kb = list(model.get_kb())

        # Re-prepare (idempotent)
        model.prepare(oracle, positive_examples=pos, negative_examples=neg)
        task2_kb = list(model.get_kb())

        assert task1_kb == task2_kb

    def test_last_call_wins(self):
        """with_examples then with_examples_data → raw data used."""
        examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        oracle = FeatureModelOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle(oracle)
                 .with_examples('nonexistent.json')  # Would fail if used
                 .with_examples_data(positive_examples=pos, negative_examples=neg)
                 .build())
        assert model.task is not None  # Used raw data, not file
```

### 2. Run full test suite

```bash
PYTHONPATH=. pytest tests/test_congen.py -v
```

### 3. Run all tests for regression

```bash
PYTHONPATH=. pytest tests/ -v
```

## Todo List

- [x] Add `TestConGenModelBuilder` class with 5 tests
- [x] Run `test_congen.py` — all pass
- [x] Run full test suite — no regressions (307/309; 2 pre-existing failures in test_evaluation.py unrelated)

## Success Criteria

- All new tests pass
- All existing tests pass unchanged
- No regressions in other test files
