# Code Review — B3 Unify Oracle Contract

Date: 2026-06-21
Branch: feat/redesign-abc
Scope: uncommitted working-tree changes + new `tests/test_oracle_contract.py`
Reviewer: code-reviewer

## Scope
- Files: `conacq/oracle/base.py`, `conacq/oracle/cached.py`, `conacq/oracle/user_prompt.py`, `tests/test_quacq.py` (modified); `tests/test_oracle_contract.py` (new)
- LOC: +158 / -37 across modified files; new test ~301 LOC
- Focus: working-tree diff only; prior committed stages out of scope

## Overall Assessment
Clean, well-scoped change. The unified `Oracle` ABC is derived from a real consumer call-site audit (verified below), not invented. All concrete oracles implement the full contract, the 468-test suite is green, and the new substitutability tests assert real behavior that would have failed pre-fix. No behavior change to the caching path. No plan-stage labels in code. PASS.

## Verification Results

### (1) Contract derived from REAL usage — VERIFIED
Every abstract method has a consumer calling it on an oracle-typed object:

| Method | Consumer call-sites (grep-verified) |
|--------|-------------------------------------|
| `is_valid` | quacq.py:203, findc.py:125, findscope.py:63, example_generators base.py:54, random_sampling.py:143/269, feature_frequency.py:111 |
| `ask` (concrete alias) | quacq.py doc + interactive path (delegates to is_valid) |
| `get_variables` | example_generators/base.py:34, apps/generate_examples.py:134, fm_oracle.py:117 |
| `complete_configuration` | example_generators/base.py:76, feature_frequency.py:198/200 |
| `get_bg_data` | acqmss/task_preparation.py:95, quacq/task_preparation.py:104, quacq/quacq_model.py:71 |

- No over-specification: all 4 methods have at least one non-test, non-self consumer.
- No under-specification: methods consumers call only on `FeatureModelOracle`-typed objects (`get_kb`, `get_assumptions`, `get_c`, `get_root_clauses`, `cleanup`) are correctly left OFF the ABC and documented in the base.py module docstring (base.py:16-19).
- `get_variables` correctly KEPT (per red-team binding decision): consumed by ExampleGenerator.base:34 + apps/generate_examples.py:134.

**Verdict (1) contract-correctness: PASS.**

### (2) No broken substitution — VERIFIED
Making 4 methods abstract means every concrete `Oracle` must implement all 4 or instantiation raises `TypeError`. Confirmed:
- `FeatureModelOracle` (fm_oracle.py): is_valid:84, get_bg_data:124, get_variables:128, complete_configuration:136 — already had all 4, inherits `ask`. No change needed; no regression.
- `CachedOracle` (cached.py): now implements get_variables:67, complete_configuration:71, get_bg_data:77 (delegating); is_valid:45 (cached); inherits `ask`.
- `UserPromptOracle` (user_prompt.py): get_variables:90, complete_configuration:97, get_bg_data:111; is_valid existing; inherits `ask`.
- Construction sites: `UserPromptOracle` at quacq_runner.py:352, `CachedOracle` via `CachedOracle(base_oracle)`. Both instantiate cleanly (full suite green proves no TypeError).
- Full suite: 468 passed, 1 warning (known `TestSuiteReader` PytestCollectionWarning). No flaky failure this run.

**Verdict (2) no-broken-substitution: PASS.**

### (3) CachedOracle delegation correctness — VERIFIED
- get_variables/complete_configuration/get_bg_data forward to `self.base_oracle.<method>(...)` and return the result unchanged (cached.py:67-79). Transparent — no caching, no transformation.
- `is_valid` caching control flow UNCHANGED: key build → hit (`_cache_hits++`, return) → miss (`_cache_misses++`, query base, store, return) (cached.py:54-63). Diff shows only docstring/comment edits around it, no logic change.

### (4) Stale-test update is a strengthening, NOT a weakening — VERIFIED
`test_quacq.py`: old `test_oracle_abc_minimal` asserted `abstract_methods == {'is_valid'}`; new `test_oracle_abc_contract` asserts the 4-method set. This matches the actual `Oracle.__abstractmethods__` now (is_valid, get_variables, complete_configuration, get_bg_data) — confirmed against base.py `@abstractmethod` decorators (lines 37, 52, 61, 75). Strengthened assertion reflecting the real contract; not loosened.

### (5) Substitutability tests are real — VERIFIED
- `TestCachedOracleSubstitutability` calls the full contract on a `CachedOracle` wrapping `_StubOracle`. `test_get_variables_conforms` asserts `== self.stub.get_variables()`; `test_complete_configuration_conforms` asserts `== self.stub.complete_configuration(partial)`; `test_get_bg_data_conforms` asserts `is self.stub.get_bg_data()` (identity — meaningful, the stub returns the same object). These would have failed pre-fix: `CachedOracle` lacked the methods, so under the new ABC it could not even instantiate (TypeError on abstract methods).
- `TestUserPromptOracleSubstitutability` asserts get_variables == declared set, complete_configuration is None, get_bg_data is None — documents the SAT-less restriction as behavior, not a skip.
- Tests are non-trivial: they exercise actual return values, not just `hasattr`.

### (6) Hygiene — VERIFIED
- No plan-stage labels (B3 / phase-09 / finding codes / audit labels) in any changed code or test file (grep clean).
- conacq-scope: all changes under `conacq/oracle/` + tests. No explanation-side edits.
- `GroundTruthData` (ground_truth.py:14) remains data-only: methods are only `from_uvl`, `__len__`, `__repr__`. Not an Oracle subclass; new test class `TestGroundTruthDataIsNotOracle` locks this (not issubclass, not isinstance, no is_valid, no ask).

## Findings by Severity

### Critical
None.

### High
None.

### Medium
None.

### Low
1. **`get_variables` return-type semantics drift (documentation-only).** base.py:53 types `get_variables() -> Optional[Set[str]]` and the docstring says it MAY return None "if the oracle has no feature catalogue (e.g. UserPromptOracle in standalone mode)." But `UserPromptOracle.get_variables()` (user_prompt.py:90) and `FeatureModelOracle` both return a non-None set; `CachedOracle` delegates. So no conformer actually returns None. Meanwhile `ExampleGenerator.__init__` (base.py:34) and apps/generate_examples.py:134 (`len(oracle.get_variables())`) assume non-None — a None would crash `len()`. The `Optional` is therefore wider than reality and slightly misleading vs. `complete_configuration`/`get_bg_data` where None is a genuine path. Not a bug (no conformer returns None), but consider narrowing to `Set[str]` for `get_variables` to match the actual contract, or keep `Optional` and have ExampleGenerator guard None. No action required for B3 correctness.

2. **`_StubOracle` lives in the test module (fine), but note it is the de-facto SAT-free FeatureModelOracle stand-in.** If future stages add a 5th contract method, this stub must be updated or unrelated tests using it will fail at instantiation. Low-risk maintenance note, no change needed now.

## Positive Observations
- Module docstrings in base.py enumerate the contract WITH the audited call-sites — excellent traceability without plan-label coupling.
- Section comments (`# --- Oracle ABC: ... ---`) in cached.py/user_prompt.py make the contract surface scannable.
- Safety-net-first discipline honored: characterization tests for previously-untested cached/user_prompt/ground_truth modules added alongside substitutability tests.
- Identity assertion (`bg is self.stub.get_bg_data()`) for delegation is a sharper test than equality — proves pass-through, not reconstruction.

## Metrics
- Full suite: 468 passed, 1 warning (known), 0 failed
- New tests: 31 in test_oracle_contract.py (all pass)
- Contract methods: 4 abstract + 1 concrete alias, all consumer-backed
- Plan-label leakage: 0
- Type coverage on changed files: full type hints present on all new/changed method signatures

## Recommended Actions
1. (Low, optional) Decide `get_variables` nullability: narrow to `Set[str]` OR add None-guard in ExampleGenerator.__init__. Defer to a later stage — not blocking.
2. None blocking for B3.

## Verdict
- Contract-correctness (1): PASS
- No-broken-substitution (2): PASS
- **B3: PASS**

## Unresolved Questions
- `get_variables -> Optional[Set[str]]` advertises a None return that no conformer produces and two consumers would crash on (`len(None)`). Intended as forward-compat slack, or should it be `Set[str]`? (Low priority — flagging for the lead's call, not blocking the commit.)
