---
title: "Move QueryGenerator & ExampleProvider to example_generators"
description: "Refactor: relocate QueryGenerator and ExampleProvider into the example_generators package for better cohesion"
status: pending
priority: P2
effort: 30m
branch: main
tags: [refactoring, module-organization]
created: 2026-02-13
---

# Move QueryGenerator & ExampleProvider to example_generators

## Motivation

`QueryGenerator` (SAT-based query generation) and `ExampleProvider` (shuffled example pool) are conceptually "example/query generation" concerns, not oracle or algorithm concerns. Moving them into `acqmss/example_generators/` improves cohesion.

## Current Locations

| Class | Current Location | LOC |
|-------|-----------------|-----|
| QueryGenerator | `acqmss/algorithms/interactive/query_generator.py` | ~262 |
| ExampleProvider | `acqmss/oracle/example_provider.py` | ~50 |

## Target Package

`acqmss/example_generators/` -- already contains `ExampleGenerator`, `RandomSamplingGenerator`, `FeatureFrequencyGenerator`, `NWiseCoverageGenerator`.

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| [Phase 01](phase-01-move-files.md) | Move files, update internal imports | pending |
| [Phase 02](phase-02-update-references.md) | Update all external references, verify | pending |

## Key Decision

**No backward-compatibility re-exports.** Old import paths removed entirely (internal codebase, no external consumers).

## Files Affected (Complete List)

**Moved:** `query_generator.py`, `example_provider.py`
**Updated `__init__.py`:** `example_generators/`, `algorithms/`, `algorithms/interactive/`, `oracle/`
**Updated imports:** `quacq.py`, `findc.py`, `learner.py`, `test_interactive.py`
**Docs updated:** `code-standards.md` (oracle import example)

## Verification

```bash
PYTHONPATH=. python -c "from acqmss.example_generators import QueryGenerator, ExampleProvider"
PYTHONPATH=. pytest tests/ -v
```
