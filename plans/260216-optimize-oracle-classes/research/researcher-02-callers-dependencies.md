# Research: Oracle Module Callers & Dependencies

**Date:** 2025-02-16
**Scope:** Map all callers and dependencies of FeatureModelOracle, FMOracleModel, OracleTaskPreparation

---

## Executive Summary

- **FMOracleModel**: Core model, satisfies CheckerModel protocol, instantiated via 3 factory patterns
- **FeatureModelOracle**: Thin wrapper, only instantiated in 1 location (generate_examples.py)
- **OracleTaskPreparation**: Static utility, only called via FMOracleModel.prepare()
- **Public API surface**: 8 essential methods, 3 convenience getters that delegate to task
- **Tight coupling**: CheckerFactory.create_from_model() hardcoded to call get_kb() + get_assumptions()

---

## 1. FMOracleModel Callers (9 locations)

### Direct Instantiation (3 factory patterns)
1. **from_fm_data()** → `test_oracle_model.py:57, 69` (2 calls)
2. **from_fm().build()** → `fm_oracle.py:52`, `test_oracle_model.py` (builder chain)
3. **ConGenModelBuilder** → `congen_model_builder.py` (returns FMOracleModel instance)

### CheckerFactory Usage (6 locations)
After instantiation, all pass model to `CheckerFactory.create_from_model()`:
- `test_congen.py:64` (test)
- `test_oracle_model.py:58, 70` (tests)
- `test_oracle_model.py:104, 111` (OneShotModel, not FMOracleModel)
- `run_congen.py:121` (main app)
- `congen_runner.py:166` (eval framework)

---

## 2. FeatureModelOracle Callers (1 location)

| Caller | Usage |
|--------|-------|
| `apps/generate_examples.py` | **Only instantiation** in entire codebase |
| | Uses `.ask()` method (inherited from Oracle ABC) |
| | Example: `oracle.ask({"f1": True, "f2": False})` |

**Implication**: FeatureModelOracle is isolated; changes safe if ABC contract preserved.

---

## 3. OracleTaskPreparation Callers (1 location)

| Caller | Usage |
|--------|-------|
| `FMOracleModel.prepare()` | **Only internal caller** |
| | Static method: `OracleTaskPreparation.prepare(self)` |
| | Returns PreparationOutput (task + provider) |

**Implication**: Complete encapsulation; can refactor freely or inline without external impact.

---

## 4. Public API Surface (8 essential methods)

### Core Protocol Methods (CheckerModel)
```python
use_incremental: bool                    # Property, checked by CheckerFactory
get_kb() -> List[List[int]]             # Required by factory
get_assumptions() -> List[int]          # Required by factory
```

### Build/Prepare Methods
```python
prepare() -> DiagnosisTask              # Called internally by factory patterns
build() -> FMOracleModel               # Builder chain (fm_oracle.py:52)
with_configuration(config) -> List     # Set active assumptions from feature config
set_incremental(bool) -> FMOracleModel # Builder pattern setter
```

### Task Access
```python
task: DiagnosisTask                    # Property (lazy), accessed 2+ times per test
description_provider: DescriptionProvider  # Property (lazy), for constraint descriptions
```

### Convenience Getters (delegate to task, unused?)
```python
get_c() -> List                        # Returns task.set_c (NOT called externally)
get_raw_fm_clauses() -> List           # Returns FM clauses (NOT called externally)
```

---

## 5. CheckerModel Protocol Compliance

| Required | FMOracleModel | OneShotModel |
|----------|---------------|--------------|
| `use_incremental` | ✓ (settable) | ✓ (hardcoded False) |
| `get_kb()` | ✓ | ✓ |
| `get_assumptions()` | ✓ | ✓ |

**Status**: Both fully compliant. CheckerFactory uses only these 3 members.

---

## 6. Backward Compatibility Risk Analysis

### High Risk (breaking changes likely cascade)
- **get_kb() signature** — called by CheckerFactory
- **get_assumptions() signature** — called by CheckerFactory
- **prepare() side effects** — populates internal state (_task, _description_provider)
- **use_incremental property** — read by CheckerFactory

### Medium Risk (affects convenience API)
- **task property** — accessed in tests/eval code for intermediate data
- **with_configuration()** — used in test_oracle_model.py

### Low Risk (unused or internal)
- **get_c(), get_raw_fm_clauses()** — never called externally
- **description_provider property** — never accessed externally
- **OracleTaskPreparation class** — fully internal to prepare()

---

## 7. Tight Coupling Points

### CheckerFactory hardcoded expectations
```python
# checker.py:233-245
def create_from_model(model: CheckerModel, ...):
    if model.use_incremental:
        return IncrementalPySATChecker(
            model.get_kb(), model.get_assumptions(),  # Direct calls
            solver_name, profiler_instance
        )
```

**Impact**: Any protocol member changes break factory.

### Builder chain dependency
```python
# fm_oracle.py:52
self._oracle_model = FMOracleModel.from_fm(fm_path).set_incremental(...).build()
self._checker = CheckerFactory.create_from_model(self._oracle_model, ...)
```

**Impact**: from_fm().build() must return prepared instance for factory to work.

---

## 8. Unused Methods (Optimization Opportunity)

- `get_c()` — never called; delegates to task.set_c
- `get_raw_fm_clauses()` — never called; returns FM clauses from constraint_map
- `start_id_assignments property` — accessed only in OracleTaskPreparation.prepare()

**Recommendation**: Mark as internal (`_get_c()`) or remove after 1 release.

---

## 9. Key Dependencies Summary

```
FMOracleModel
├── CheckerFactory.create_from_model()  [HARD DEPENDENCY]
├── DiagnosisTask (internal, populated by prepare())
├── DescriptionProvider (internal)
└── OracleTaskPreparation.prepare() (static, internal)

FeatureModelOracle
└── Oracle ABC.is_valid(), ask()  [HARD DEPENDENCY]

CheckerModel Protocol
├── use_incremental (bool property)
├── get_kb() -> List[List[int]]
└── get_assumptions() -> List[int]
```

---

## Unresolved Questions

1. Why are `get_c()` and `get_raw_fm_clauses()` public if never used?
2. Should `with_configuration()` update internal `set_c` in-place or return fresh list?
3. Is `description_provider` intentionally unused in public API?
