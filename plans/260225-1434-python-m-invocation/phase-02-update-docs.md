---
parent: ./plan.md
status: complete
priority: P3
effort: 15m
---

# Phase 2: Update Documentation

## Overview

Update all documentation files that reference `PYTHONPATH=. python apps/` pattern to use `python -m apps.` instead.

## Related Code Files

### Modify
- `README.md` — workflow commands, usage examples
- `CLAUDE.md` — Quick Commands section
- `docs/codebase-summary.md` — script invocation references

### Skip (historical records)
- `plans/` — all plan files and reports (don't rewrite history)
- `data/examples/README.md` — check if needs update

## Implementation Steps

1. Update `README.md`: replace all `PYTHONPATH=. python apps/X.py` with `python -m apps.X`
2. Update `CLAUDE.md`: Quick Commands section
3. Update `docs/codebase-summary.md`: any script references
4. Check `data/examples/README.md` for references
5. Keep `PYTHONPATH=. pytest tests/` unchanged (test runner, not app script)

## Todo

- [ ] Update README.md
- [ ] Update CLAUDE.md
- [ ] Update docs/codebase-summary.md
- [ ] Check data/examples/README.md
- [ ] Run tests: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- All non-plan docs show `python -m apps.X` pattern
- `PYTHONPATH=. pytest` references unchanged
- Tests pass (308/310)

## Risk Assessment

- **Low**: Documentation-only changes, no code impact
