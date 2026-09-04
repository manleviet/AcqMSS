---
title: "Switch to python -m invocation pattern"
description: "Replace PYTHONPATH=. python apps/x.py with python -m apps.x across all scripts and docs"
status: complete
priority: P3
effort: 30m
branch: main
tags: [dx, refactor, scripts]
created: 2026-02-25
---

# Switch to `python -m` Invocation Pattern

## Goal

Replace `PYTHONPATH=. python apps/script.py` with `python -m apps.module` across all scripts and documentation.

## Motivation

- Eliminates `PYTHONPATH=.` requirement (`python -m` adds CWD to `sys.path` automatically)
- More Pythonic invocation pattern
- Better IDE run config support
- Backward compat preserved (old pattern still works)

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Create package + update scripts](./phase-01-package-and-scripts.md) | complete | 15m |
| 2 | [Update documentation](./phase-02-update-docs.md) | complete | 15m |

## Scope

- 10 scripts in `apps/`
- 10 TOML configs in `apps/conf/`
- README.md, CLAUDE.md, docs/codebase-summary.md
- Tests invocation unchanged (`PYTHONPATH=. pytest` stays)
