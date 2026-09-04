# Checker.py Redundancy Analysis Report

**File:** `explanation/operations/algorithms/checker.py` (478 lines)
**Date:** 2026-02-13

## Summary

6 redundancy patterns found across 3 concrete checker classes. Estimated ~80 lines removable through DRY refactoring.

## Findings

### R1. Assumption-Delta Calculation (Duplicated 3x)

**Severity:** High — core business logic duplicated verbatim

| Class | Lines | Code |
|-------|-------|------|
| IncrementalPySATChecker | 207-212 | `set_c_set = set(set_c); delta = [...]; final_assumptions = set_c + [-1 * ...]` |
| NonIncrementalPySATChecker | 295-297 | Identical to above |
| SAT4JChecker | 375-377 | Same delta calc, but outputs unit clauses `[[a]]` instead of flat `[a]` |

**Pattern:** All 3 compute `delta = assumptions \ set_c`, then negate. PySAT classes produce flat list; SAT4J wraps in unit clauses.

**Fix:** Extract `_compute_delta(set_c) -> (enabled, disabled)` to base class. Each subclass formats output.

---

### R2. Pickle Protocol (Duplicated 3x)

**`__getstate__`:**
- NonIncremental (318-321) and SAT4J (413-416): **Identical** — `state['profiler'] = None`
- Incremental (239-247): Same + `state['solver'] = None`

**`__setstate__`:**
- NonIncremental (325-328) and SAT4J (419-422): **Identical** — restore profiler
- Incremental (249-257): Same + recreate solver

**Fix:** Move default `__getstate__`/`__setstate__` to `ConsistencyChecker`. Incremental overrides to add solver handling (~20 lines saved).

---

### R3. No-Op `cleanup()` (Duplicated 2x)

- NonIncremental (314-316): `pass`
- SAT4J (409-411): `pass`
- Base class declares `cleanup()` as `@abstractmethod`

**Fix:** Change base `cleanup()` from abstract to default no-op. Only IncrementalPySATChecker overrides (~6 lines saved).

---

### R4. `self.result` Instance Field — Dead State

- Set in base `__init__` (line 114): `self.result = False`
- Updated in each `is_consistent()`, then immediately returned
- **Never read externally** — grep confirms no `checker.result` access outside the class

**Fix:** Remove `self.result` from base. Use local variable in `is_consistent()`. Saves state pollution.

---

### R5. Constructor Field Duplication

All 3 concrete classes store identical fields:
- `self.set_kb`, `self.assumptions` — in all 3
- `self.solver_name` — in both PySAT classes

**Fix:** Could lift `set_kb`/`assumptions` storage to a shared mixin or intermediate base. However, this may over-engineer — the duplication is minimal (2 lines per class). **Low priority.**

---

### R6. Docstring Verbosity

- Module docstring: 87 lines (lines 1-87) — repeats class-level docs
- Each class docstring repeats module-level information
- Method docstrings in subclasses duplicate abstract method docs verbatim

**Estimate:** ~60 lines of docstrings could be trimmed without losing information.

**Fix:** Trim module docstring to ~15 lines. Remove subclass method docstrings that just repeat the abstract definition.

---

## Impact Summary

| ID | Pattern | Occurrences | Lines Saved | Priority |
|----|---------|-------------|-------------|----------|
| R1 | Delta calculation | 3x | ~12 | High |
| R2 | Pickle protocol | 3x | ~20 | High |
| R3 | No-op cleanup | 2x | ~6 | Medium |
| R4 | Dead self.result | 3x | ~6 | Medium |
| R5 | Constructor fields | 3x | ~4 | Low |
| R6 | Docstring bloat | N/A | ~60 | Low |
| **Total** | | | **~108** | |

## Unresolved Questions

1. Is `self.result` used via reflection/dynamic access anywhere? (Grep says no, but worth confirming with tests)
2. Should R5 (constructor fields) be addressed given the small savings vs. added abstraction complexity?
