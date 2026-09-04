# Phase 1: Slim Oracle ABC + Introduce FMData

## Context Links
- [Plan overview](plan.md)
- [Oracle usage mapping](research/researcher-01-oracle-usage.md)
- Current Oracle ABC: `acqmss/oracle/base.py`
- FeatureModelOracle: `acqmss/oracle/fm_oracle.py`

## Overview
- **Priority**: P1 (foundation for all subsequent phases)
- **Status**: complete
- **Effort**: 1.5h

Slim Oracle ABC to only `is_valid()` and `ask()`. Create `FMData` dataclass to hold FM metadata extracted from FeatureModelOracle. Add `get_fm_data()` convenience method on FeatureModelOracle.

## Key Insights
- Oracle ABC currently has 5 abstract methods; only `is_valid()` is a true membership query
- `UserPromptOracle` raises `NotImplementedError` for `complete_configuration()` and `get_cnf_clauses()` — proves they don't belong in ABC
- `CachedOracle` delegates all non-core methods — boilerplate reduction by removing them
- All callers that use FM metadata already know they have `FeatureModelOracle` (not generic `Oracle`)

## Requirements

### Functional
1. Oracle ABC contains only `is_valid()` and `ask()` (no abstract methods for metadata/SAT)
2. `FMData` dataclass holds: `features`, `feature_ids`, `root_feature`, `num_constraints`, `next_tseitin_var`
3. FeatureModelOracle exposes `get_fm_data() -> FMData`
4. `complete_configuration()` stays on FeatureModelOracle as concrete method (not in ABC)
5. `get_cnf_clauses()` **REMOVED entirely** from FeatureModelOracle (not needed — GroundTruthData reads FM directly)
<!-- Updated: Validation Session 1 - get_cnf_clauses() removed per user decision -->

### Non-functional
- No backward compatibility needed (break everything, fix everything)
- FMData is immutable (frozen dataclass)

## Architecture

```
Oracle (ABC)                    FMData (dataclass)
├── is_valid(assignments)       ├── features: Set[str]
└── ask(assignments)            ├── feature_ids: Dict[str, int]
                                ├── root_feature: str
FeatureModelOracle(Oracle)      ├── num_constraints: int
├── is_valid()                  ├── next_tseitin_var: int
├── complete_configuration()    └── feature_count: int (property)
├── get_cnf_clauses()
├── get_fm_data() -> FMData
├── get_root_feature()          # kept for internal use
├── get_constraint_descriptions()
└── cleanup()
```

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/oracle/base.py` | Remove `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`, `get_feature_count()` from ABC |
| `acqmss/oracle/fm_oracle.py` | Keep removed methods as concrete (non-override). Add `get_fm_data()`. Remove `get_feature_count()` (use `FMData.feature_count`) |
| `acqmss/oracle/user_prompt.py` | Remove `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()` methods entirely |
| `acqmss/oracle/cached.py` | Remove `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()` delegations |
| `acqmss/oracle/__init__.py` | Export `FMData` |

### Create
| File | Purpose |
|------|---------|
| `acqmss/oracle/fm_data.py` | FMData frozen dataclass |

## Implementation Steps

1. **Create `acqmss/oracle/fm_data.py`**
   ```python
   @dataclass(frozen=True)
   class FMData:
       features: Set[str]
       feature_ids: Dict[str, int]
       root_feature: str
       num_constraints: int
       next_tseitin_var: int

       @property
       def feature_count(self) -> int:
           return len(self.features)
   ```

2. **Slim `acqmss/oracle/base.py`**
   - Remove all abstract methods except `is_valid()`
   - Keep `ask()` as concrete alias
   - Remove `get_feature_count()`
   - Result: ~20 lines

3. **Update `acqmss/oracle/fm_oracle.py`**
   - `get_features()`, `get_feature_ids()` become regular methods (no `@abstractmethod` override)
   - `complete_configuration()`, `get_cnf_clauses()` become regular methods
   - Add `get_fm_data() -> FMData` that creates FMData from internal state
   - Remove `get_feature_count()` (moved to FMData property)

4. **Strip `acqmss/oracle/user_prompt.py`**
   - Remove `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`
   - Constructor still takes `features` list (needed for display), stored as instance attr but NOT part of Oracle ABC

5. **Strip `acqmss/oracle/cached.py`**
   - Remove delegation of `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`
   - Only delegates `is_valid()`

6. **Update `acqmss/oracle/__init__.py`**
   - Add `FMData` to imports and `__all__`

## Todo List
- [x] Create `fm_data.py` with FMData dataclass
- [x] Slim Oracle ABC in `base.py`
- [x] Add `get_fm_data()` to FeatureModelOracle
- [x] Strip UserPromptOracle
- [x] Strip CachedOracle
- [x] Update `__init__.py` exports
- [x] Verify imports resolve: `PYTHONPATH=. python -c "from acqmss.oracle import Oracle, FMData"`

## Success Criteria
- Oracle ABC has exactly 1 abstract method (`is_valid`)
- `FMData` dataclass created and exported
- `FeatureModelOracle.get_fm_data()` returns populated FMData
- UserPromptOracle and CachedOracle have no metadata/SAT methods
- No import errors

## Risk Assessment
- **Risk**: Downstream code breaks immediately (ExampleGenerator, InteractiveLearner, tests)
- **Mitigation**: Expected. Phases 2-7 fix all downstream. Run tests AFTER all phases complete.
- **Risk**: CachedOracle callers that used `complete_configuration()` via cache
- **Mitigation**: Callers must wrap FeatureModelOracle and call directly. Check all CachedOracle usage sites.

## Next Steps
- Phase 2: Refactor ExampleGenerator to receive FMData as param
- Phase 3: Refactor InteractiveLearner to use FMData
