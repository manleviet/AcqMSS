# Brainstorm: QuAcq DescriptionProvider Refactor

## Problem Statement

QuAcq passes `DescriptionProvider` as parameter to `learn()` algorithm, violating separation of concerns. ConGen does it correctly — algorithm returns raw IDs, runner resolves names afterward via `model.resolve_kb()`.

## Current State

| Aspect | QuAcq (problematic) | ConGen (clean) |
|--------|---------------------|----------------|
| Provider passed to | `quacq.learn(description_provider=...)` | Not passed to algorithm |
| Resolution timing | Inside `_build_result()` | After `acquire()`, via `model.resolve_kb()` |
| Coupling | Algorithm knows about presentation | Algorithm only deals with IDs |

## Evaluated Approaches

### Approach A: Mirror ConGen pattern (Recommended)
- Remove `description_provider` param from `learn()` and `_build_result()`
- Add `resolve_kb()` to `QuAcqModel` (same as ConGen)
- Runner resolves names after `learn()` returns

**Pros:** Clean SRP, consistent with ConGen, algorithm purely about learning
**Cons:** Minor test updates needed

### Approach B: Keep current, document it
- No code changes, just document the inconsistency

**Pros:** Zero effort
**Cons:** Technical debt remains, inconsistent design across packages

## Recommended Solution: Approach A

### Changes Required

1. **`quacq.py`**: Remove `description_provider` from `learn()` signature and `_build_result()`. Return raw IDs only in `kb_constraints` field (or remove it, let runner fill it).
2. **`quacq_model.py`**: Add `resolve_kb(kb_assumption_ids)` method mirroring ConGen's pattern.
3. **`quacq_runner.py`**: After `learn()` returns, call `model.resolve_kb()` to populate constraint names on result.
4. **`test_quacq.py`**: Update tests — remove `description_provider` param from `learn()` calls, verify names via model instead.

### Risk Assessment
- **Low risk**: Provider already optional in `_build_result()` (fallback to `str(id)`)
- **No behavioral change**: Same names resolved, different layer
- **Test impact**: Mechanical updates, no logic changes

## Success Metrics
- `description_provider` no longer appears in QuAcq algorithm signatures
- All tests pass
- Name resolution works identically via runner layer

## Next Steps
Create implementation plan with phases.
