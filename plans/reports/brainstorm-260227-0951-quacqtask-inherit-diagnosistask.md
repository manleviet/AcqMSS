# Brainstorm: QuAcqTask Inherits from DiagnosisTask

## Problem Statement

QuAcqTask duplicates 4 fields from DiagnosisTask (`set_kb`, `assumptions`, `negation_map`, `background`/`set_b`). Goal: full alignment with DiagnosisTask hierarchy (like ConGenTask → TestCaseTask → DiagnosisTask).

## Chosen Approach

**QuAcqTask(DiagnosisTask)** with full field alignment:
- Inherit: `set_c`, `set_b`, `set_kb`, `negation_map`, `assumptions`, `get_cf()`
- Remove from QuAcqTask: `set_kb`, `assumptions`, `negation_map` declarations (inherited)
- Remove `background` field → use `set_b` from parent
- Keep `bias: Set[int]` as QuAcq-specific (NOT mapped to `set_c`)
- `set_c` from parent: stays empty/unused by QuAcq algorithms

## Field Mapping After Refactor

| QuAcqTask (new) | Source | Notes |
|---|---|---|
| `set_c` | DiagnosisTask (inherited) | Empty, unused by QuAcq |
| `set_b` | DiagnosisTask (inherited) | Replaces `background` |
| `set_kb` | DiagnosisTask (inherited) | Same as before |
| `negation_map` | DiagnosisTask (inherited) | Same as before |
| `assumptions` | DiagnosisTask (inherited) | Same as before |
| `bias: Set[int]` | QuAcqTask own | Unchanged |
| `learned_kb` | QuAcqTask own | Unchanged |
| `background_clauses` | QuAcqTask own | Unchanged |
| `feature_ids` | QuAcqTask own | Unchanged |
| `id_to_feature` | QuAcqTask own | Unchanged |
| `constraint_clauses` | QuAcqTask own | Unchanged |
| `negated_clauses` | QuAcqTask own | Unchanged |
| `n_queries` | QuAcqTask own | Unchanged |
| `query_history` | QuAcqTask own | Unchanged |

## Rename: `background` → `set_b`

### Files to update

**Core:**
- `conacq/algorithms/interactive/quacq_task.py` — field declaration + `clone()`
- `conacq/algorithms/interactive/interactive_task_preparation.py` — `result.background` → `result.set_b`
- `conacq/algorithms/interactive/quacq.py` — `task.background` (2 refs)
- `conacq/algorithms/interactive/learner.py` — `self.task.background` (1 ref)
- `conacq/algorithms/interactive/_task_compat.py` — `task.background` (3 refs)
- `conacq/algorithms/interactive/task.py` — InteractiveTask.background field + clone() (deprecated, but keep consistent)
- `conacq/example_generators/query_generator.py` — `task.background` (1 ref)

**Tests:**
- `tests/test_interactive.py` — `task.background` / `learner.task.background` (7 refs)

## Dataclass Inheritance Notes

- DiagnosisTask is `@dataclass` with all default fields → child `@dataclass` works fine
- Constructor order: parent fields first (`set_c`, `set_b`, `set_kb`, `negation_map`, `assumptions`), then child fields
- `QuAcqTask()` with no args still works (all have defaults)
- `clone()` must include `set_b=` instead of `background=`, and NOT pass `set_c` (leave default empty)

## Risks

1. **`get_cf()` dead code** — returns `set_b + set_c`. Since `set_c` is empty, returns `set_b` only. Harmless but misleading. Could override to raise NotImplementedError if desired.
2. **`_task_compat.py` update** — `get_bg_clauses()` checks `task.background` → must change to `task.set_b`. Also InteractiveTask still uses `background` (deprecated).
3. **Type precision** — DiagnosisTask uses untyped `Dict` and `List`. QuAcqTask currently uses `Dict[int, int]`, `List[int]`. After inheritance, parent fields are untyped. Could add type stubs if needed.

## Success Criteria

- All tests pass
- `QuAcqTask` inherits from `DiagnosisTask`
- No `background` field on QuAcqTask (uses `set_b`)
- No duplicate `set_kb`, `assumptions`, `negation_map` fields
- `bias` remains `Set[int]`, independent of `set_c`
- `prepare_kb()` still works (writes to inherited fields)
