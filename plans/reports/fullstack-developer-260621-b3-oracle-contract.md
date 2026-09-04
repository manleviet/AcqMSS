# B3 Oracle Contract — Implementation Report

**Date:** 2026-06-21  
**Branch:** feat/redesign-abc  
**Phase:** 9 — B3 single Oracle contract

---

## Audited Contract (method list + rationale)

| Method | In ABC? | Consumer call-sites |
|--------|---------|---------------------|
| `is_valid` | yes (abstract) | quacq.py:203, findc.py:125, findscope.py:63, random_sampling.py:143/269, feature_frequency.py:111, base.py:54 |
| `ask` | yes (concrete alias) | quacq.py comment; external callers via Oracle reference |
| `get_variables` | yes (abstract) | `ExampleGenerator.base:34`, `apps/generate_examples.py:134` — BINDING (C5 depends on this) |
| `complete_configuration` | yes (abstract) | `ExampleGenerator.base:76`, `feature_frequency.py:198-200` |
| `get_bg_data` | yes (abstract) | `ConGenTaskPreparation:95`, `QuAcqTaskPreparation:104`, `QuAcqModel:71` |
| `get_kb` | no — FeatureModelOracle only | `generate_ne.py:119` — callers TYPE_CHECK as `FeatureModelOracle` |
| `get_assumptions` | no — FeatureModelOracle only | `generate_ne.py:120` |
| `get_c` | no — FeatureModelOracle only | `generate_ne.py:87` |
| `get_root_clauses` | no — FeatureModelOracle only | `congen_runner.py:195`, `quacq_runner.py:305` |
| `cleanup` | no — FeatureModelOracle only | `base_runner.py:121` |

**Decision rationale:** `get_kb / get_assumptions / get_c / get_root_clauses / cleanup` appear only in runners and `GenerateNE`, which are always parameterized with `FeatureModelOracle` via direct type annotation (`TYPE_CHECKING` guards). Making them abstract would force non-FM oracles to stub solver internals with no semantic meaning. They remain on `FeatureModelOracle`.

---

## Single Oracle Definition

`conacq/oracle/base.py` — replaces the old stub-heavy ABC.

Four abstract methods: `is_valid`, `get_variables`, `complete_configuration`, `get_bg_data`.  
One concrete method: `ask` (alias for `is_valid`).  
No empty `pass` stubs — removed entirely.

`base.py` imports `BGData` from `conacq/oracle/bg_data.py`; no circular dependency (bg_data has no oracle import).

---

## Delegation Fix

### CachedOracle (`conacq/oracle/cached.py`)
Previously: only implemented `is_valid`; `get_variables` / `complete_configuration` fell through to the `pass` stubs (returned `None`); `get_bg_data` raised `AttributeError`.

Fix: Added three delegation methods that forward directly to `self.base_oracle`:
- `get_variables()` → `base_oracle.get_variables()`
- `complete_configuration(partial)` → `base_oracle.complete_configuration(partial)`
- `get_bg_data()` → `base_oracle.get_bg_data()`

Only `is_valid`/`ask` remain cached; delegation methods are uncached (semantically correct — they return metadata, not query results).

### UserPromptOracle (`conacq/oracle/user_prompt.py`)
Previously: only implemented `is_valid`; same stub fall-through; `get_bg_data` raised `AttributeError`.

Fix:
- `get_variables()` — returns `set(self.features)` (the feature list supplied at construction)
- `complete_configuration()` — returns `None` with docstring noting callers needing SAT completion must use `FeatureModelOracle`
- `get_bg_data()` — returns `None` with docstring noting same restriction

These return values are explicit, documented, and intentional — not "missing" behavior.

---

## GroundTruthData Confirmation

`conacq/oracle/ground_truth.py` is already `class GroundTruthData` (dataclass, not Oracle subclass).

Caller audit confirms data-only usage:
- `conacq/eval/kb_comparator.py:96` — typed `oracle: GroundTruthData` (not Oracle)
- `conacq/eval/progressive_evaluation.py:107` — typed `groundtruth: GroundTruthData`
- `apps/run_evaluation.py:92` — `GroundTruthData.from_uvl(...)` then passed as `ground_truth=`
- `apps/run_compare.py:124/234` — `GroundTruthData.from_uvl(...)` then `.clause_set`, `.descriptions`, `.clauses` accessed directly

No Oracle-substitution assumption exists. No changes needed to callers.

---

## Safety-Net Tests Added

`tests/test_oracle_contract.py` — 31 tests covering:

- `TestCachedOracleCharacterization` (5): cache miss/hit, key order invariance, clear, ask-through-cache
- `TestCachedOracleSubstitutability` (6): full contract on CachedOracle — all 4 abstract methods + `ask` + `isinstance(Oracle)` — these 3 failed before fix, all 6 pass after
- `TestUserPromptOracleCharacterization` (6): creation, yes/no answers, retry-until-valid, query count, repr
- `TestUserPromptOracleSubstitutability` (6): full contract on UserPromptOracle — `get_variables` failed before fix, `get_bg_data` raised AttributeError before fix, all 6 pass after
- `TestGroundTruthDataIsNotOracle` (4): not subclass, not isinstance, no `is_valid`, no `ask`
- `TestGroundTruthDataCharacterization` (4): default construction, `__len__`, repr, `from_uvl` integration

---

## test_quacq.py update

`TestOracleABC.test_oracle_abc_minimal` asserted `abstract_methods == {'is_valid'}` — this was the stale single-method contract. Updated to `test_oracle_abc_contract` asserting the four-method unified contract. The assertion is now tighter and tests the real design intent.

---

## Files Modified

| File | Change |
|------|--------|
| `conacq/oracle/base.py` | Replaced stub-heavy ABC with 4-abstract-method unified contract; removed `pass` stubs |
| `conacq/oracle/cached.py` | Added `get_variables`, `complete_configuration`, `get_bg_data` delegation |
| `conacq/oracle/user_prompt.py` | Added `get_variables` (returns feature set), `complete_configuration` (returns None), `get_bg_data` (returns None) |
| `tests/test_oracle_contract.py` | New — 31 safety-net + substitutability tests |
| `tests/test_quacq.py` | Updated stale `test_oracle_abc_minimal` → `test_oracle_abc_contract` |

Not modified: `fm_oracle.py` (already conforms), `ground_truth.py` (data-only, confirmed correct), `bg_data.py` (no change needed), `__init__.py` (no change needed), eval/apps importers (confirmed data-only usage).

---

## Final Test Summary

```
468 passed, 1 warning in 52.79s
```

- Baseline: 437 passed, 1 warning
- After B3: 468 passed, 1 warning (+31 new oracle safety-net tests)
- Pre-existing warning: `TestSuiteReader` PytestCollectionWarning (unchanged)
- No regressions

---

## Deviations from Spec

None. All red-team adjustments applied:
- `get_variables` kept in contract (BINDING per spec)
- Delegation gap fixed in CachedOracle and UserPromptOracle
- GroundTruthData confirmed data-only (no change needed)
- Safety-net tests written BEFORE contract change (order respected)
- Substitutability tests assert REAL contract (not weakened)

---

**Status:** DONE  
**Summary:** Single Oracle ABC with 4 abstract methods derived from consumer audit; CachedOracle and UserPromptOracle now conform; GroundTruthData confirmed data-only; 31 safety-net tests added; full suite 468/468 green.  
**Concerns:** None.
