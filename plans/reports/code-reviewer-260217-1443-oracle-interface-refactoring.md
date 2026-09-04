# Code Review: Oracle Interface Refactoring

**Reviewer:** code-reviewer
**Date:** 2026-02-17
**Plan:** plans/260217-1358-oracle-interface-refactoring

---

## Scope

- **Files reviewed:** 18 files across `acqmss/oracle/`, `acqmss/algorithms/`, `acqmss/example_generators/`, `acqmss/eval/`, `apps/`, `tests/`
- **Focus:** Correctness, remaining stale references, type safety, backward compatibility
- **LOC changed:** ~300 (estimated from diff surface)

---

## Overall Assessment

The refactoring achieves its stated goal: Oracle ABC is slimmed to `is_valid()` + `ask()`, FM metadata is extracted into a frozen `FMData` dataclass, and callers are updated to use `FMData` or `FeatureModelOracle` directly. The architecture is cleaner, and the separation of concerns is improved.

However, there is one **critical** incomplete item and a few **medium** issues.

---

## Critical Issues

### 1. `get_cnf_clauses()` NOT removed from `FeatureModelOracle` -- contradicts plan decision

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py` (line 162-164)
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py` (line 214)

The plan's Validation Log explicitly states:
> "get_cnf_clauses() should be REMOVED from FeatureModelOracle entirely (not kept as concrete method)"

But `get_cnf_clauses()` is still defined on `FeatureModelOracle` (line 162), and `InteractiveLearner.from_examples()` still calls it (line 214):

```python
# learner.py:214
learner._fm_clauses = oracle.get_cnf_clauses()
```

The plan decision (Q2, Q6) was to refactor `from_examples()` to use `oracle.is_valid()` instead of SAT-checking CNF clauses. This was NOT done.

Additionally, `learn_from_examples()` (line 233-237) passes `self._fm_clauses` to `QuAcq.learn_from_examples()`, which uses it for consistency checking via `OneShotModel`. The entire `_fm_clauses` flow remains intact.

**Impact:** The plan's core architectural goal (Oracle only answers membership queries) is violated. `get_cnf_clauses()` exposes SAT internals through the Oracle.

**However** -- there is a practical tension here. The `learn_from_examples()` code path uses `fm_clauses` for FindScope/FindC SAT checks, which are structurally different from simple `is_valid()` calls. Replacing this with `oracle.is_valid()` per-example would work for the simple consistency check but NOT for the SAT-level FindScope/FindC operations that need raw clauses.

**Recommendation:** Either:
- (a) Remove `get_cnf_clauses()` from `FeatureModelOracle` and have `from_examples()` get clauses from `FMOracleModel` directly (via `oracle._oracle_model.get_raw_fm_clauses()`), OR
- (b) Accept that `get_cnf_clauses()` stays as a concrete method on `FeatureModelOracle` (not on Oracle ABC) and update the plan to reflect this deliberate decision. This is the pragmatic choice since the example-based learning fundamentally needs raw FM clauses for FindScope/FindC.

---

## High Priority

### 2. Plan action items not executed

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/plans/260217-1358-oracle-interface-refactoring/plan.md` (lines 95-98)

The following action items remain unchecked:
- `[ ] Update Phase 1: remove get_cnf_clauses() from FeatureModelOracle`
- `[ ] Update Phase 3: refactor from_examples() to use oracle.is_valid()`
- `[ ] Update Phase 5: remove from_fm_oracle() factory`
- `[ ] Update Phase 6: remove get_cnf_clauses() cleanup`

The `from_fm_oracle()` removal (Phase 5) IS done -- `GroundTruthData` has no such method. But the checkboxes were not updated.

All phase statuses remain "pending" despite the code changes being implemented.

**Recommendation:** Update plan statuses and check off completed items.

### 3. `apps/generate_examples.py` uses `oracle.get_features()` directly

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/generate_examples.py` (line 143)

```python
n_features = len(oracle.get_variables())
```

This still works because `get_features()` is a concrete method on `FeatureModelOracle`. Not broken, but inconsistent with the pattern of using `oracle.get_fm_data().feature_count`.

**Recommendation:** Migrate to `oracle.get_fm_data().feature_count` for consistency with the new pattern. Low urgency since `get_features()` remains available on the concrete class.

---

## Medium Priority

### 4. `FMData.features` is a mutable `Set[str]` inside a frozen dataclass

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_data.py` (line 23)

```python
@dataclass(frozen=True)
class FMData:
    features: Set[str]
    feature_ids: Dict[str, int]
```

`frozen=True` prevents reassignment of attributes but does NOT prevent mutation of mutable containers. A caller could do `fm_data.features.add("hacked")` and it would succeed silently.

**Impact:** Violates the "immutable" invariant documented in the docstring. Could lead to subtle bugs if callers accidentally mutate shared FMData instances.

**Recommendation:** Use `frozenset` for `features` and convert `feature_ids` to `MappingProxyType` in `__post_init__`, or document that callers must not mutate. Pragmatically, `frozenset` for features is a simple change:

```python
features: frozenset  # instead of Set[str]
```

And in `FeatureModelOracle.get_fm_data()`:

```python
features = frozenset(self.get_variables()),
```

### 5. `FeatureModelOracle.__repr__` inconsistency with Phase 1 goal

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/fm_oracle.py` (line 186)

```python
def __repr__(self):
    return f"FeatureModelOracle(features={len(self._oracle_model.variables)})"
```

Phase 1 noted: "updated `__repr__` to not use `get_feature_count()`". The current implementation uses `len(self._oracle_model.variables)` which is fine. This is resolved correctly.

### 6. `GroundTruthData` is NOT frozen

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/extractor.py` (line 14)

```python
@dataclass
class GroundTruthData:
```

Unlike `FMData`, `GroundTruthData` is a plain `@dataclass` (not frozen). This is acceptable since it is populated from a factory method and not intended to be shared/cached like FMData. Just noting for consistency awareness.

### 7. Test fixture `interactive_task` uses `oracle.get_feature_ids()` directly

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_interactive.py` (line 52)

```python
feature_ids = oracle.get_feature_ids()
```

This works fine since `get_feature_ids()` is a concrete method on `FeatureModelOracle`. But it could use `oracle.get_fm_data().feature_ids` for consistency with the new pattern.

**Recommendation:** Low priority. Leave as-is since tests are allowed to call concrete methods directly.

---

## Low Priority

### 8. Redundant import in `task_preparation.py`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py` (lines 27-28)

```python
if TYPE_CHECKING:
    from ..oracle import FeatureModelOracle
    from ..oracle.fm_data import FMData
```

`FMData` could be imported via `from ..oracle import FMData` for consistency with the `FeatureModelOracle` import. Minor style nit.

### 9. `OracleData` backward compat alias exported from two packages

**Files:**
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/__init__.py` (line 29)
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/__init__.py` (line 87)

Both export `OracleData` as backward compatibility alias. This is intentional and correct -- callers can import from either package.

**Recommendation:** Add a deprecation note or `warnings.warn()` in `OracleData` usage to guide future cleanup.

---

## Positive Observations

1. **Clean Oracle ABC** -- only `is_valid()` as abstract, `ask()` as a concrete alias. Minimal, clear contract.
2. **FMData as frozen dataclass** -- good pattern for extracting immutable snapshots of mutable state. `feature_count` as a computed property is clean.
3. **CachedOracle simplification** -- only caches `is_valid()`, which is the only method it needs. Clean wrapper.
4. **UserPromptOracle** -- well-structured interactive oracle with only `is_valid()` implementation.
5. **ConGenModel.prepare()** correctly extracts `FMData` and passes to `ConGenTaskPreparation` -- decouples model from direct FM dependency.
6. **_build_task_from_bias takes FMData** -- good separation, static method, testable in isolation (test at line 327).
7. **TestOracleABC** verifies the ABC contract via introspection -- excellent regression guard.
8. **TestFMData** verifies immutability and correct population -- solid coverage.
9. **GroundTruthData.from_uvl()** reads FM directly without instantiating an Oracle -- proper separation.
10. **GenerateNE kept as-is** -- correct YAGNI decision, avoiding unnecessary parameter explosion.

---

## Edge Cases Found

1. **`from_examples()` + `learn_from_examples()` flow still depends on `get_cnf_clauses()`** -- this is the primary gap. If `get_cnf_clauses()` were removed, the `InteractiveRunner` and cross-validation pipeline would break.

2. **`FMData.feature_ids` mutation** -- if two callers share an FMData instance and one mutates `feature_ids`, the other sees the change. Frozen dataclass does not prevent this.

3. **`complete_configuration()` on FeatureModelOracle creates a new Solver per call** (line 125-136) -- no pooling. This is acceptable for the current use case but worth noting for future performance optimization.

4. **`CachedOracle` wrapping `FeatureModelOracle`** -- if a caller has `CachedOracle`, they lose access to `get_fm_data()`, `complete_configuration()`, etc. The type system correctly prevents this (CachedOracle types as Oracle), but callers must know to extract FMData BEFORE wrapping.

---

## Recommended Actions (Prioritized)

1. **[Critical]** Decide on `get_cnf_clauses()` fate: either remove it and refactor `from_examples()` flow, or accept it as a concrete FeatureModelOracle method and update the plan. The current state is inconsistent with the plan's decisions.

2. **[High]** Update plan.md phase statuses from "pending" to "done" for completed phases. Check off completed action items.

3. **[Medium]** Consider `frozenset` for `FMData.features` to truly enforce immutability.

4. **[Low]** Migrate `apps/generate_examples.py:143` from `oracle.get_features()` to `oracle.get_fm_data().feature_count`.

5. **[Low]** Add deprecation marker to `OracleData` alias for future cleanup.

---

## Metrics

| Metric | Value |
|--------|-------|
| Type Coverage | Good -- `FMData` typed, `Oracle` ABC typed, `TYPE_CHECKING` used correctly |
| Test Coverage | FMData, Oracle ABC, CachedOracle, learner from_files, _build_task_from_bias covered |
| Linting Issues | 0 (no syntax/import errors found) |
| Stale References | 1 critical (`get_cnf_clauses` in learner), 1 low (`oracle.get_features()` in apps) |

---

## Unresolved Questions

1. Should `get_cnf_clauses()` stay on `FeatureModelOracle` as a pragmatic concession (since FindScope/FindC genuinely need raw clauses), or should the `from_examples()` flow be restructured to avoid it? The plan says remove, but the implementation complexity may not justify it.

2. Should `FMData` enforce true deep immutability (frozenset + MappingProxyType), or is the frozen dataclass sufficient with a "don't mutate" convention?
