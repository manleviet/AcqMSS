# Phase 4: Refactor GenerateNE

## Context Links
- [Plan overview](plan.md)
- [Phase 1: Slim Oracle](phase-01-slim-oracle-and-fm-data.md)
- [Phase 3: Refactor InteractiveLearner](phase-03-refactor-interactive-learner.md)
- GenerateNE: `acqmss/algorithms/generate_ne.py`
- ConGenTaskPreparation: `acqmss/algorithms/task_preparation.py`

## Overview
- **Priority**: P1
- **Status**: pending
- **Effort**: 1h

GenerateNE is tightly coupled to FeatureModelOracle internals (`get_c()`, `get_kb()`, `get_assumptions()`). Refactor to receive these as explicit parameters so GenerateNE has zero oracle dependency.

## Key Insights
- `GenerateNE.__init__` stores `self.oracle`
- `generate()` calls `self.oracle.get_c()` once for `set_bg`
- `_process_testcase()` calls `self.oracle.get_kb()` and `self.oracle.get_assumptions()` per testcase
- These methods delegate to `oracle._oracle_model.task.set_kb`, `.task.assumptions`, `.task.set_c`
- All three values are known at the call site (ConGenTaskPreparation) — can be passed in directly
- After refactoring, GenerateNE becomes a pure algorithm with no oracle import

## Requirements

### Functional
1. `GenerateNE.__init__()` takes no oracle parameter
2. `generate()` receives `oracle_kb`, `oracle_assumptions`, `oracle_set_c` as explicit params
3. No import of `FeatureModelOracle` in generate_ne.py
4. ConGenTaskPreparation extracts oracle KB/assumptions/set_c and passes to GenerateNE

### Non-functional
- GenerateNE becomes a pure function-like class (stateless except for algorithm logic)

## Architecture

### Before
```
GenerateNE(oracle: FeatureModelOracle)
├── generate(testsuite, variables, result_set_kb, result_assumptions, start_id)
│   └── set_bg = self.oracle.get_c()
└── _process_testcase(...)
    ├── set_kb = self.oracle.get_kb() + result_set_kb
    └── assumptions = self.oracle.get_assumptions() + result_assumptions
```

### After
```
GenerateNE()   # no oracle
├── generate(testsuite, variables, result_set_kb, result_assumptions, start_id,
│            oracle_kb, oracle_assumptions, oracle_set_c)
│   └── set_bg = oracle_set_c
└── _process_testcase(..., oracle_kb, oracle_assumptions, oracle_set_c)
    ├── set_kb = oracle_kb + result_set_kb
    └── assumptions = oracle_assumptions + result_assumptions
```

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/algorithms/generate_ne.py` | Remove oracle from `__init__`. Add `oracle_kb`, `oracle_assumptions`, `oracle_set_c` params to `generate()`. Remove FeatureModelOracle import. |
| `acqmss/algorithms/task_preparation.py` | Update `_prepare_negative_examples` to extract oracle data and pass to GenerateNE. Remove oracle param from GenerateNE constructor. |

## Implementation Steps

### 1. Update `generate_ne.py`

```python
class GenerateNE:
    """Generate negated negative examples using QuickXPlain."""

    def generate(
            self,
            testsuite: TestSuite,
            variables: Dict[str, int],
            result_set_kb: List[List[int]],
            result_assumptions: List[int],
            start_id: int,
            oracle_kb: List[List[int]],
            oracle_assumptions: List[int],
            oracle_set_c: List[int],
    ) -> Tuple[List[NEPerTestcase], int]:
        if not testsuite.testcases:
            return [], start_id

        results: List[NEPerTestcase] = []
        id_assumption = start_id

        for testcase in testsuite.testcases:
            ne, id_assumption = self._process_testcase(
                testcase, variables, result_set_kb, result_assumptions,
                oracle_kb, oracle_assumptions, oracle_set_c, id_assumption)
            results.append(ne)

        return results, id_assumption

    def _process_testcase(
            self,
            testcase: TestCase,
            variables: Dict[str, int],
            result_set_kb: List[List[int]],
            result_assumptions: List[int],
            oracle_kb: List[List[int]],
            oracle_assumptions: List[int],
            oracle_set_c: List[int],
            id_assumption: int
    ) -> Tuple[NEPerTestcase, int]:
        set_kb = oracle_kb + result_set_kb
        assumptions = oracle_assumptions + result_assumptions
        set_bg = oracle_set_c
        # ... rest unchanged
```

- Remove `__init__` entirely (or make it empty)
- Remove `TYPE_CHECKING` import of `FeatureModelOracle`

### 2. Update `_prepare_negative_examples` in task_preparation.py

```python
def _prepare_negative_examples(
        self,
        result: ConGenTask,
        provider: DescriptionProvider,
        model: ConGenModel,
        oracle: FeatureModelOracle,
        testsuite: TestSuite,
        id_assumption: int
) -> int:
    # Extract oracle data for GenerateNE
    oracle_kb = oracle.get_kb()
    oracle_assumptions = oracle.get_assumptions()
    oracle_set_c = oracle.get_c()

    generate_ne = GenerateNE()
    ne_results, id_assumption = generate_ne.generate(
        testsuite, model.variables, result.set_kb, result.assumptions,
        id_assumption, oracle_kb, oracle_assumptions, oracle_set_c)
    # ... rest unchanged
```

### 3. After Phase 4, remove oracle param from ConGenTaskPreparation

With GenerateNE decoupled, the only reason `ConGenTaskPreparation.prepare()` needs oracle is to extract KB/assumptions/set_c for GenerateNE. Move this extraction to `ConGenModel.prepare()` level:

**Option A (simple):** Keep oracle param in `_prepare_negative_examples` only. `ConGenTaskPreparation.prepare()` signature from Phase 3 remains `(model, fm_data, oracle)`.

**Option B (full decoupling):** Pass oracle KB/assumptions/set_c through ConGenModel or as additional params.

**Decision:** Option A — KISS. Oracle param stays for `_prepare_negative_examples` only. The prepare() method takes `(model, fm_data, oracle)` as established in Phase 3. Full decoupling is YAGNI.

## Todo List
- [ ] Remove `__init__(oracle)` from GenerateNE
- [ ] Add `oracle_kb`, `oracle_assumptions`, `oracle_set_c` params to `generate()`
- [ ] Pass through to `_process_testcase()`
- [ ] Remove `FeatureModelOracle` TYPE_CHECKING import from generate_ne.py
- [ ] Update `_prepare_negative_examples` to extract oracle data and pass to GenerateNE
- [ ] Verify GenerateNE has zero oracle dependency

## Success Criteria
- `generate_ne.py` has no import of oracle (neither runtime nor TYPE_CHECKING)
- GenerateNE constructor takes no parameters
- All oracle data passed explicitly to `generate()`
- ConGenTaskPreparation still works end-to-end

## Risk Assessment
- **Risk**: Many params in `generate()` signature (8 params)
- **Mitigation**: Group into a dataclass if it becomes unwieldy. For now, explicit params are clearer than hidden state. KISS.
- **Risk**: oracle.get_kb() returns mutable list; caller may modify
- **Mitigation**: GenerateNE creates new list via concatenation (`oracle_kb + result_set_kb`). No mutation risk.

## Next Steps
- Phase 5: Refactor OracleData to GroundTruthData
