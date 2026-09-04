---
title: "Extract oracle code into acqmss/oracle package"
description: "Consolidate Oracle ABC, FeatureModelOracle, and interactive oracle classes into a dedicated acqmss/oracle/ package"
status: complete
priority: P3
effort: 30m
branch: main
tags: [refactor, extraction, oracle]
created: 2026-02-13
---

# Extract Oracle Code into `acqmss/oracle/` Package

## Motivation

Oracle-related code is split across two unrelated packages:
- `acqmss/testcases/oracle.py` — Oracle ABC + FeatureModelOracle
- `acqmss/algorithms/interactive/user_interface.py` — InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider

These classes form a cohesive domain (oracle/ground-truth interfaces) and belong together. `OracleData` in `acqmss/eval/oracle_extractor.py` stays in eval — it's evaluation-specific data extraction.

## Target Structure

```
acqmss/oracle/
├── __init__.py          # Re-exports all oracle classes
├── oracle.py            # Oracle ABC + FeatureModelOracle (from testcases/oracle.py)
└── interactive.py       # InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider (from interactive/user_interface.py)
```

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| [Phase 1](phase-01-create-oracle-package.md) | Create `acqmss/oracle/` package, move files, fix internal imports | complete |
| [Phase 2](phase-02-update-imports-and-cleanup.md) | Update all consumer imports (15 files), delete old files, verify | complete |

## Consumer Impact

15 files import oracle classes directly or transitively. No backward-compat shims — clean break.

## Verification

```bash
# After both phases
PYTHONPATH=. python -c "from acqmss.oracle import Oracle, FeatureModelOracle, AutomatedOracle"
PYTHONPATH=. pytest tests/ -v
```
