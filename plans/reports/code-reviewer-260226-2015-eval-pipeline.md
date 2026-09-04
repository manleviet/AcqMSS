# Code Review: QuAcq -> ConGen Evaluation Pipeline

**Date:** 2026-02-26
**Reviewer:** code-reviewer
**Scope:** New evaluation pipeline + source-tagging infrastructure

---

## Code Review Summary

### Scope
- **New files (7):** `query_converter.py`, `semantic_equivalence.py`, `progressive_evaluation.py`, `run_evaluation.py`, `run_evaluation_config.toml`, `test_query_converter.py`, `test_semantic_equivalence.py`
- **Modified files (11):** `quacq_task.py`, `task.py`, `result.py`, `findc.py`, `findscope.py`, `learner.py`, `quacq.py`, `interactive_runner.py`, `query_generator.py`, `kb_comparator.py`, `eval/__init__.py`, `examples/__init__.py`, `test_interactive.py`
- **LOC:** ~1,122 added, ~430 removed (net +692)
- **Focus:** New evaluation pipeline, source tagging, dual-task compatibility

### Overall Assessment

**Good implementation.** The pipeline architecture is well-structured with clear separation: source tagging at query level, format conversion, SAT-based semantic equivalence, and progressive evaluation. Backward compatibility is maintained throughout via the `_task_compat.py` duck-typing layer.

A few correctness, type safety, and edge case issues require attention.

---

## Critical Issues

### C1. Type annotation mismatch in `SemanticEquivalenceChecker.__init__`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/semantic_equivalence.py` line 59

```python
bg_clauses: List[List[int]] = None,
```

Annotation says `List[List[int]]` but default is `None`. This will cause mypy/pyright errors. `Optional` is not imported.

**Fix:**
```python
from typing import List, Optional, Tuple

# ...
bg_clauses: Optional[List[List[int]]] = None,
```

### C2. BG clauses asymmetry in `check_ct_entails_kb`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/semantic_equivalence.py` lines 89-96

```python
def check_kb_entails_ct(self):
    source = self.kb_clauses + self.bg_clauses  # BG included
    return self._check_entails(source, self.ct_clauses)

def check_ct_entails_kb(self):
    return self._check_entails(self.ct_clauses, self.kb_clauses)  # BG excluded
```

Design decision says "BG clauses included in source only (not entailment targets)." This is **correct** for KB->CT direction: the learned KB + BG together should entail C_T.

However, for CT->KB: checking `self.ct_clauses entails self.kb_clauses` without BG on either side means if the KB learned a constraint that is only valid given BG, C_T would fail to entail it. This could cause **false negatives** in the `ct_entails_kb` direction -- i.e., reporting unentailed KB clauses that are actually entailed under BG.

**Recommendation:** Consider whether BG should be added to the source in `check_ct_entails_kb` as well:
```python
def check_ct_entails_kb(self):
    source = self.ct_clauses + self.bg_clauses
    return self._check_entails(source, self.kb_clauses)
```

This depends on whether KB clauses are meant to stand alone or with BG. If the KB is intended to represent constraints beyond BG, current behavior is correct. Document the decision explicitly either way.

---

## High Priority

### H1. Solver name inconsistency: `glucose3` vs `glucose4`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/semantic_equivalence.py` line 60

```python
solver_name: str = 'glucose3'
```

Every other solver default in the codebase uses `'glucose4'`. This should be consistent.

**Fix:** Change default to `'glucose4'`.

### H2. No test for `ProgressiveEvaluator` or `_compare_by_semantic`

The `progressive_evaluation.py` (190 lines) and `_compare_by_semantic` in `kb_comparator.py` have **zero direct tests**. The pipeline is complex -- it creates `ConGenRunResult`, feeds `ConGenResultData`, runs three comparison strategies. Unit tests that mock `ConGenRunner` would catch regressions.

**Recommendation:** Add at least:
- Test `ProgressiveEvaluator.evaluate()` with mocked runner
- Test `_compare_by_semantic()` with known clause sets
- Test edge case: empty `query_history`

### H3. `progressive_evaluation.py` accesses `congen_result.kb_clauses` -- verify attribute exists

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/progressive_evaluation.py` line 166

```python
sem_result = self._run_semantic_check(
    congen_result.kb_clauses, congen_result.bg_clauses)
```

`ConGenRunResult` has `kb_clauses: List[List[int]]` (confirmed). This is fine. But the `ConGenResultData` constructed on line 155-160 does NOT have `kb_clauses` -- it only has `kb_constraints` (string IDs). This means line 166 relies on `congen_result` (the `ConGenRunResult`) NOT the `result_data` (the `ConGenResultData`). Variable naming is confusing but correct.

**Recommendation:** Rename `result_data` to `comparator_data` or similar to reduce confusion.

### H4. Redundant double-filter in `ProgressiveEvaluator.evaluate()`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/progressive_evaluation.py` lines 130, 145

```python
main_queries = [(c, a, s) for c, a, s in query_history if s == 'main']
# ...
pos, neg = queries_to_assignment_lists(sliced, source_filter='main')
```

`sliced` is already filtered to `source='main'`, so `source_filter='main'` matches everything. Not a bug, but unnecessary work and could confuse readers into thinking there are other sources still present.

**Fix:** Either remove the filter in `queries_to_assignment_lists` call or document the redundancy.

### H5. `process_model` bare `except Exception` catches too broadly

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_evaluation.py` lines 147-151

```python
except Exception as e:
    print(f"Error processing {model_name}: {e}")
    import traceback
    traceback.print_exc()
    return None
```

This silently swallows all exceptions and continues to next model. While acceptable for batch processing, `KeyboardInterrupt` is a subclass of `BaseException` so it won't be caught. Consider at minimum logging the traceback to a file. The `import traceback` inside the except is a code smell -- it should be at module level.

**Fix:** Move `import traceback` to top of file. Consider `logging.exception()` instead of `print + traceback`.

---

## Medium Priority

### M1. `to_dict()` truncates unentailed clauses to 20

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/semantic_equivalence.py` lines 41-42

```python
'unentailed_ct': [list(c) for c in self.unentailed_ct[:20]],
'unentailed_kb': [list(c) for c in self.unentailed_kb[:20]],
```

Silently truncating to 20 without indicating total count. A reader of the JSON might not realize data was lost.

**Fix:** Add `'n_unentailed_ct': len(self.unentailed_ct)` and `'n_unentailed_kb': len(self.unentailed_kb)` fields.

### M2. `_compare_by_semantic` metrics mapping is approximate

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/kb_comparator.py` lines 316-324

```python
metrics = EvaluationMetrics(
    true_positives=n_ct_entailed,
    false_negatives=len(sem_result.unentailed_ct),
    false_positives=len(sem_result.unentailed_kb),
    true_negatives=0
)
```

Mapping semantic entailment counts to TP/FP/FN is a proxy, not exact. An entailed CT clause is not the same as a "true positive constraint." Document this mapping with a comment explaining the semantics.

### M3. `ProgressiveEvaluator.checkpoints_pct` mutable default

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/progressive_evaluation.py` line 108

```python
checkpoints_pct: List[int] = None,
```

Uses `None` with `or` pattern, which is correct. But the type annotation should be `Optional[List[int]]` for mypy compliance.

### M4. `query_converter.py` index counter increments only on matching source

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/examples/query_converter.py` lines 28-40

```python
idx = 0
for config, answer, source in query_history:
    if source != source_filter:
        continue
    # ...
    example = Example(id=f"q{idx}{suffix}", ...)
    idx += 1
```

This means IDs are sequential (q0, q1, q2...) after filtering. Good for uniqueness, but the IDs don't correspond to positions in the original history. This is a design choice, not a bug, but worth documenting.

### M5. `run_evaluation.py` `output.update(prog_result.to_dict())` may overwrite keys

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_evaluation.py` line 119

```python
output = {'metadata': {...}, 'quacq': {...}}
output.update(prog_result.to_dict())
```

`ProgressiveResult.to_dict()` returns keys: `total_queries`, `metadata`, `progressive`, `quacq`. Both `metadata` and `quacq` overlap with the existing `output` dict. The `update()` will **overwrite** the original `metadata` and `quacq` values.

**This is a correctness bug.** The final JSON will lose the QuAcq-specific metadata.

**Fix:** Namespace the progressive result:
```python
output['progressive'] = prog_result.to_dict()['progressive']
output['quacq']['comparison'] = prog_result.to_dict()['quacq']['comparison']
```

### M6. `_task_compat.py` duck-typing relies on `hasattr` -- fragile

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/interactive/_task_compat.py`

Using `hasattr` to distinguish task types works now but is fragile. If either class adds the other's attribute name, the dispatch breaks.

**Recommendation:** Use `isinstance` checks (already done in `quacq.py` via `_is_quacq_task()`) for safety. Consider adding a `task_type` attribute or using Protocol for type safety.

### M7. `InteractiveResult.load()` backward compat for 2-tuple query history

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/interactive/result.py` line 122

```python
query_history = [
    (qh['config'], qh['answer'], qh.get('source', 'main'))
    for qh in data.get('query_history', [])
]
```

Handles new format (`{'config', 'answer', 'source'}`) with `get('source', 'main')` default. But what about old format where `query_history` items were `[config, answer]` tuples (not dicts)? If loading old JSON files, accessing `qh['config']` on a list would raise `TypeError`.

**Recommendation:** Add a type check:
```python
if isinstance(qh, dict):
    # new format
else:
    # legacy 2-tuple format
```

---

## Low Priority

### L1. `checkpoints_pct` allows duplicate checkpoints

If user provides `[25, 25, 50]`, ConGen will run twice at 25%. No dedup.

### L2. Missing `__all__` in `query_converter.py`

Not strictly needed for internal module, but other modules in the package define `__all__`.

### L3. `_print_checkpoint_table` separator width hardcoded

The separator `{'-'*58}` doesn't match the actual table width (which varies with data).

---

## Edge Cases Found

1. **Empty query history:** `ProgressiveEvaluator.evaluate()` handles this -- `n=0` triggers `continue`, skipping all checkpoints. But `result.checkpoints` will be empty, and `prog_result.quacq_*` comparisons still run. If QuAcq learned nothing, `quacq_run_result.kb_constraints` is `[]` and `kb_clauses` is `[]` -- semantic checker handles empty KB correctly.

2. **All queries from findc, none from main:** `main_queries` will be empty, `total=0`. All checkpoints skipped. No progressive data generated. The QuAcq final comparison still runs. This is a valid edge case for FMs where every query requires scope decomposition.

3. **Single-literal clause negation:** In `_check_entails`, clause `[x]` is negated as `[[-x]]`. Correct.

4. **`dict.update()` key collision in `run_evaluation.py`:** Found and reported as M5 above.

5. **`ConGenRunner.run()` failure at a checkpoint:** The `ProgressiveEvaluator.evaluate()` method does not catch exceptions from `self.congen_runner.run()`. A failure at one checkpoint will abort the entire evaluation.

---

## Positive Observations

1. **Clean separation of concerns:** Query converter, semantic equivalence, and progressive evaluation are well-isolated modules with single responsibilities.

2. **Backward compatibility:** The `_task_compat.py` duck-typing layer and `source='main'` default ensure existing code continues to work unchanged.

3. **Good test coverage for new primitives:** `test_query_converter.py` (10 tests) and `test_semantic_equivalence.py` (8 tests) cover key scenarios including empty inputs, edge cases, and serialization.

4. **Proper resource cleanup:** `findc.py` uses try/finally for solver cleanup. `interactive_runner.py` uses try/finally for tracemalloc and oracle cleanup.

5. **Config-driven pipeline:** TOML configuration is clean and extensible for batch experiments.

6. **SAT solver lifecycle:** `SemanticEquivalenceChecker._check_entails` uses context manager (`with Solver(...) as solver`) for each check -- no leaked solvers.

---

## Recommended Actions (Priority Order)

1. **[Critical] Fix M5** -- `output.update()` key collision in `run_evaluation.py` will silently overwrite QuAcq metadata. This corrupts output JSON.
2. **[Critical] Fix C1** -- Add `Optional` import and fix type annotation for `bg_clauses` parameter.
3. **[High] Fix H1** -- Change default solver to `glucose4` in `semantic_equivalence.py`.
4. **[High] Decide C2** -- Document BG clause policy for `check_ct_entails_kb` direction.
5. **[Medium] Fix M1** -- Add total counts for truncated unentailed clause lists.
6. **[Medium] Fix H5** -- Move `import traceback` to module level; use `logging.exception`.
7. **[Medium] Add M2 comment** -- Document the semantic-to-metrics mapping approximation.
8. **[Low] Add tests for H2** -- Progressive evaluator integration tests.

---

## Metrics

- **Type Coverage:** Moderate -- most public APIs have type hints, but `_task_compat.py` uses untyped duck-typing (`task`, `c_id`).
- **Test Coverage:** 18 new tests pass. Missing coverage for `progressive_evaluation.py` and `_compare_by_semantic`.
- **Linting Issues:** 2 type annotation issues (C1, M3). 1 import location issue (H5).

---

## Unresolved Questions

1. Should BG clauses be included in the `check_ct_entails_kb` direction? The current design excludes them, which may undercount equivalence.
2. Should `ProgressiveEvaluator.evaluate()` catch per-checkpoint exceptions and continue, or fail fast?
3. Is the `_task_compat.py` duck-typing layer intended to be permanent, or should it be migrated to `isinstance` checks before the deprecated `InteractiveTask` is removed?
