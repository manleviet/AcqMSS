# Independent audit — did `feat/redesign-abc-v2` drop any feature from `feat/redesign-abc` / `feat/phase-r-task-as-unit`?

**Method (read-only, no changes):** v2 is a rebuild-from-baseline, so compared at **symbol/behaviour** level, not commit level. For every `.py` present on an old branch but absent by path on v2 (`comm -23` of `git ls-tree`), extracted its top-level `class`/`def` and `git grep -w`'d each in the v2 tree; 0-hit-in-all-forms = candidate drop. Then for old-only **test** files, read what behaviour they pin and searched for the equivalent v2 assertion.

**Scope:** 38 old-only `.py` files (32 from `feat/redesign-abc`, 17 from `feat/phase-r-task-as-unit`, overlapping). Branch `.py` counts: redesign-abc 159, phase-r 130, **v2 176** (v2 has *more* files — old-only paths are overwhelmingly renames/reorgs).

---

## Real finding (1) — QuAcqRunner.run() characterisation is UNPINNED in v2

`tests/test_runners_characterization.py::TestQuAcqRunnerCharacterization` (old branch) pinned `QuAcqRunner.run()` end-to-end on REAL-FM-7 in **`example_only`** mode, `shuffle_seed=42` — **13 deterministic fields**: `n_bias=295`, **`n_kb=1`**, `n_queries=17`, `convergence_reason='pool_exhausted'`, `consistency_checks=17`, `is_consistent_calls=1996`, `quacq_calls=1`, `findscope_calls=15`, `findc_calls=1`, `dis_gen_calls=0`, `reduce_calls=…`.

**v2 has no equivalent.** `git grep QuAcqRunner tests/` → the only hit is a *docstring* in `test_quacq.py` (my B2 knob test). Meanwhile **`ConGenRunner` IS pinned** (`tests/test_t11_congen_runner_net.py`, "the T11 net layer that was never built"). So the two production runners are covered asymmetrically: ConGen's `run()` is netted, QuAcq's `run()` is not.

- v2 covers the QuAcq *algorithm* example paths only **structurally** (`test_quacq.py::test_example_only_works_without_discrim_gen`, `test_example_first_requires_discrim_gen`, `test_pool_exhausted_when_empty`) — "works / raises / exhausts", no value pins.
- **Why it matters now:** B2 (`quacq.py:140`, just landed) runs in example mode. The old `n_kb=1` example-mode characterisation would have caught a regression there; in v2 that path has **no fast net** — only the deferred `data/results/interactive` paper output (B1 bundle) exercises it.
- **Risk:** medium. Behaviour is not lost (QuAcqRunner exists and runs), but its example-mode output is silently unguarded at the fast-test layer.

## Real finding (2) — minor, lighter-not-dropped

| Old pin | v2 status | Assessment |
|---|---|---|
| `test_oracle_contract.py::TestUserPromptOracle{Characterization,Substitutability}` | v2 `test_oracle_protocols.py` pins UserPromptOracle **role** (inheritance) only, not behaviour | Lighter. UserPromptOracle is interactive I/O (low deterministic value). Low risk. |
| `test_io_base_roundtrip.py::TestExampleIORoundTrip` (write→read + on-disk format stable) | v2 exercises `ExampleIO` (reads) in test_congen/test_evaluation/e2e; no dedicated write→read roundtrip pin found (`test_bias_io.py` covers BiasIO) | Lighter. Examples are read-mostly inputs. Low risk. |
| `test_apps_harness.py::TestConfigLoader` (TOML load) | v2 splits harness coverage: `test_atomic_io.py` (writes) + `test_apps_logging.py` (logging); a TOML config-loader unit test specifically was not found | Lighter. Plumbing. Low risk. |

## Everything else = intentional exclusions or renames/relocations (NOT drops)

**Intentional exclusions (as instructed, confirmed 0-hit-by-design):**
`conacq/oracle/base.py` (fat Oracle ABC, ADR-0010) · `conacq/oracle/fm_data.py` (FMData, T11.4c) · `explanation/models/codec.py` (VariableCodec) · `explanation/operations/algorithms/executor.py` + `test_executor.py` (parallel executor, ADR-0014) · `pysat_conflict_sat4j.py` / `pysat_diagnosis_sat4j.py` (sat4j op clones, T3) · `conacq/runners/unified_result.py` (`UnifiedConGenResult` **rejected**, ADR-0008) · MappingProxyType (ADR-0007).

**Renames / relocations — all symbols present in v2:**
- `conacq/eval/config.py` → `conacq/config.py` (5/5 symbols) · `conacq/eval/performance_metrics.py` → `conacq/runners/metrics.py` (4/4) · `conacq/oracle/fm_oracle.py` + `fm_oracle_model.py` → `conacq/oracle/fm/oracle.py` (FMOracle/FMOracleModel present) · `conacq/oracle/oracle_task_data.py` → `conacq/oracle/oracle_data.py` (`OracleData`) · `explanation/operations/algorithms/checker.py` + `solver_backend.py` → `explanation/checker/{protocols,backend}.py`; the two old-name 0-hits are **T7 renames**: `_BackendConfig` → `SolverBackend`, `build_solver_backend` → `build_checker` (both present) · `profiler.py` + `profiler/*` → top-level `profiling/` package (all 13+ symbols present, T8/ADR-0003).
- Tests: `test_diagnosis.py` (`DiagnosisTest` monolith) → split per-algorithm files (T13; 9/10 symbols migrated) · `diagnosis_support.py::_skip_if_disabled` → `diagnosis_helpers._skip_disabled` (rename) · `test_bias_module*.py` → `scripts/*demo*` (T17) with real coverage now in `test_bias_io.py`.

**Refactored-not-dropped (behaviour preserved under a new shape):**
- `conacq/_io_base.py::JsonSerializationMixin` (T14 DRY mixin) — **not adopted in v2**; `BiasIO`/`ExampleIO` classes still exist and do JSON IO, and T10's `conacq/atomic_io.py` supersedes the boilerplate goal. Bias IO round-trip is tested (`test_bias_io.py`, T17 K=7). The mixin is an internal helper, not a user feature.
- `conacq/algorithms/oracle_aware_task_preparation.py::OracleAwareTaskPreparation` (`_copy_bg_data_part3/4`) — restructured into `OracleData`/`BGData` per-model preparation (ADR-0009: the oracle answers, does not provision). `conacq/oracle/bg_data.py` + `test_quacq.py::TestQuAcqTaskPart4` (`test_bgdata_part4_default_empty`) cover the Part-3/4 BG data. Behaviour preserved.

## Unresolved questions

1. **QuAcqRunner net** — do you want a `test_t11_quacq_runner_net.py` (mirror of the ConGen one) added to close finding (1)? It would pin QuAcqRunner.run() example-mode output (n_kb=1 etc.) — but its golden depends on B1+B2+B3, so it belongs with the B1 bundle regen at the ConGen revision, not now.
2. **T14 status** — was `JsonSerializationMixin`/`_io_base.py` intentionally superseded by `atomic_io.py` (T10), or is the DRY consolidation still a pending item? (Not a drop either way; flagging for the roadmap.)
3. Minor gaps (UserPromptOracle behaviour, ExampleIO roundtrip, ConfigLoader unit) — accept as-is (low risk), or track for a coverage top-up?
