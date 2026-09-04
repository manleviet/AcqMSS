# Documentation Update: QuAcq DescriptionProvider Refactoring

**Date**: 2026-02-28
**Status**: COMPLETED
**Scope**: Update documentation to reflect removal of `description_provider` parameter from `QuAcq.learn()`

## Summary

The QuAcq algorithm has been refactored to match ConGen's clean separation of concerns. Previously, `QuAcq.learn()` accepted a `description_provider` parameter to resolve learned constraint IDs to human-readable names. This has been removed to simplify the algorithm layer.

**New Pattern**: Algorithm returns raw assumption IDs, runner layer resolves names via `model.resolve_kb()`. Matches ConGen: algorithm → IDs, runner → names.

## Changes Made

### 1. Updated system-architecture.md

- **Last Updated timestamp**: Changed to 2026-02-28 (QuAcq DescriptionProvider refactoring)
- **API Example Update**: Clarified that `quacq.learn()` returns `QuAcqResult` with KB assumption IDs only
- **Added Note**: "Runner resolves names: `kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)`"
- **QuAcq Flow Diagram**: Updated result representation section
  - Removed: "kb_constraints resolved via DescriptionProvider"
  - Added: "kb_constraints resolved by runner via model.resolve_kb()"

### 2. Updated quacq.md

- **Last Updated timestamp**: Changed to 2026-02-28 (DescriptionProvider refactoring)
- **Code Example**: Updated the learn() → resolve pattern
  - Before: Direct result using `result.kb_constraints`
  - After: Shows two-step pattern: algorithm returns IDs, runner calls `model.resolve_kb()`
- **QuAcqResult Description**: Updated to clarify new responsibility boundaries
  - `kb_assumption_ids`: Primary (from algorithm)
  - `kb_constraints`: Secondary (resolved by runner)
  - Added note: "Pattern matches ConGen"

### 3. Updated code-standards.md

- **Last Updated timestamp**: Changed to 2026-02-28
- **QuAcq Facade Pattern Example**: Expanded to show name resolution flow
  - Clarified that algorithm returns raw assumption IDs
  - Added explicit `model.resolve_kb()` call in runner.run()
  - Shows complete return path with resolved KB
- **Learn Method Docstring**: Added clarification about DI pattern and name resolution responsibility

## Technical Details

### Pattern

```python
# Algorithm returns raw IDs (no description_provider param)
result = quacq.learn(
    set_c=task.set_c, ...,
    mode='oracle', max_queries=1000
)  # → QuAcqResult.kb_assumption_ids: List[int]

# Runner resolves names (matches ConGen)
kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)

# Return result with resolved names
return QuAcqRunResult(
    kb_constraints=kb_names,
    kb_clauses=kb_clauses,
    ...
)
```

### Key Benefits

1. **Separation of Concerns**: Algorithm focuses on constraint discovery, runner handles presentation
2. **ConGen Alignment**: Both acquisition paradigms now follow identical pattern
3. **Simpler API**: No description provider injection needed in algorithm layer
4. **Reusability**: Multiple presentation strategies possible via different runners/wrappers

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| docs/system-architecture.md | Timestamp, API example, result diagram | ~5 edits |
| docs/quacq.md | Timestamp, code example, result description | ~4 edits |
| docs/code-standards.md | Timestamp, facade pattern example, docstring | ~3 edits |

All changes focused on documentation only. No code behavior changes documented — only clarification of responsibility boundaries between algorithm and runner layers.

## Verification

Documentation updates are minimal and surgical:
- Only sections directly affected by the refactoring were updated
- Responsibility boundary clearly articulated: algorithm returns IDs, runner resolves names
- Pattern consistency with ConGen emphasized throughout
- All code examples follow the new two-step pattern (learn → resolve)

## No Breaking Changes

These are documentation-only updates. The refactoring was completed in previous commits:
- `conacq/algorithms/quacq/quacq.py` — learn() signature (removed description_provider)
- `conacq/runners/quacq_runner.py` — run() method includes resolve_kb() call
- Tests already passing with new pattern

## Questions/Notes

None at this time. The refactoring cleanly aligns QuAcq with ConGen's architecture.
