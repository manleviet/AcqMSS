# Phase 2: Refactor ConGenModel

## Context Links
- [plan.md](./plan.md)
- [phase-01-update-oracle-api.md](./phase-01-update-oracle-api.md)
- [congen_model.py](../../conacq/algorithms/congen_model.py)
- [task_preparation.py](../../conacq/algorithms/task_preparation.py)

## Overview
- **Date**: 2026-02-16
- **Description**: Remove FM-derived fields from `ConGenModel`, change `prepare()` to accept oracle parameter, update `ConGenTaskPreparation` to extract FM metadata from oracle.
- **Priority**: P2
- **Implementation Status**: Pending
- **Review Status**: Pending

## Key Insights
- `ConGenModel` currently stores `_oracle`, `_fm_path`, `num_fm_constraints`, `root_feature` -- all FM concerns
- Oracle is only used in `ConGenTaskPreparation._prepare_negative_examples()` via `model.oracle`
- `num_fm_constraints` used once: ID reservation in `ConGenTaskPreparation.prepare()` (line 118)
- `root_feature` used once: `_prepare_bg()` in `ConGenTaskPreparation.prepare()` (line 115)
- `next_tseitin_var` serves dual purpose: (1) initial value from FM model, (2) updated during task prep. Keep on model but init from oracle.
- `model.oracle` property accessed in `task_preparation.py` line 166 -- change to local param

## Requirements

### Functional
- `ConGenModel.prepare(oracle, pos_examples, neg_examples)` -- oracle as explicit param
- Remove `_oracle`, `_fm_path`, `num_fm_constraints`, `root_feature` from `ConGenModel.__init__`
- Remove `oracle` property from `ConGenModel`
- `ConGenTaskPreparation.prepare(model, oracle)` -- oracle passed through
- `_prepare_bg()` takes `root_feature` and `num_fm_constraints` as params (from oracle)

### Non-Functional
- `ConGenModel` becomes FM-agnostic (pure bias + solver config container)
- No circular imports

## Architecture

### Before
```
ConGenModel
  ├── _oracle: FeatureModelOracle       # FM concern
  ├── _fm_path: str                     # FM concern
  ├── num_fm_constraints: int           # FM concern
  ├── root_feature: str                 # FM concern
  ├── constraint_map                    # bias (keep)
  ├── variables                         # bias (keep)
  ├── next_tseitin_var                  # keep (init from oracle at prepare)
  └── prepare(pos, neg)                 # creates task
```

### After
```
ConGenModel
  ├── constraint_map                    # bias (keep)
  ├── negated_constraint_map            # bias (keep)
  ├── variables                         # bias (keep)
  ├── next_tseitin_var                  # keep (init from oracle at prepare)
  ├── _use_incremental                  # solver config (keep)
  └── prepare(oracle, pos, neg)         # oracle injected
```

## Related Code Files

### Files to Modify
| File | Change |
|------|--------|
| `acqmss/algorithms/congen_model.py` | Remove FM fields, update `prepare()` signature |
| `acqmss/algorithms/task_preparation.py` | `prepare()` and `_prepare_negative_examples()` accept oracle param; `_prepare_bg()` accepts root_feature/num_fm_constraints as params |

### Files Unchanged (modified in later phases)
| File | Phase |
|------|-------|
| `congen_model_builder.py` | Phase 3 |
| `congen_runner.py` | Phase 4 |

## Implementation Steps

### Step 1: Update `ConGenModel` (`congen_model.py`)

1. **Remove FM fields from `__init__`**:
   - Delete: `self._fm_path`, `self._oracle`, `self.num_fm_constraints`, `self.root_feature`
   - Keep: `self.constraint_map`, `self.negated_constraint_map`, `self.variables`, `self.next_tseitin_var`, `self._use_incremental`, `self._task_input`, `self._task`, `self._description_provider`

2. **Remove `oracle` property** (lines 59-61)

3. **Remove `FeatureModelOracle` import** (line 17: `from ..oracle import FeatureModelOracle`)

4. **Update `prepare()` signature**:
   ```python
   def prepare(
           self,
           oracle: FeatureModelOracle,
           positive_examples: Optional[List[Dict[str, bool]]] = None,
           negative_examples: Optional[List[Dict[str, bool]]] = None
   ) -> ConGenTask:
   ```
   - Use TYPE_CHECKING import for `FeatureModelOracle` to avoid circular deps
   - Pass oracle to `ConGenTaskPreparation`

5. **Update `prepare()` body**:
   ```python
   # Initialize next_tseitin_var from oracle on first prepare
   # (subsequent calls reuse model's updated value from prior runs)
   if self.next_tseitin_var == 1000:  # default sentinel
       self.next_tseitin_var = oracle.get_next_tseitin_var()

   from .task_preparation import ConGenTaskPreparation
   preparation = ConGenTaskPreparation()
   output = preparation.prepare(self, oracle)
   ```

   Actually, simpler approach: always set from oracle since each prepare() creates fresh task:
   ```python
   self.next_tseitin_var = oracle.get_next_tseitin_var()

   from .task_preparation import ConGenTaskPreparation
   preparation = ConGenTaskPreparation()
   output = preparation.prepare(self, oracle)
   ```

### Step 2: Update `ConGenTaskPreparation` (`task_preparation.py`)

1. **Update `prepare()` signature**:
   ```python
   def prepare(self, model: ConGenModel, oracle: FeatureModelOracle) -> PreparationOutput:
   ```

2. **Extract FM metadata from oracle inside `prepare()`**:
   ```python
   root_feature = oracle.get_root_feature()
   num_fm_constraints = oracle.get_num_constraints()
   ```

3. **Update `_prepare_bg()` call** (line 115):
   ```python
   # Before:
   id_assumption = _prepare_bg(result, provider, model.variables, model.root_feature, id_assumption)
   # After:
   id_assumption = _prepare_bg(result, provider, model.variables, root_feature, id_assumption)
   ```

4. **Update ID reservation** (line 118):
   ```python
   # Before:
   id_assumption = id_assumption + (model.num_fm_constraints - 1) * _ASSUMPTION_PAIR_STRIDE
   # After:
   id_assumption = id_assumption + (num_fm_constraints - 1) * _ASSUMPTION_PAIR_STRIDE
   ```

5. **Update `_prepare_negative_examples()` signature**:
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
   ```

6. **Update `_prepare_negative_examples()` body** (line 166-167):
   ```python
   # Before:
   oracle = model.oracle
   if oracle is None:
       raise ValueError(...)
   # After:
   # oracle passed as parameter -- validation handled by caller
   ```

7. **Update call to `_prepare_negative_examples()`** in `prepare()`:
   ```python
   id_assumption = self._prepare_negative_examples(
       result, provider, model, oracle, testsuite, id_assumption)
   ```

8. **Add TYPE_CHECKING import** for `FeatureModelOracle`:
   ```python
   if TYPE_CHECKING:
       from ..oracle import FeatureModelOracle
   ```

### Step 3: Verify
```bash
PYTHONPATH=. pytest tests/test_congen.py -v
```
Note: Tests will fail until Phase 3-4 update builder and callers to pass oracle.

## Todo List
- [ ] Remove `_oracle`, `_fm_path`, `num_fm_constraints`, `root_feature` from `ConGenModel.__init__`
- [ ] Remove `oracle` property from `ConGenModel`
- [ ] Update `prepare()` to accept `oracle` parameter
- [ ] Set `next_tseitin_var` from oracle in `prepare()`
- [ ] Update `ConGenTaskPreparation.prepare()` to accept oracle
- [ ] Extract `root_feature` and `num_fm_constraints` from oracle in `prepare()`
- [ ] Update `_prepare_negative_examples()` to accept oracle param
- [ ] Remove direct `model.oracle` access in task_preparation
- [ ] Add TYPE_CHECKING imports

## Success Criteria
- `ConGenModel.__init__` has no FM-related fields
- `prepare()` requires explicit oracle parameter
- `ConGenTaskPreparation` gets all FM metadata from oracle parameter
- No `model.oracle`, `model._fm_path`, `model.num_fm_constraints`, `model.root_feature` references in algorithms/

## Risk Assessment
- **Medium**: All callers of `prepare()` must be updated simultaneously (Phase 3-4). Can do Phase 2-4 as atomic commit.
- **Low**: `_prepare_bg()` signature change is internal only

## Security Considerations
- None -- internal refactoring

## Next Steps
- Phase 3: Update builder to stop setting FM fields, stop creating oracle
- Phase 4: Update runner/tests to create oracle and pass to `prepare()`
