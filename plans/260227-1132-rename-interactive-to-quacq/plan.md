---
title: "Rename interactive -> QuAcq + Add Example Modes"
description: "Rename interactive package/classes to QuAcq, add example_only/example_first support to run_quacq.py"
status: pending
priority: P2
effort: 2h
branch: main
tags: [refactoring, rename, quacq]
created: 2026-02-27
---

# Rename interactive -> QuAcq + Add Example Modes

## Summary

Rename `conacq/algorithms/interactive/` package and all associated classes/files/configs to use "QuAcq" naming. Add example_only/example_first mode support to the app script.

**Key decision**: Mode string `'interactive'` (oracle UX) stays unchanged -- only package/class/file names change. All 4 modes remain: `automated`, `interactive`, `example_only`, `example_first`.

## Phases

| # | Phase | Status | Effort | Key Files |
|---|-------|--------|--------|-----------|
| 1 | [Package Rename](phase-01-package-rename.md) | pending | 40m | interactive/ -> quacq/, model, task_prep, __init__.py |
| 2 | [Runner Rename](phase-02-runner-rename.md) | pending | 20m | interactive_runner.py -> quacq_runner.py, eval refs |
| 3 | [App + Config + Tests + Example Mode](phase-03-app-config-tests.md) | pending | 40m | run_interactive -> run_quacq, TOML, test file, ExampleIO |
| 4 | [Docs Update](phase-04-docs-update.md) | pending | 20m | 9 docs files, CLAUDE.md, README.md |

## Dependencies

- Phase 2 depends on Phase 1 (runner imports from package)
- Phase 3 depends on Phase 2 (app imports from runner)
- Phase 4 can start after Phase 3

## Risk Mitigation

- Use `git mv` for all renames to preserve history
- Delete `__pycache__` dirs after folder rename
- Run tests after each phase
- `'interactive'` mode string unchanged (UX mode, not algorithm name)

## Blast Radius

~15 .py files renamed/modified + 2 TOML + 9 docs + README + CLAUDE.md
