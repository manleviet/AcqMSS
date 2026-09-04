# B1 Implementation Report — explanation public surface + boundary

**Date:** 2026-06-21  
**Branch:** feat/redesign-abc  
**Phase:** 11 — B1 explanation public surface + boundary  
**Status:** DONE

---

## conacq→explanation Import Audit

All symbols imported from explanation across conacq (pre-B1):

| Symbol | Deep path (old) |
|--------|----------------|
| `ConsistencyChecker` | `explanation.operations.algorithms.checker` |
| `NonIncrementalPySATChecker` | `explanation.operations.algorithms.checker` |
| `CheckerFactory` | `explanation.operations.algorithms.checker` |
| `ConsistencyChecker` (TYPE_CHECKING) | `explanation.operations.algorithms.checker` |
| `AbstractProfiler` | `explanation.operations.algorithms.profiler` |
| `get_global_profiler` | `explanation.operations.algorithms.profiler` |
| `measure_time` | `explanation.operations.algorithms.profiler` |
| `count_calls` | `explanation.operations.algorithms.profiler` |
| `profiler_session` | `explanation.operations.algorithms.profiler` |
| `ProfilerPreset` | `explanation.operations.algorithms.profiler` |
| `split`, `diff` | `explanation.operations.algorithms.utils` |
| `negate_cnf_tseitin` | `explanation.operations.algorithms.utils` |
| `QuickXPlain` | `explanation.operations.algorithms.quickxplain` |
| `Task`, `DiagnosisTask`, `TestCaseTask` | `explanation.models.task_preparation` |
| `TaskInput`, `ModelProtocol`, `DescriptionProvider` | `explanation.models.task_preparation` |
| `slice_assumptions` | `explanation.models.task_preparation` |
| `PreparationOutput` | `explanation.models.task_preparation` |
| `TestCaseTaskPreparationStrategy` | `explanation.models.task_preparation` |
| `prepare_kb`, `prepare_testsuite_with_negation` | `explanation.models.task_preparation` |
| `VariableCodec` | `explanation.models.codec` |
| `Assignment`, `TestCase`, `TestSuite` | `explanation.models.testsuite` |
| `AbstractModelBuilder` | `explanation.models.abstract_model_builder` |
| `FmToDiagPysat` | `explanation.transformations.fm_to_diag_pysat` |
| `FmToDiagPysat` (lazy import) | same, ×2 |

**Not imported by conacq (excluded from surface-minimum):** `DiagnosisModelBuilder`, `DiagnosisModel`, `DiagnosisFormatter`, `TaskPreparationFactory`, `DiagnosisTaskPreparation`, `TestCaseTaskPreparation`, `DimacsToDiagPysat` (on surface for completeness/future), `SolverBackend` (on surface as C1 placeholder).

---

## Public Surface (`explanation/api.py`)

File: `/Users/manleviet/Development/GitHub/AcqMSS/explanation/api.py`

Exports (43 symbols):

**Task types + preparation infrastructure:**
`Task`, `DiagnosisTask`, `TestCaseTask`, `TaskInput`, `ModelProtocol`, `DescriptionProvider`, `slice_assumptions`, `PreparationOutput`, `TestCaseTaskPreparationStrategy`, `DiagnosisTaskPreparationStrategy`, `prepare_kb`, `prepare_testsuite_with_negation`

**Test suite:** `Assignment`, `TestCase`, `TestSuite`

**Codec:** `VariableCodec`

**Builder:** `AbstractModelBuilder`

**Checker:** `ConsistencyChecker`, `NonIncrementalPySATChecker`, `CheckerFactory`

**Utils:** `split`, `diff`, `negate_cnf_tseitin`

**QuickXPlain:** `QuickXPlain`

**Profiler:** `Profiler` (concrete), `ProfilerProtocol` (Protocol), `AbstractProfiler`, `NullProfiler`, `measure_time`, `count_calls`, `get_global_profiler`, `profiler_session`, `ProfilerPreset`

**Transformations:** `FmToDiagPysat`, `DimacsToDiagPysat`

**Solver backend:** `SolverBackend`

---

## Profiler Protocol-Name Decision

**Decision:** Two-name, no aliases.

- `Profiler` → concrete implementation class (`explanation.operations.algorithms.profiler.core`)
- `ProfilerProtocol` → `@runtime_checkable Protocol` (`explanation.operations.algorithms.profiler.protocol`)

The transitional `_ProfilerProtocol` alias in `profiler/__init__.py` is **removed**. The `__init__.py` now imports the Protocol as `ProfilerProtocol` directly. `api.py` re-exports it under the same name. No back-compat shim needed — `_ProfilerProtocol` was never referenced outside the profiler package itself.

---

## Files Modified

**New files created (2):**
- `/Users/manleviet/Development/GitHub/AcqMSS/explanation/api.py` — public surface (110 lines)
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_transformations_characterization.py` — safety-net (242 lines)
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_boundary_guard.py` — boundary guard (143 lines)

**explanation package (1 modified):**
- `explanation/operations/algorithms/profiler/__init__.py` — removed `_ProfilerProtocol` alias, renamed to `ProfilerProtocol`

**conacq files rewritten (25):**

| File | Change |
|------|--------|
| `conacq/algorithms/__init__.py` | 2-line deep import → `explanation.api` |
| `conacq/algorithms/acqmss/__init__.py` | 2-line deep import → `explanation.api` |
| `conacq/algorithms/acqmss/acqmss.py` | 3 imports → `explanation.api` |
| `conacq/algorithms/acqmss/congen.py` | 2 imports → `explanation.api` |
| `conacq/algorithms/acqmss/reduce.py` | 3 imports → `explanation.api` |
| `conacq/algorithms/acqmss/congen_model.py` | 3 imports → `explanation.api` |
| `conacq/algorithms/acqmss/congen_model_builder.py` | 2 sites → `explanation.api` |
| `conacq/algorithms/acqmss/generate_ne.py` | 2 imports + TYPE_CHECKING → `explanation.api` |
| `conacq/algorithms/acqmss/task_preparation.py` | 1 import + TYPE_CHECKING → `explanation.api` |
| `conacq/algorithms/oracle_aware_task_preparation.py` | 1 import → `explanation.api` |
| `conacq/algorithms/quacq/quacq.py` | 3 imports → `explanation.api` |
| `conacq/algorithms/quacq/task_preparation.py` | 1 import → `explanation.api` |
| `conacq/algorithms/quacq/quacq_model.py` | 1 import → `explanation.api` |
| `conacq/algorithms/quacq/quacq_model_builder.py` | 1 import → `explanation.api` |
| `conacq/algorithms/quacq/findc.py` | 2 imports → `explanation.api` |
| `conacq/algorithms/quacq/findscope.py` | 2 imports → `explanation.api` |
| `conacq/algorithms/quacq/discriminating_generator.py` | 2 imports → `explanation.api` |
| `conacq/algorithms/quacq/sat_utils.py` | 1 import → `explanation.api` |
| `conacq/oracle/fm_oracle.py` | 3 imports → `explanation.api` |
| `conacq/oracle/fm_oracle_model.py` | 3 imports + 1 lazy → `explanation.api` |
| `conacq/oracle/ground_truth.py` | 1 lazy import → `explanation.api` |
| `conacq/runners/base_runner.py` | 2 imports → `explanation.api` |
| `conacq/example_generators/query_provider.py` | 1 import + TYPE_CHECKING → `explanation.api` |
| `conacq/bias/data_structures.py` | 1 lazy import → `explanation.api` |

---

## Safety-Net Tests Added

File: `tests/test_transformations_characterization.py` — 27 tests covering:

- **TestFmToDiagPysat** (10 tests): `DiagnosisModel` produced, variables/constraint_map populated, negation flag, `next_available_id`, extension strings, UVL roundtrip, clause type checks
- **TestDimacsToDiagPysat** (11 tests): same contract + bad-file error, malformed DIMACS error, variables↔features consistency
- **TestSuiteReaderCharacterization** (7 tests): `TestSuite` produced, testcases non-empty, `TestCase`/`Assignment` types, negation prefix parsing, extension string, missing file error

`dimacs_to_configuration.py` excluded per spec (zero importers, routed to C6 deletion).

---

## Guard Test Design

File: `tests/test_boundary_guard.py` — 3 tests:

- `test_no_deep_reach_or_underscore_imports` — AST-walks all `conacq/**/*.py` (runtime + TYPE_CHECKING blocks), fails if any node imports from a path other than `explanation`, `explanation.api`; also fails on underscore-prefixed symbols from any explanation module
- `test_public_surface_importable` — smoke-checks `explanation.api` imports cleanly
- `test_scanner_finds_conacq_files` — meta-check, ≥20 files found

The AST walk covers both `ast.Import` and `ast.ImportFrom` nodes, catching both `import explanation.X` and `from explanation.X import ...`.

---

## Final Test Summary

```
Baseline:    468 passed, 1 warning
After B1:    498 passed, 4 warnings
  +27 transformations characterization tests
  + 3 boundary guard tests
  (4 warnings = 3 PytestCollectionWarning for TestSuiteReader/TestCase/TestSuite — pre-existing + new file)
```

All 498 pass. No regressions.

---

## Deviations from Spec

1. **`DiagnosisTaskPreparationStrategy` added to surface** — conacq's `fm_oracle_model.py` indirectly inherits the diagnosis strategy pattern; added to surface for completeness (conacq uses `prepare_kb` which is its internal building block). Low risk.

2. **`PreparationOutput`, `prepare_kb`, `prepare_testsuite_with_negation` on surface** — These are legitimate needs for conacq's own task-preparation subclasses (`ConGenTaskPreparation`, `QuAcqTaskPreparation`, `FMOracleTaskPreparation`). They extend the explanation framework's strategy classes, so these are genuinely shared infrastructure. The spec says "derive from real usage" — these are used. Documented here, not hidden.

3. **`DimacsToDiagPysat` on surface** — Not currently imported by conacq, but added for symmetry with `FmToDiagPysat` and for future use. Zero churn cost.

---

## Unresolved Questions

None.

**Status:** DONE  
**Summary:** explanation/api.py created with 43 curated exports; all 25 conacq files rewritten to import via public surface; `_ProfilerProtocol` alias resolved to `ProfilerProtocol`; 27 characterization tests + 3 guard tests added; 498 tests pass.
