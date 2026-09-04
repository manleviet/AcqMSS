# Phase 3: Test & Verify

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-simplify-congen-shuffle.md), [Phase 2](phase-02-quacq-build-to-init.md)

## Overview
- Priority: P3
- Description: Run full test suite, verify deterministic behavior
- Implementation status: complete
- Review status: complete

## Implementation Steps

1. Run full test suite:
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```

2. If failures: fix and re-run

3. Code review via code-reviewer agent

4. Update docs via docs-manager agent

## Todo List
- [ ] Full test suite passes
- [ ] Code review completed
- [ ] Docs updated

## Success Criteria
- All tests pass
- Both runners use identical shuffle-after-prepare pattern
- No regressions
