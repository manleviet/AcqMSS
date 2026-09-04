---
title: "Refactor FindScope & FindC to Classes"
description: "Convert find_scope/find_c standalone functions to FindScope/FindC classes following QuAcq DI pattern"
status: complete
priority: P2
effort: 1h
branch: main
tags: [refactor, quacq, class-design]
created: 2026-02-28
---

# Refactor FindScope & FindC to Classes

## Summary

Convert `find_scope()` and `find_c()` from standalone module-level functions (11-12 params each) to `FindScope` and `FindC` classes with constructor-injected collaborators (oracle, checker, profiler/generator) and a `run()` method for per-call algorithm data.

## Brainstorm Report

- [brainstorm-260228-0450-findscope-findc-class-refactor.md](../reports/brainstorm-260228-0450-findscope-findc-class-refactor.md)

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | Convert FindScope & FindC to classes | complete | [phase-01](phase-01-convert-to-classes.md) |
| 2 | Integrate into QuAcq & update exports | complete | [phase-02](phase-02-integrate-quacq.md) |

## Key Design Decisions

- **Constructor**: collaborators (oracle, checker, profiler, generator)
- **Method `run()`**: per-call algorithm data (e, R, Y, constraint_clauses, etc.)
- **Private helpers**: become instance methods (`self._prune_rejecting_partial`, `self._narrow_with_generator`)
- **QuAcq ownership**: creates FindScope/FindC internally as `self._find_scope`, `self._find_c`
- **remaining_bias**: stays mutable (status quo)
- **No external API changes**: QuAcq constructor signature unchanged

## Files Modified

| File | Change |
|---|---|
| `conacq/algorithms/quacq/findscope.py` | function → FindScope class |
| `conacq/algorithms/quacq/findc.py` | function → FindC class |
| `conacq/algorithms/quacq/quacq.py` | create instances in `__init__`, update call sites |
| `conacq/algorithms/quacq/__init__.py` | export FindScope/FindC classes |

## Success Criteria

- All existing tests pass
- No external API changes
- Call sites in QuAcq.learn() use fewer args (oracle/profiler/generator via constructor)
- FindScope/FindC independently testable via class instantiation
