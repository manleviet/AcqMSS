# Phase A2 — Abstract Model Builder: Implementation Report

## Base Location & Signature

**Created:** `explanation/models/abstract_model_builder.py`
**Re-exported from:** `explanation/models/__init__.py` (added to `__all__`)

```python
class AbstractModelBuilder(ABC):
    def __init__(self) -> None:
        self._bias_path: Optional[str] = None
        self._oracle: Optional['FeatureModelOracle'] = None
        self._create_negation: bool = False

    # Fluent source/option methods
    @classmethod
    def from_bias(cls, bias_path: str) -> 'AbstractModelBuilder': ...
    def with_oracle(self, oracle) -> 'AbstractModelBuilder': ...
    def with_negation(self, enabled: bool = True) -> 'AbstractModelBuilder': ...

    # Concrete build() — used by ConGen/QuAcq; DiagnosisModelBuilder overrides entirely
    def build(self) -> Any: ...  # validate → load bias → _create_model_instance()
                                 # → set constraint_map/variables → negation loop
                                 # → _post_negation_build(model) → return model

    # Template hooks (override in ConGen/QuAcq)
    def _create_model_instance(self) -> Any: ...  # raises NotImplementedError by default
    def _post_negation_build(self, model: Any) -> None: ...  # no-op by default

    # Shared validator
    def _validate(self) -> None: ...  # raises ValueError if _bias_path or _oracle is None
```

## Before → After for Each Builder

### `explanation/models/diagnosis_model_builder.py`

**Before:**
- `__init__` declared its own `self._create_negation: bool = False`
- `with_negation()` was a standalone method setting `self._create_negation`
- `for_redundancy = with_negation` aliased the local method

**After:**
- Inherits `AbstractModelBuilder`; `super().__init__()` provides `_create_negation`, `_bias_path`, `_oracle`
- `with_negation()` removed — inherited from base
- `for_redundancy = AbstractModelBuilder.with_negation` (alias to base method, same semantic)
- `build()` fully overrides base (different source pattern: fide/uvl/dimacs/feature_model, no oracle required)
- `_create_model_instance` / `_post_negation_build` not implemented (not needed; `build()` is overridden)

**Deleted from this file:** own `_create_negation` init + own `with_negation()` method body.

### `conacq/algorithms/acqmss/congen_model_builder.py`

**Before (lines 108–122 verbatim block):**
```python
from conacq.bias import BiasIO
from explanation.operations.algorithms.utils import negate_cnf_tseitin

bias = BiasIO.load_from_json(self._bias_path)
model = ConGenModel()
model.constraint_map = bias.to_constraint_map()
model.variables = bias.feature_ids

next_tseitin_var = self._oracle.get_bg_data().next_available_id
for key, c in model.constraint_map.items():
    neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
    model.negated_constraint_map[f"NOT({key})"] = neg_clauses
model.next_available_id = next_tseitin_var
```

Also had: own `from_bias()` classmethod, own `with_oracle()` method, own `_validate()` method.

**After:**
- Inherits `AbstractModelBuilder`
- `from_bias()`, `with_oracle()`, `_validate()` deleted — inherited from base
- `_bias_path`, `_oracle`, `_create_negation` deleted from `__init__` — from base
- Entire verbatim block deleted from `build()`
- `build()` method deleted — inherited from base
- Added: `_create_model_instance()` → `return ConGenModel()`
- Added: `_post_negation_build(model)` → sets `self.last_task = None`, auto-prepares if examples present
- `last_task`, `_has_examples`, `_resolve_examples`, `_make_task_input`, `with_examples`, `with_examples_data`, `get_examples` kept as-is (ConGen-specific)

### `conacq/algorithms/quacq/quacq_model_builder.py`

**Before (lines 57–71 verbatim block, identical to ConGen):**
```python
from conacq.bias import BiasIO
from explanation.operations.algorithms.utils import negate_cnf_tseitin

bias = BiasIO.load_from_json(self._bias_path)
model = QuAcqModel()
model.constraint_map = bias.to_constraint_map()
model.variables = bias.feature_ids

next_tseitin_var = self._oracle.get_bg_data().next_available_id
for key, c in model.constraint_map.items():
    neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
    model.negated_constraint_map[f"NOT({key})"] = neg_clauses
model.next_available_id = next_tseitin_var
```

Also had: own `from_bias()`, own `with_oracle()`, own `_validate()`.

**After:**
- Inherits `AbstractModelBuilder`
- All of the above deleted — inherited
- Added: `_create_model_instance()` → `return QuAcqModel()`
- Added: `_post_negation_build(model)` → `self.last_task = model.prepare_task(self._oracle)`
- `last_task` kept on the subclass (B4 scope)
- File reduced from 82 lines to 48 lines

## `last_task` Behavior — Confirmed Untouched

- `last_task` is declared only on `ConGenModelBuilder.__init__` and `QuAcqModelBuilder.__init__`, not on `AbstractModelBuilder`.
- The setting logic is in `_post_negation_build()` on each concrete builder, matching the original `build()` behavior exactly:
  - ConGen: `last_task = None` then set only if examples present → identical to before
  - QuAcq: `last_task = model.prepare_task(self._oracle)` → always set → identical to before
- Tests `test_auto_prepare_from_file`, `test_auto_prepare_from_data`, and all QuAcq `builder.last_task` accesses pass unchanged.

## Test Results

```
376 passed, 1 warning in 62.02s
```

Identical to pre-refactor baseline. No test rewrites needed.

## Files Modified

| File | Change |
|------|--------|
| `explanation/models/abstract_model_builder.py` | Created (new base, 128 lines) |
| `explanation/models/__init__.py` | Added `AbstractModelBuilder` import + `__all__` entry |
| `explanation/models/diagnosis_model_builder.py` | Inherit base; remove own `_create_negation` + `with_negation()` |
| `conacq/algorithms/acqmss/congen_model_builder.py` | Inherit base; remove verbatim 15-line block + `from_bias`/`with_oracle`/`_validate` |
| `conacq/algorithms/quacq/quacq_model_builder.py` | Inherit base; remove verbatim 15-line block + `from_bias`/`with_oracle`/`_validate`; file −34 lines |

## Deviations from Spec

None. All red-team requirements applied:
- Base at `explanation/models/abstract_model_builder.py` (hard requirement satisfied)
- Re-exported from `explanation/models/__init__.py` in this stage
- `last_task` untouched (B4 scope)
- No private module hiding
- No `conacq`→`explanation` underscore import

**Status:** DONE
**Summary:** `AbstractModelBuilder` extracted to `explanation/models/`; all 3 builders inherit it; verbatim bias+negation block (15 lines, duplicated in ConGen+QuAcq) collapsed into base `build()`; `with_negation` unified; `last_task` contract preserved on concrete subclasses; 376/376 tests pass.
**Concerns:** None.
