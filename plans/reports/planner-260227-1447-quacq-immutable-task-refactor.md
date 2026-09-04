# Planner Report: Refactor QuAcqTask to Immutable-Task Pattern

**Date**: 2026-02-27
**Plan**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260227-1447-quacq-immutable-task-refactor/`

## Summary

Created 3-phase plan to refactor QuAcqTask from mutable to immutable-task pattern, matching ConGenTask/DiagnosisTask conventions.

## Problem

QuAcqTask holds 4 mutable fields (`bias`, `learned_kb`, `n_queries`, `query_history`) plus 3 mutation methods (`add_to_kb`, `remove_from_bias`, `record_query`). The QuAcq algorithm mutates these during learning. This violates the project pattern where tasks are immutable inputs and algorithms produce separate result objects.

## Approach

- **Phase 1** (45m): Remove mutable fields/methods from QuAcqTask. Use inherited `set_c` (from DiagnosisTask) for bias IDs — exactly matching ConGenTask.
- **Phase 2** (45m): Move mutable state into QuAcq.learn()/learn_from_examples() as local variables. Thread `remaining_bias` (set) and `record_query` (callback) through FindScope/FindC/QueryGenerator.
- **Phase 3** (30m): Update QuAcqRunner shuffle, update 15+ test assertions, run full suite.

## Key Design Decision

`remaining_bias` is a mutable `set` passed by reference to FindScope/FindC — they mutate it for pruning (same semantics as before, just not via task). `record_query` is a closure callback that FindC calls for discriminating queries. This keeps the threading minimal while preserving exact behavior.

## Files Impacted (8 source + 1 test)

| File | Change Type |
|------|-------------|
| `conacq/algorithms/quacq/task_preparation.py` | Remove fields/methods, use set_c |
| `conacq/algorithms/quacq/quacq.py` | Local state, updated signatures |
| `conacq/algorithms/quacq/findscope.py` | Add remaining_bias param |
| `conacq/algorithms/quacq/findc.py` | Add remaining_bias + record_query |
| `conacq/example_generators/query_generator.py` | Add remaining_bias + learned_kb params |
| `conacq/runners/quacq_runner.py` | Shuffle task.set_c instead of task.bias |
| `tests/test_quacq.py` | Delete 4 tests, update 11+ assertions |
| `conacq/eval/cross_validation.py` | No changes (uses runner, not task) |
| `conacq/eval/progressive_evaluation.py` | No changes (uses QuAcqRunResult) |

## Unresolved Questions

1. **Should `task.set_c` be frozen after preparation?** Currently `List[int]` is mutable; QuAcqRunner shuffles it in place. True immutability would require copying before shuffle. Not blocking — consider for future.
