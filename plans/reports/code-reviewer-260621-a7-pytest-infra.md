# A7 Pytest-Infra Refactor — Code Review

Branch: feat/redesign-abc | Scope: test infra (Stage A7) | Reviewer: code-reviewer
Suite: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q` → **352 passed, 1 warning** (= baseline). Only remaining warning is the known `TestSuiteReader` PytestCollectionWarning. `slow`-marker warning GONE.

## Verdict: PASS (with 1 out-of-scope flag)

All 5 acceptance criteria met. All inviolable assertion/fixture/import constraints upheld. One real constraint violation: a non-test code change rode along in the working tree (see HIGH-1). It is behaviorally equivalent + tests green, but it is outside A7 scope and must be separated.

---

## Findings by severity

### HIGH
**HIGH-1 — Out-of-scope non-test change in working tree** — `conacq/oracle/fm_oracle.py:170-178`
- A7 constraint: "only pyproject + tests + moved demos should change." But `fm_oracle.py::_model_to_config` was rewritten from an inline dict-comp to `self._base_task.codec.model_to_config(model)`.
- Behavioral analysis: **equivalent**. Old `{name: fid in model for name,fid in variables.items()}` vs codec's `for lit in model: if abs(lit) in id_to_name: config[name]=lit>0`. `id_to_name` is the exact inverse of `variables` (`fm_oracle_model.py:81`), and `get_model()` returns a complete assignment, so identical key set + values. `_base_task.codec` always populated (`__init__` line 59; already used at `is_valid` line 104) → no new AttributeError path. Suite green confirms.
- Risk: low correctness risk, but it pollutes the A7 commit and breaks the "no non-test behavior change" gate.
- Fix: `git restore conacq/oracle/fm_oracle.py` from the A7 staging set; land it as its own DRY-codec refactor commit (with its own review), OR explicitly re-scope A7 to include it. Do not bundle silently.

### MEDIUM
None.

### LOW
**LOW-1 — Unused import** — `tests/test_quacq.py:11` `from conacq.bias import BiasIO`
- Was used only by the removed per-file `bias` fixture (now in conftest). No other reference in the file. Harmless (won't break), but dead. Remove it. (`FeatureModelOracle` import is still used at line 249 — keep.)

---

## Acceptance criteria — verification
1. ✅ `tests/conftest.py` + `tests/resource_paths.py` exist and are consumed (conftest `bias`/`oracle` used in test_quacq L48/114, test_congen L69/113/158; `resource_paths` imported by test_congen/quacq/evaluation/executor).
2. ✅ test_utils + test_executor migrated; no `unittest.TestCase` / `unittest` base remains; `__main__`+`unittest.main()` blocks removed.
3. ✅ Resource paths defined once in `resource_paths.py`. Only remaining per-file copy is `test_diagnosis.py:160-164` (`TEST_DIR`/`RESOURCES_DIR`/`class Resources`) — the intentionally-deferred one. OK.
4. ✅ Demos moved out of `tests/` → `scripts/bias_module_demo.py`, `scripts/bias_generation_quickstart.py`. Both contain **0 asserts** → no coverage lost. Old paths `git rm`'d.
5. ✅ `slow` marker registered in `pyproject.toml [tool.pytest.ini_options]`; applied at `test_quacq.py:239`; warning no longer emitted.

## Inviolable constraints — verification
- ✅ **No weakened assertions.** Full audit of test_utils.py + test_executor.py diffs:
  - `assertEqual(a,b)`→`assert a==b`; `assertTrue(x[,msg])`→`assert x[, msg]`; `assertGreater(a,b)`→`assert a>b`; `assertIsNot`→`assert is not`; `assertIn/NotIn`→`assert in / not in`. All semantically equal.
  - `assertEqual(True, fn(...))`→`assert fn(...) is True`: STRICTER, not weaker. Verified return types are real bools (`utils.py`: `any()`/`all()`; `_CountingExecutor.is_consistent` returns `(sum%2)==0`). No coverage lost.
  - No assertion dropped; counts match (e.g., test_executor parity test keeps both `s_sat==p_sat` and `s_model==p_model`).
- ⚠️ **No non-test behavior change** — violated by HIGH-1 (equivalent but out-of-scope).
- ✅ **Fixtures identical.** conftest `bias`/`oracle` byte-for-byte match the removed per-file fixtures (same skip-guard, same `str(PATH)`, same loader).
- ✅ **Imports resolve.** Full suite collected + passed → `from tests.resource_paths import ...` and conftest fixture injection all resolve under new `testpaths=["tests"]`.

## ALSO-CHECK items
- ✅ Old module-level constants (FM_PATH/BIAS_PATH/EXAMPLES_*/RESULT_PATH/MODELS) all re-resolved via `from tests.resource_paths import ...` in congen/quacq/evaluation.
- ✅ `TestOracleFeatureIds` `MODELS` now absolute paths (`str(DATA_DIR/...)`) vs old relative `"data/fms/..."`. `Path(fm_path).exists()`, `UVLReader(fm_path)`, `FeatureModelOracle(fm_path)`, `BiasIO.load_from_json(bias_path)` all accept absolute strings → MORE robust (CWD-independent). Both parametrized tests pass.
- ⚠️ Leftover unused import: LOW-1 (`BiasIO` in test_quacq). `Path` correctly removed from quacq/evaluation; correctly KEPT in test_congen (used L374/388).

## Pre-existing (not A7)
- `test_executor.py::TestProcessExecutorParity::test_consistency_check_count_parity` — known intermittent serial==parallel `is_consistent_calls` race. Did not trigger this run (352/352). A7 untouched executor logic. Noted as pre-existing flakiness, not an A7 defect.

## Unresolved questions
1. Is `fm_oracle.py` codec delegation intended to be part of A7, or did it leak from a parallel branch? Recommend separating into its own commit before committing A7.
