# Code Explorer: Oracle BG Refactoring Analysis

## Files Requiring Changes

| File | Change | Scope |
|------|--------|-------|
| `conacq/oracle/bg_data.py` | CREATE | BGData frozen dataclass |
| `conacq/oracle/fm_oracle_model.py` | MODIFY | BGData extraction in OracleTaskPreparation.prepare() + FMOracleModel property |
| `conacq/oracle/fm_oracle.py` | MODIFY | Add get_bg_data() method |
| `conacq/oracle/__init__.py` | MODIFY | Export BGData |
| `conacq/algorithms/acqmss/task_preparation.py` | MODIFY | Delete _prepare_bg, remove FMData param, replace skip arithmetic |
| `conacq/algorithms/acqmss/congen_model.py` | MODIFY | Remove fm_data usage, update prepare() call |
| `explanation/models/task_preparation.py` | MODIFY | Add get_descriptions_for() to DescriptionProvider |

## Files NOT Requiring Changes
- `conacq/oracle/fm_data.py` — FMData stays (InteractiveLearner uses it)
- `conacq/runners/congen_runner.py` — calls model.prepare(oracle=...) which is unchanged
- `conacq/algorithms/interactive/learner.py` — FMData usage is orthogonal
- `tests/test_congen.py` — test API unchanged
- `tests/test_oracle_model.py` — assertion counts unchanged

## Signature Changes
| Location | Before | After |
|----------|--------|-------|
| task_preparation.py:107 | `prepare(self, model, fm_data, oracle)` | `prepare(self, model, oracle)` |
| congen_model.py:203 | `preparation.prepare(self, fm_data, oracle)` | `preparation.prepare(self, oracle)` |

## Dead Code After Refactor
- `congen_model.py:187-188`: `fm_data = oracle.get_fm_data()` / `self.next_tseitin_var = fm_data.next_tseitin_var` — remove
- `task_preparation.py:52-84`: `_prepare_bg()` — delete entirely

## Risks
1. Root must be first in constraint_map — add assertion
2. DescriptionProvider may lack bulk-read — add get_descriptions_for()
3. model.next_tseitin_var becomes unused in ConGenModel.prepare() path — clean up
