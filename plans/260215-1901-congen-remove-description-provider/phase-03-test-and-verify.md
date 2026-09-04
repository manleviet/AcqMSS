# Phase 3: Test & Verify

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-simplify-congen-and-result.md), [Phase 2](phase-02-update-callers.md)

## Overview
- **Priority:** High
- **Status:** complete
- **Description:** Run full test suite, verify no regressions, confirm import cleanup.

## Requirements
- All existing tests pass
- No references to old CONGENResult field names
- No unused imports of DescriptionProvider in algorithm layer

## Implementation Steps

1. **Run tests:**
   ```bash
   PYTHONPATH=. pytest tests/test_congen.py -v
   ```

2. **Verify no stale references:**
   - Grep for `kb_constraints` in codebase — should only exist in non-congen files or as resolved output
   - Grep for `redundant_constraints` — same
   - Grep for `description_provider` in congen.py — should not exist (except maybe save_result)

3. **Run full test suite** (if other tests exist):
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```

4. **Fix any failures** — iterate until green

## Todo
- [x] Run test_congen.py — all tests pass
- [x] Run full test suite — no regressions
- [x] Verify no stale field references
- [x] Verify DescriptionProvider import removed from congen.py core

## Success Criteria
- All tests green
- `grep -r "description_provider" acqmss/algorithms/congen.py` returns nothing (or only in save_result)
- Clean separation: algorithm layer has no presentation logic

## Risk Assessment
- **Low:** If Phase 1-2 are correct, tests should pass without issues

## Security Considerations
- None

## Next Steps
- Done. Optionally: update `acqmss/algorithms/__init__.py` exports if CONGENResult fields changed
