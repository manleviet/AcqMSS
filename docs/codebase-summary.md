# AcqMSS Codebase Summary

**Total Python Code**: ~21,800 lines across ~102 files
**Main Packages**: conacq (~10,000 LOC) + explanation (~5,000 LOC) + apps (~3,025 LOC) + tests (~3,745 LOC)
**Last Updated**: 2026-07-18 (T18 docs-coherence: CheckerFactory removal, prepare_task unification, executor deferred to canonical repo)

## Package Structure

### conacq/ — Constraint Acquisition Algorithms (~9,900 LOC)

Core acquisition logic organized into seven sub-packages:

#### conacq/algorithms/ — Acquisition Algorithms (~2,845 LOC, 16 files)

Primary constraint discovery algorithms:

| File | LOC | Purpose |
|------|-----|---------|
| `congen.py` | 149 | ConGen orchestration (direct params, no task object) |
| `acqmss.py` | 104 | ACQMSS: divide-and-conquer MSS finding |
| `reduce.py` | 104 | REDUCE: redundancy elimination via consistency checking |
| `acqmss/generate_ne.py` | 138 | GenerateNE: pure negated example generation (returns clauses, no mutation) |
| `task_preparation.py` | 233 | Task hierarchy + ConGenTaskPreparation strategy (calls GenerateNE internally) |
| `congen_model.py` | 89 | Immutable KB container; `prepare_task(task_input) → PreparedTask` (pure per-call; stores no task/describe/solver-mode state) |
| `congen_model_builder.py` | 32 | Fluent builder; subclasses `OracleBiasModelBuilder`, adds example handling + the two model hooks |
| (Total: 1,331 LOC for main algorithms) |
| (Subtotal: 1,439 LOC including both paradigm-specific builders) |

**QuAcq Sub-package** (`quacq/`, 9 files, ~1,066 LOC):

**Assumption-Based Learning (Unified with ConGen, Paper-Aligned Queries, DI Pattern)**:

| File | LOC | Purpose |
|------|-----|---------|
| `quacq.py` | 262 | QuAcq algorithm + QuAcqResult (DI pattern, mode dispatch, direct param learn()) |
| `sat_utils.py` | 52 | Standalone SAT utilities for QuAcq: constraint filtering, scope matching, assumption conversion, consistency pruning |
| `quacq_model.py` | 97 | QuAcqModel: dual to ConGenModel for interactive learning. Stores negated_constraint_map + next_available_id (computed at build time). |
| `quacq_model_builder.py` | 37 | QuAcqModelBuilder: subclasses `OracleBiasModelBuilder`; supplies `_create_model_instance`/`_post_negation_build` hooks (solver mode + BG assignment maps + auto-prepare). |
| `task_preparation.py` | 103 | QuAcqTask + QuAcqTaskPreparation: pure data container + preparation |
| `findc.py` | 138 | FindC (IJCAI13 Algorithm 3): oracle.is_valid() + DiscriminatingGenerator(C_L[Y]) |
| `findscope.py` | 84 | FindScope (IJCAI13 Algorithm 2): oracle.is_valid() partial queries, no SAT |
| `discriminating_generator.py` | 65 | DiscriminatingGenerator: Paper Algorithm 3 line 5, C_L[Y] + BG, not FM |
| `__init__.py` | 73 | Package exports |

**Changes (This Session - QuAcqTask Cleanup + DI Refactor - commits 260228-e2b68c8)**:
- ✅ **Cleaned QuAcqTask** — Removed 7 dead methods (~80 LOC), now pure data container (fields only)
- ✅ **Moved behavior to sat_utils.py** — Shared SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses, prune_rejecting, constraint scope matching
- ✅ **Removed DescriptionProvider** from QuAcq.learn() — Moved to runner layer (QuAcqRunner.resolve_kb())
- ✅ Refactored `QuAcq.__init__()` — DI pattern (oracle, query_provider, discriminating_generator, profiler)
- ✅ Added `QuAcq.for_oracle()` factory — discrim_gen required
- ✅ Added `QuAcq.for_examples()` factory — query_provider required
- ✅ Refactored `QuAcq.learn()` — Direct parameter signature (set_c, set_b, ..., mode, max_queries); runner resolves names
- ✅ learn() supports 3 modes: 'oracle', 'example_only', 'example_first' via single parameter

**Previous Session Changes (FindScope/FindC Refactoring - commit 260227)**:
- ✅ Added `discriminating_generator.py` — DiscriminatingGenerator (Paper Algorithm 3 line 5)
- ✅ Updated `findscope.py` — oracle.is_valid() instead of SAT-based consistency check
- ✅ Updated `findc.py` — Pool-based narrowing via oracle.is_valid()

**Previous Session Changes**:
- ✅ Merged `QuAcqTaskPreparation` into `task_preparation.py` (was `quacq_task.py`, renamed)
- ✅ Merged `QuAcqResult` into `quacq.py` (deleted `result.py`)
- ✅ Deleted `task.py` (`InteractiveTask`) — use `QuAcqTask` (assumes int IDs)
- ✅ Deleted `learner.py` (`InteractiveLearner`) — use `QuAcqModelBuilder` path
- ✅ Removed `_task_compat.py` (module deleted, functionality moved to sat_utils.py - commit 84e1c11)

#### conacq/bias/ — Bias (Constraint) Generation (~1,176 LOC, 6 files)

Feature model to constraint conversion pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `bias_generator.py` | 275 | Extract constraints from feature model (hierarchical + cross-tree) |
| `bias_io.py` | 222 | JSON/YAML I/O for constraints and configurations |
| `config_loader.py` | 203 | TOML/YAML configuration loading for bias generation |
| `clause_generator.py` | 199 | Convert FM constraints to CNF clauses |
| `data_structures.py` | 239 | Constraint, BiasConfig, ConstraintType enumerations |

#### conacq/example_generators/ — Example & Query Generation (~935 LOC, 6 files)

Sampling strategies and query generation for learning:

| File | LOC | Purpose |
|------|-----|---------|
| `query_provider.py` | 160 | QueryProvider: unified query/example provision (strategies: generate_from_pool, generate_from_sat, generate) |
| `random_sampling.py` | 284 | RS sampling: uniformly random configuration selection |
| `feature_frequency.py` | 279 | FF: feature frequency-based sampling. Calls oracle.complete_configuration() |
| `nwise_coverage.py` | 104 | 2-COV strategy: n-wise pairwise coverage |
| `base.py` | 80 | Base strategy class. Calls oracle.complete_configuration() (no pysat.solvers imports) |
| `__init__.py` | ~1 | Package exports with QueryProvider |

#### conacq/examples/ — Example and Query History Conversion (~470 LOC, 4 files)

Utilities for converting query histories and managing example formats:

| File | LOC | Purpose |
|------|-----|---------|
| `data_structures.py` | 214 | Example, ExampleSet, ExampleType dataclasses |
| `io_utils.py` | 150 | I/O utilities for example persistence |
| `query_converter.py` | 63 | Convert QuAcqRunner query_history to ExampleSet or assignment lists for ConGen |
| `__init__.py` | ~1 | Package exports |

**Oracle Sub-package** (`conacq/oracle/`, 13 files, ~1,090 LOC; role-protocol design ADR-0009/0010):

| File | LOC | Purpose |
|------|-----|---------|
| `protocols.py` | 115 | Narrow role protocols (ADR-0009/0010): `MembershipOracle`/`CompletableOracle`/`CatalogProvider`/`BGProvider`/`KBProvider`/`GeneratorOracle` — `@runtime_checkable` roles carving the oracle surface; every member is `@abstractmethod`. No fat `Oracle` base (the old stub-owning class is gone). |
| `oracle_data.py` | 77 | `OracleData`: frozen provisioning snapshot (ADR-0009/0012) built once from the oracle model; satisfies `BGProvider`+`KBProvider` so consumers (`GenerateNE`, builders, task-prep) receive a snapshot, not the live oracle. |
| `ground_truth.py` | 71 | `GroundTruthData`: extracts constraint descriptions + CNF clauses from the FM directly (no full oracle) — eval-side ground truth (oracle→ground_truth rename, T17). |
| `bg_data.py` | 52 | `BGData`: frozen dataclass for the background-knowledge root constraint + negation pair; extracted post-preparation for ConGen assumption-ID allocation without overlap. |
| `constraint_description.py` | 129 | CTC description extraction from FM (requires/excludes/hierarchical). |
| `user_prompt.py` | 90 | `UserPromptOracle`: interactive membership oracle (implements `is_valid()`/`ask()` only). |
| `cached.py` | 77 | `CachedOracle`: transparent caching wrapper; caches `is_valid()`, delegates the rest to the base oracle. |
| `fm/oracle.py` | 170 | `FMOracle(MembershipOracle, CompletableOracle, CatalogProvider)`: loads a `.uvl` file → CNF, validates configurations via a persistent PySAT solver. |
| `fm/model.py` | 46 | `FMOracleModel`: assumption-guarded FM clauses (pure KB). Exposes `bg_data` property + `get_bg_data()` for ConGen to extract the root BG constraint. |
| `fm/builder.py` | 62 | `FMOracleModelBuilder(AbstractModelBuilder[FMOracleModel])`: loads an FM file into the immutable FM KB (T6); built through the `explanation.api` template. |
| `fm/task_preparation.py` | 126 | `FMOracleTaskPreparation`: FM oracle task-prep (prep strategies merged in T11b; no "OracleAware" mixin). |
| `__init__.py` | 49 | Package exports |

**Critical Implementation Details**:

1. **Oracle roles (no fat ABC)**: The old fat `Oracle` ABC is gone (ADR-0010). `conacq/oracle/protocols.py` declares narrow `@runtime_checkable` role protocols — `MembershipOracle` (`is_valid`), `CompletableOracle` (`complete_configuration`), `CatalogProvider` (`get_variables`/`get_variable_ids`), plus `BGProvider`/`KBProvider` (provisioning) — and each oracle DECLARES the roles it plays by inheriting them. `conacq.oracle` exports no single `Oracle` base.

2. **Provisioning snapshots (`OracleData`/`BGData`)**: An oracle *answers* (`is_valid`/`complete_configuration`) but does not *provision* (ADR-0009). Provisioning is extracted into frozen values built once: `OracleData` (a `KBProvider`+`BGProvider` snapshot handed to `GenerateNE`, the builders, and task-prep) and `BGData` (root constraint + negation pair). Being frozen, no membership query can shift them.

3. **`FMOracle` (feature-model oracle)**: implements `MembershipOracle`+`CompletableOracle`+`CatalogProvider` — public methods `is_valid()`, `complete_configuration()`, `get_variables()`/`get_variable_ids()`, `cleanup()`. Loads a `.uvl` file → CNF and validates configurations via a persistent PySAT solver; the assumption-guarded FM KB lives on `FMOracleModel`.

4. **`FMOracleModel`**: FM clauses in `set_kb` with assumption-guarded feature assignments; prepared via `FMOracleTaskPreparation` (prep strategies merged, T11b). Exposes the `bg_data` property for root-constraint extraction.

5. **Feature ID Consistency**: Uses flamapy's variable mapping (tree traversal order) from `FmToPysat.variables`. Ensures feature_ids match SAT variable IDs in CNF clauses.

6. **GenerateNE**: `GenerateNE.generate() → List[NEPerTestcase]` (pure) — activates QuickXPlain once per e- to find minimal conflicts, then negates them into NE constraints. Runs during ConGen `prepare_task`; returns clauses and the caller extends its own KB copy (no mutation).

7. **Builder Pattern**: `ConGenModelBuilder` requires an oracle for build-time negation; `build()` returns an immutable KB. Call `model.prepare_task(task_input)` per fold — pure and single-arg (the oracle's frozen snapshot is carried inside `task_input`).

8. **Assumption-Based Representation**: All checkers use identical assumption-based data (no `if is_incremental` branching in algorithms).

#### conacq/runners/ — Execution Runners (~480 LOC, 4 files)

Pipeline runners with unified lifecycle (build-once/run-many/cleanup-once):

| File | LOC | Purpose |
|------|-----|---------|
| `base_runner.py` | ~95 | BaseRunner ABC + BaseRunResult (shared fields + `metrics: RunMetrics`) |
| `congen_runner.py` | ~200 | ConGenRunner: CONGEN pipeline with profiling + bias shuffle seed support |
| `quacq_runner.py` | ~350 | QuAcqRunner: QuAcq dual-mode (oracle + example modes) |
| `metrics.py` | ~200 | **Metric declaration + reduction** (ADR-0006, moved out of `eval/`): `Kind`/`MetricSpec` + disjoint `CONGEN_METRICS`/`QUACQ_METRICS` tables + `RunMetrics` (dict-backed, `to_dict` derived from spec) + `collect(profiler, spec)` + generic `aggregate(runs)` reducer (~40 LOC replacing ~365 hand-written). A runner's output, not a run's evaluation — so it lives here, killing the old `runners→eval` cycle |
| `__init__.py` | ~18 | Package exports |

**BaseRunner Architecture** (NEW):
- ABC defining lifecycle: `__init__` (oracle + model built once) → `run()` (may be called multiple times) → `cleanup()` (release resources)
- Oracle and model created once in `__init__`, reused across all `run()` calls
- Enforces consistent initialization across ConGen and QuAcq runners
- `cleanup()` method releases oracle resources

**BaseRunResult**:
- Shared fields: `kb_constraints`, `kb_clauses`, `bg_clauses`, `n_bias`, `n_kb`, `runtime_ms`, `consistency_checks`, `memory_peak_mb`, `profiler_data`, and `metrics` (a `RunMetrics` built via `collect(profiler, <ALGO>_METRICS)`)
- Both `ConGenRunResult` and `QuAcqRunResult` inherit from BaseRunResult
- The per-run `performance` block is *derived* from `metrics` (no hand-listed extended fields); cross-validation reads `run_result.metrics` and feeds `aggregate()`

**ConGenRunner** (inherits BaseRunner):
- File-path-based constructor: `ConGenRunner(bias_path, fm_path, solver_name='glucose4')`
- `__init__`: Builds model once via ConGenModelBuilder (requires oracle for negation computation)
- `run(positive_examples, negative_examples, shuffle_seed=None)` returns `ConGenRunResult` with MSS count
  - Per-fold lifecycle: prepare_task() → shuffle set_c (copy) after prepare_task() → run ConGen
  - Supports bias shuffle seed for reproducibility
  - Oracle reused across folds (no rebuild)

**QuAcqRunner** (inherits BaseRunner):
- File-path-based constructor: `QuAcqRunner(bias_path, fm_path, ...)`
- `__init__`: Builds model once via QuAcqModelBuilder (requires oracle for negation computation, auto-prepares)
- Per-run lifecycle: prepare_task() again → shuffle set_c (copy) after prepare_task() → dispatch to oracle/example mode
- Dual-mode `run(mode, ...)`: dispatches to oracle ('automated'/'interactive') or example ('example_only'/'example_first') paths
- Returns `QuAcqRunResult` with KB constraints, metrics, and profiler data

**Unified Shuffle Pattern** (NEW - commit 260228):
- Both runners now follow identical shuffle lifecycle: prepare_task() → shuffle set_c (copy) → run algorithm
- Shuffle seed controls bias iteration order after preparation (not before)
- Enables reproducible CV experiments without model rebuild

#### conacq/eval/ — Evaluation Framework (~2,090 LOC, 10 files)

Cross-validation, accuracy metrics, unified CV output, and QuAcq->ConGen progressive evaluation. **`eval` is a layer of its own** (ADR-0006): the app core (`runners`/`algorithms`/`oracle`/`bias`/`examples`/`example_generators`) must not import it — boundary-guard rule 6 enforces this. Two former members left `eval/`: the metrics container → `conacq/runners/metrics.py` (a runner's output), and pipeline config → `conacq/config.py` (application config, imported by 5 `apps/` scripts).

| File | LOC | Purpose |
|------|-----|---------|
| `cross_validation.py` | 418 | n-fold CV (CONGEN + Interactive) with pre-generated fold support |
| `kb_comparator.py` | 352 | Compare learned KB vs ground-truth FM. Strategies: description, clause, semantic (SAT-based equivalence) |
| `report.py` | 278 | Generate CSV/JSON/LaTeX/Markdown reports; unified CV dict builder (`generate_unified_cv_dict`, `_enrich_constraints`) |
| `accuracy.py` | 170 | Accuracy/precision/recall/F1 calculation |
| `metrics.py` | 149 | `EvaluationMetrics` + `compute_metrics`: Formula-1 accuracy = (TP+TN)/(TP+TN+FP+FN) from TP/TN/FP/FN counts |
| `folds.py` | 146 | Shared CV fold generation/save/load for fair comparison |
| `result_loader.py` | 111 | Load evaluation results; `ConGenResultData.from_dict()` classmethod |
| `semantic_equivalence.py` | 114 | SAT-based bidirectional entailment checker (KB ≡ C_T equivalence) |
| `progressive_evaluation.py` | 211 | ProgressiveEvaluator engine: run ConGen at query-budget checkpoints, compare vs ground truth |
| `__init__.py` | 143 | Package exports |

### explanation/ — SAT Solver Infrastructure (~6,100 LOC, ~35 files)

Diagnosis algorithms and SAT model abstraction:

#### explanation/models/ — Diagnosis Models & Task Abstraction (Phase R, ~1,560 LOC, 11 files)

SAT model representation and immutable task units:

| File | LOC | Purpose |
|------|-----|---------|
| `task_preparation.py` | 709 | Task family (frozen) + DiagnosisTaskPreparation/TestCaseTaskPreparation strategies + factories + `PreparedTask(task, describe, assignment_map)` result container |
| `diagnosis_model_builder.py` | 381 | Builder (subclasses `AbstractModelBuilder`): `build()` → immutable KB model; `build_task_input()` → per-task `TaskInput`. No `use_incremental()` (checker concern). |
| `pysat_diagnosis_model.py` | 115 | DiagnosisModel: immutable KB (no task/use_incremental state); `prepare_task(task_input)` → `PreparedTask`; exposes id_to_name/name_to_id |
| `testsuite.py` | 92 | TestSuite: holds test cases + their configurations |
| `encoding.py` | 58 | Free-function encoders (config↔literals, config→assignment-assumptions, clause→names). No codec class; name↔id maps passed in. |
| `assignment_assumption_map.py` | 28 | `AssignmentAssumptionMap` frozen holder of pos/neg assignment→assumption maps (prep-derived) |
| `assumption_id_allocator.py` | 44 | `AssumptionIdAllocator`: hands out ids and emits paired (original, negated) ids as a unit — the caller never re-derives which is which by stride |
| `kb_protocol.py` | 27 | `KBProtocol` — read-only name↔id catalog contract (id_to_name/name_to_id + constraint maps) |
| `frozen_dict.py` | 29 | `FrozenDict`: immutable `dict` for deep-freezing mapping-valued fields (e.g. `Task.negation_map`) |
| `abstract_model_builder.py` | 46 | `AbstractModelBuilder` universal base: pure `build()` template (`_validate`→`_create_model`, two abstract hooks); no conacq refs. Exported via api. |
| `__init__.py` | 31 | Package exports |

**Single-source name↔id (T2, refined by ADR-0007):** the name↔id catalog lives on the KB under KB Protocol names (`id_to_name`/`name_to_id`). Read-only is enforced at the **type layer**, not at runtime: `KBProtocol` declares these as `Mapping` (so type-checkers reject `kb.name_to_id[x] = …`), while the concrete storage is a plain `dict` — no `MappingProxyType`, no per-access wrapping (ADR-0007 removed the runtime views: they existed only to pass their own test, cost ~25% on a hot path, and blocked `json.dumps`). The conacq `KBModel` base (`conacq/kb_model.py`) is **domain-neutral**: its `__init__` owns five plain fields (`constraint_map`, `negated_constraint_map`, `next_available_id`, and the public `name_to_id`/`id_to_name` dicts) — no feature-model terms in the base, no properties. ConGen/QuAcq/FMOracle call `super().__init__()` then set only model-specific values; builders assign the `name_to_id`/`id_to_name` dicts directly at build. `DiagnosisModel` is the exception — it keeps `name_to_id`/`id_to_name` as **properties** because it is a flamapy translation layer that maps onto PySATModel's `variables`/`features` (returned as-is, no proxy). The `encoding` free functions receive these maps as parameters — no `VariableCodec`, no per-model encoding duplication. A sibling conacq-root file, `conacq/oracle_bias_model_builder.py`, holds `OracleBiasModelBuilder` — the shared bias-load → negation-via-oracle builder base for ConGen/QuAcq (subclasses the framework `AbstractModelBuilder` via `explanation.api`); it lives in the app because it imports `conacq.bias` and types against `FMOracle`.

#### explanation/checker/ — Consistency-checker Port + Adapters (~404 LOC, 3 files)

The consistency-checker port and its solver-backed adapters. These are not
algorithms — they are what the algorithms *consume* — so they live in their own
package rather than beside `fastdiag.py`/`quickxplain.py` in `operations/algorithms/`.

| File | LOC | Purpose |
|------|-----|---------|
| `protocols.py` | 62 | Consistency-checker **PORT**: `ConsistencyChecker` + `TestCaseChecker` + `CopyableChecker` Protocols (@runtime_checkable); imports no pysat/subprocess. ~24 algorithm sites depend on a port. Re-exported via `explanation/api.py`. |
| `backend.py` | 320 | Backend **ADAPTERS**: `CheckerBase` + `IncrementalPySATChecker`/`NonIncrementalPySATChecker`/`SAT4JChecker` + `SolverBackend` (enum: which solver) + `SolverTimeoutError` + `build_checker` (single public task-based door **and** single class-selection site — token→class if/else inlined; no private `_build_checker`; `sat4j_timeout` knob, default 300). A SAT4J timeout raises `SolverTimeoutError` (not a silent UNSAT). Imports `protocols` top-level (acyclic). |
| `__init__.py` | 22 | Internal facade re-exporting the 3 Protocols + `SolverBackend` + `build_checker` + `SolverTimeoutError`. Not a public door — `explanation/api.py` is the single public surface. |

#### explanation/operations/ — SAT Operations (Phase R, ~4,800 LOC, ~26 files)

Diagnosis operation wrappers and their template base (the consistency-checker
port + adapters they consume now live in `explanation/checker/`, above):

**Core Operation Files** (operations/ top level):

| File | LOC | Purpose |
|------|-----|---------|
| `pysat_explanation_builder.py` | 437 | Builder for diagnosis operations (FastDiag, QuickXPlain, KBDiag) |
| `pysat_abstract_explanation.py` | 52 | Thin base for ALL PySAT operations (checker seam + `get_result`, no HSDAG); redundancy ops extend this directly |
| `pysat_abstract_hsdag_explanation.py` | 299 | Template-method base for HSDAG operations (diagnosis/conflict/testcase); extends `PySATAbstractExplanation` |
| `registry.py` | 56 | Operation registry — name → operation-class seam (the plugin door); built-ins self-register |

**Diagnosis Algorithm Implementations** (`algorithms/` subdirectory, ~2,200 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `algorithms/fastdiag.py` | 85 | FastDiag: breadth-first minimal diagnosis finding |
| `algorithms/fastdiagp.py` | 239 | FastDiagP: parallel FastDiag — depth-first with speculative consistency checks fanned across an `mp.Pool` (kept as scaffolding; the injectable executor is deferred to canonical, ADR-0014) |
| `algorithms/quickxplain.py` | 80 | QuickXPlain: minimal conflict finding |
| `algorithms/kbdiag.py` | 100 | KBDiag: kernel-based diagnosis |
| `algorithms/wipeoutr_fm.py` | 90 | WipeOutR_FM: feature model variant |
| `algorithms/wipeoutr_t.py` | 110 | WipeOutR_T: test case variant |
| `algorithms/utils.py` | 120 | split, diff, negate_cnf_tseitin utilities |
| `algorithms/hsdag/hsdag.py` | 353 | HSDAG tree search: optimization for multiple diagnoses/conflicts (+ `hsdag/node.py`, `hsdag/labeler/` adapters) |

**Operation Wrappers** (pysat_*.py files, 8 files):

Each wraps diagnosis algorithms for specific use cases (conflict, diagnosis, testcase/KBDiag, redundancy). Operations take a `PreparedTask`: `op.execute(prepared)` reads `prepared.task` to solve and `prepared.describe` to format. Solver selection is operation-level: `use_incremental` and `use_sat4j` are op attributes; `build_checker(task, SolverBackend.from_flags(use_incremental, use_sat4j), solver_name, profiler)` (from `explanation.checker.backend`) builds the checker. The standalone `pysat_conflict_sat4j.py`/`pysat_diagnosis_sat4j.py` wrappers were folded into `PySATConflict`/`PySATDiagnosis` via `use_sat4j` (builder entry points `for_conflict_sat4j`/`for_diagnosis_sat4j` remain).

#### explanation/transformations/ — Model Converters (~292 LOC, 5 files)

Feature model to SAT conversion:

| File | LOC | Purpose |
|------|-----|---------|
| `fm_to_diag_pysat.py` | 113 | Feature model → DiagnosisModel (PySAT) |
| `dimacs_to_diag_pysat.py` | 81 | DIMACS CNF → DiagnosisModel |
| `dimacs_to_configuration.py` | 59 | DIMACS variable assignments → Configuration |
| `testsuite_reader.py` | 42 | Read test suites from files |

### profiling/ — Profiling Infrastructure (top-level package)

Neutral infrastructure imported directly by **both** `explanation` and `conacq` (not nested under either). Split by concern from the former 1,220-LOC `explanation/operations/algorithms/profiler.py`:

| File | Purpose |
|------|---------|
| `protocol.py` | `Profiler` @runtime_checkable Protocol (consumers type-annotate against it; facade re-exports as `ProfilerProtocol`) + `AbstractProfiler` ABC + `NullProfiler` + `MetricType` + `ProfilerError` |
| `core.py` | concrete `Profiler` (metrics, stats, CSV/console reporting) + `ProfilerMode` |
| `decorators.py` | `measure_time`, `count_calls` |
| `presets.py` | `ProfilerPreset`, `create_profiler` |
| `registry.py` | `get/set/use_global_profiler`, `profiler_session` |
| `__init__.py` | facade re-exporting the full public surface (`from profiling import X`) |

### apps/ — Standalone Applications (~3,210 LOC, 12 files)

CLI applications for constraint acquisition pipeline. Uses `python -m apps.X` invocation pattern.

| File | LOC | Purpose |
|-----|-----|---------|
| `__init__.py` | ~1 | Package marker (enables python -m invocation) |
| `_harness.py` | 65 | Shared CLI harness: TOML config path + `-v/--verbose` + logging setup + config load + top-level error handling, so each app declares only what's unique |
| `extract_results.py` | 772 | Post-process results, generate Markdown/LaTeX reports (reads embedded evaluation from unified CV format or falls back to external eval files) |
| `generate_bias_config.py` | 502 | Feature model → YAML bias configuration |
| `generate_bias_files.py` | 350 | YAML bias config → JSON/CNF files |
| `generate_examples.py` | 287 | Generate E+/E- examples with sampling strategies |
| `run_compare.py` | 302 | Config mode: reads/enriches unified CV JSONs (idempotent write-back); KB mode: compare learned KB vs ground-truth FM |
| `run_evaluation.py` | 260 | QuAcq → ConGen pipeline: run QuAcq, feed progressive query subsets to ConGen, compare both KBs vs ground truth |
| `run_cv.py` | 209 | Unified n-fold CV for ConGen and Interactive; outputs single JSON per (model × strategy × mode) |
| `run_quacq.py` | 200 | Pure QuAcq learning → KB files (no CV, no evaluation) |
| `run_congen.py` | 188 | Execute CONGEN learning pipeline (dev/debug tool) |
| `generate_cv_folds.py` | 78 | CLI to pre-generate CV folds for reproducible evaluation |

**Config Files** (`conf/`, 11 TOML files):
- `generate_bias_config.toml` — Bias config generation settings
- `generate_bias_files_config.toml` — Bias JSON/CNF generation settings
- `generate_examples_config.toml` — Example generation settings
- `generate_cv_folds_config.toml` — CV fold generation settings
- `run_congen_config.toml` — Single ConGen run settings
- `run_cv_config.toml` — Unified CV settings (ConGen + Interactive)
- `run_quacq_config.toml` — Interactive-only learning settings
- `run_compare_config.toml` — KB comparison settings
- `run_evaluation_config.toml` — QuAcq → ConGen evaluation pipeline settings
- `extract_results_config.toml` — Results extraction settings
- `test_eval_config.toml` — Test evaluation settings

### tests/ — Test Suite (~8,000 LOC, ~40 files)

Pytest suite (`PYTHONPATH=. pytest tests/`). Diagnosis tests were split per-algorithm (T13); the old `test_bias_module.py` demos became `test_bias_io.py` real coverage (T17).

| File | LOC | Purpose |
|------|-----|---------|
| `test_diagnosis_hsdag.py` | 744 | HSDAG multi-diagnosis/conflict search (per-algorithm split of the former diagnosis monolith, T13) |
| `test_diagnosis_redundancy.py` | 204 | WipeOutR redundancy ops |
| `test_diagnosis_kbdiag.py` | 133 | KBDiag |
| `test_diagnosis_quickxplain_wtc.py` | 75 | QuickXPlain-with-testcases |
| `test_diagnosis_fastdiag.py` | 71 | FastDiag / FastDiagP |
| `test_diagnosis_quickxplain.py` | 46 | QuickXPlain |
| `test_quacq.py` | 672 | QuAcq interactive learning (oracle + example modes) |
| `test_congen.py` | 402 | ConGen passive acquisition |
| `test_evaluation.py` | 519 | Cross-validation + accuracy metrics |
| `test_profiler.py` | 536 | Profiling infrastructure |
| `test_t11_purity_guards.py` | 451 | Prepare-purity / immutability guards (T11) |
| `test_assumption_slicer.py` | 230 | Assumption-ID slicing |
| `test_t9_metrics_safety_net.py` | 225 | Metrics-container safety net (T9) |
| `test_boundary_guard.py` | 204 | Package-layering boundary guard (6 rules) |
| `test_generator_characterization.py` | 165 | Example-generator characterization |
| `test_solver_backend_port.py` | 164 | Checker port / `SolverBackend` adapter |
| `test_bias_io.py` | 163 | Bias IO/stats coverage (`validate_config`, `get_statistics`, `save_to_json/cnf/statistics` — T17) |
| `test_oracle_protocols.py` | 142 | Oracle role protocols (ADR-0009/0010) |
| `test_oracle_model.py` | 131 | FMOracleModel |
| `test_semantic_equivalence.py` | 109 | SAT bidirectional entailment |
| `test_task_immutability.py` | 100 | Frozen Task immutability |
| `test_query_converter.py` | 96 | QuAcq `query_history` → ExampleSet |
| `test_example_generators_rng_guard.py` | 91 | RNG-isolation guard (T16) |
| `test_atomic_io.py` | 90 | Atomic file writes |
| `test_transformations_characterization.py` | 78 | FM→SAT transformation characterization |
| `test_encoding.py` | 72 | config↔literals encoding free functions |
| `test_apps_logging.py` | 70 | Apps logging config (needs `tomllib` / py3.11) |
| `test_parallel_scaffolding_guard.py` | 47 | Deferred-executor scaffolding guard (ADR-0014, T4) |
| `test_assumption_id_allocator.py` | 36 | `AssumptionIdAllocator` |
| `test_t11_*.py` (congen_runner_net, oracle_trace_net, prepared_task_ids, e2e_learned_kb) | 105/70/76/44 | T11 oracle-safety-net + e2e checks |
| `test_utils.py` | 56 | Utility functions |
| `conftest.py` / `resource_paths.py` / `diagnosis_helpers.py` / `t11_e2e_harness.py` / `t11_oracle_net_helpers.py` | 31/35/224/266/153 | Shared fixtures, resource paths, and harness helpers (not test modules) |

**Key Testing Patterns**:
- **Parameterization**: `@parameterized.expand()` combinations of incremental/non-incremental modes
- **Test Control**: `ENABLED_TESTS` and `ENABLED_PARAMS` dictionaries for selective test execution
- **Profiling Tests**: Measure execution time and solver call counts
- **Mode Coverage**: Tests run in both incremental (persistent solver) and non-incremental (fresh solver) modes

## Data Directories

### data/fms/ — Feature Models (7 models)

Reference UVL feature models for testing and evaluation:

| Model | Features | Constraints | Files |
|-------|----------|-------------|-------|
| REAL-FM-7 IDE | 14 | ~20 | 1 |
| arcade-game | 65 | ~60 | 1 |
| fqa | 179 | ~100 | 1 |
| REAL-FM-4 eshop | 291 | ~150 | 1 |
| busybox-1.18.0 | 854 | ~500 | 1 |
| ea2468 | 1,408 | ~800 | 1 |
| linux-2.6.33.3 | 6,467 | ~10,000 | 1 |

### data/bias-config/ — Bias Configurations

YAML-formatted bias configurations (one per model), generated by `generate_bias_config.py`.

### data/bias/ — Generated Bias Files

Generated constraint files in JSON and CNF formats:
- `{model}.json` — JSON constraint representation
- `{model}.cnf` — DIMACS CNF format
- `{model}_stats.json` — Constraint statistics

### data/examples/ — Generated Examples

Positive/negative example sets (naming: `{model}_{strategy}_{multiplier}.json`):
- Strategies: `RS` (random sampling), `FF` (feature frequency), `2COV` (2-coverage)
- Multipliers: 25, 50, 75, 100, 150 (percentage of valid configurations to sample)

### data/results/ — Evaluation Results

CONGEN and QuAcq learning results:
- `{model}_CONGEN.json` — CONGEN result
- `{model}_CV_{fold}.json` — Cross-validation folds
- `{model}_interactive.json` — QuAcq result
- `{model}_profile.json` — Execution profiling data

## Dependencies

### Core Runtime
- **python-sat** (PySAT) — SAT solver interface (glucose4, minisat, lingeling)
- **flamapy** — Feature model parsing and manipulation (UVL format)

### Development & Testing
- **pytest** — Test framework
- **parameterized** — Test parameterization decorator

### Utilities
- **pyyaml** — YAML configuration parsing
- **tomllib** (Python 3.11+) — TOML configuration parsing

### Optional
- **sat4j** — External Java SAT solver (subprocess invocation)

## Key Architectural Patterns

### 1. Builder Pattern
- `DiagnosisModelBuilder` — Construct diagnosis models with configuration
- `PySATExplanationBuilder` — Build diagnosis operations

### 2. Strategy Pattern
- `ConsistencyChecker` ABC with implementations (Incremental, NonIncremental, SAT4J)
- Sampling strategies: `RandomSampling`, `FeatureFrequency`, `TwoCoverage`
- Evaluation strategies: `description`, `clause`

### 3. Template Method
- `PySATAbstractHSDAGExplanation` — Base for diagnosis algorithms
- Subclasses implement specific algorithms

### 4. Dependency Injection
- Algorithms accept `ConsistencyChecker` as dependency
- Profiler optionally injected for timing/counting
- Mode-agnostic: No `if is_incremental` branching

### 5. Facade Pattern
- `InteractiveLearner` — High-level QuAcq interface
- `CONGENRunner` — High-level CONGEN pipeline
- `Evaluator` — High-level evaluation orchestration

### 6. Builder Pattern
- `ConGenModelBuilder.from_bias()` — Builder-pattern model construction
- Solver instantiation via consistent factories

## Codebase Statistics

| Component | LOC | Files | Avg File Size | Status |
|-----------|-----|-------|---------------|--------|
| conacq/ | ~10,170 | ~53 | ~192 | ✅ Core algorithms (QuAcq unified + eval pipeline + builder) |
| explanation/ | ~4,600 | ~35 | ~131 | ✅ SAT infrastructure |
| apps/ | ~3,300 | 12 | ~275 | ✅ CLI applications (+ run_evaluation.py) |
| tests/ | ~8,000 | ~40 | ~200 | ✅ Comprehensive coverage |
| **Total** | **~26,000** | **~140** | **~186** | ✅ **Production ready** |

**Task Family** (immutable pure data — `@dataclass(frozen=True)`, no methods):
- **Task(ABC)** → Base holding intrinsic solve fields (single source of truth): `set_c`, `set_b`, `set_kb`, `negation_map`, `assumptions`. No methods — derived quantities are free functions (`cf(task)` = `set_b + set_c`).
- **DiagnosisTask(Task)** → Marker for diagnosis-shaped tasks (no test-case fields).
- **TestCaseTask(Task)** → Adds `set_tc`/`set_tv` (E+/E- IDs), `set_neg_tv`/`set_neg_tc` (negated forms).
- **ConGenTask(TestCaseTask)** → Passive acquisition (marker; `set_neg_tv` populated by GenerateNE).
- **QuAcqTask(DiagnosisTask)** → Adds `constraint_clauses` (raw CNF clauses keyed by assumption ID).
- **TaskInput** → Frozen input; `__post_init__` rejects mutually-exclusive combos (config/test_case vs positive_test_cases); use-case factories `fm_diagnosis`/`config`/`config_with_cf`/`error`/`testcases`/`redundancy_fm`/`redundancy_t`.

**Benefits**:
- Immutable units-of-work built via build-then-freeze (fields computed into locals, task constructed once at end) → two tasks from one KB are safe to execute concurrently.
- Pure data: no codec/describe/get_cf on the task; formatting context and derived helpers live outside it.

**Shared SAT Utilities** (`sat_utils.py`):
- `get_constraint_vars(constraint_clauses)` — Extract SAT variables from constraint CNF
- `prune_rejecting(remaining_bias, config_assumptions, task)` — Filter constraints that reject config
- `config_to_assumptions(config, task)` — Convert feature config to assumption literals
- `violates_clauses(config_assumptions, clauses)` — Check if config violates clauses

**Architecture Unification** (earlier):
- QuAcq now uses **int assumption IDs** (identical to ConGen)
- `QuAcqRunner` dispatches to oracle or example modes via `run(mode)`
- `QuAcqResult` has dual representation: kb_constraints (str names) + kb_assumption_ids (int IDs)
- Both QuAcqTask and ConGenTask use same negation_map and assumption layout
- Shared REDUCE algorithm reuse — no more `_reduce_kb()` conversion layer

**Deprecated Classes** (Backward compatible):
- `InteractiveTask` → Use `QuAcqTask` (string-based names replaced by assumption IDs)
- `InteractiveLearner` → Use `QuAcqModel` + `QuAcq` (clearer architecture)

**Earlier Changes** (Oracle Interface Refactoring - commit c978d66):

> _(Phase-R historical — superseded. Current oracle architecture: role protocols, no fat ABC, frozen provisioning snapshots — ADR-0009/0010/0012. See the oracle sub-package table + Critical Implementation Details above.)_

**Oracle ABC Slimmed**:
- Removed `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()` from Oracle ABC
- Only abstract methods: `is_valid(assignments)` (membership query)
- Concrete method: `ask()` (alias for `is_valid()`)
- All FM-specific methods moved to `FMOracle` implementation

**FMData Introduced**:
- New frozen dataclass `acqmss/oracle/fm_data.py` — FM metadata container
- Fields: `features`, `feature_ids`, `root_feature`, `num_constraints`, `next_available_id`
- Created by `FMOracle.get_fm_data()`, passed explicitly to decouple callers

**FMOracle Extended**:
- New method: `get_fm_data() -> FMData` — Create frozen metadata snapshot
- Concrete methods: `get_features()`, `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`, `get_next_available_id()`, `complete_configuration()`, `get_cnf_clauses()`, `get_constraint_descriptions()`
- `complete_configuration()` implements SAT-based config completion with fallback
- `get_cnf_clauses()` returns raw FM CNF (no assumption guards)

**Example Generators Refactored**:
- Typed as `FMOracle` (not generic `Oracle`)
- Use `oracle.complete_configuration()` instead of direct SAT solver calls
- Removed pysat.solvers imports from `base.py` and `feature_frequency.py`
- Decoupled from solver implementation details

**UserPromptOracle & CachedOracle Updated**:
- Simplified to implement only Oracle ABC (`is_valid()`, `ask()`)
- Raise `NotImplementedError` for FM-specific methods (or delegate to base)
- `CachedOracle` caches `is_valid()` results, delegates FM methods to base oracle

**OracleData Renamed**:
- Old name: `OracleData`
- New name: `GroundTruthData` (reflects FM-reading behavior)
- Backward-compatible alias: `OracleData` still available

**InteractiveLearner Updated**:
- `_build_task_from_bias()` now takes `fm_data: FMData` instead of oracle
- Receives FM metadata explicitly, not tied to oracle instance

**ConGenTaskPreparation Updated**:
- `prepare()` now takes `(model, fm_data, oracle)` signature
- `fm_data` for metadata (FMData), `oracle` for `GenerateNE` and config completion
- Separates concerns: metadata vs. SAT queries
- No longer uses `_prepare_bg()` method (refactored to use BG data extraction)

**BG Data Extraction** (new):
- New frozen dataclass `BGData` in `conacq/oracle/bg_data.py` — Root BG constraint pair + metadata
- Fields: `set_kb`, `assumptions` (root_id, negated_root_id), `negation_map`, `descriptions`, `next_available_id`
- FMOracleModel now exposes `bg_data` property (lazy-computed) and `get_bg_data()` method
- ConGenTaskPreparation calls `oracle.get_bg_data()` to extract root constraint post-preparation
- Enables clean separation: Oracle owns Parts 1-4 of assumption ID layout; ConGen starts allocation at `next_available_id`

**Phase R Architecture** (task-as-unit refactor):
- Models are immutable KB containers (bias + negation maps)
- `model.prepare_task(task_input, oracle) → Task` is pure: fresh Task per call
- GenerateNE pure: returns clauses; caller extends its own KB copy
- Checker built from Task: `build_checker(task, SolverBackend.from_flags(use_incremental=...))` (from `explanation.api`)
- Solver mode (incremental vs non-incremental) chosen via `SolverBackend` enum, not on model builder
- Oracle injected at prepare_task() time, not stored in model
- Cross-validation: build once (expensive negation), prepare+shuffle per fold (cheap, pure)

## Build & Test Commands

```bash
# Install dependencies (from pyproject.toml + uv.lock)
uv sync --extra dev        # or: pip install -e ".[dev]"

# Run all tests (both modes)
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/test_diagnosis_hsdag.py -v

# Run tests matching pattern
PYTHONPATH=. pytest tests/ -k "fastdiag" -v

# Run single test with full profiling
PYTHONPATH=. pytest tests/test_diagnosis_fastdiag.py -v -s
```

## Main Applications

**Unified CV Pipeline** (replaces 45+ file outputs with single JSON per experiment):
1. `run_cv.py` — Unified n-fold CV for ConGen and/or Interactive → single JSON per (model x strategy x mode)
2. `run_compare.py` (config mode) — Reads unified CV JSONs, compares folds, writes enriched evaluation back
3. `extract_results.py` — Post-process unified CV JSONs, generate final reports with fold metrics
4. `run_congen.py` / `run_quacq.py` — Single-run tools for debugging
5. `run_compare.py` (KB mode) — Compare single learned KB vs GroundTruth FM

**QuAcq → ConGen Evaluation Pipeline** (NEW):
1. `run_evaluation.py` — Progressive evaluation: run QuAcq, feed query subsets to ConGen at checkpoints (10%, 25%, 50%, 75%, 100%), compare both KBs vs ground truth

```bash
# Generate bias files from feature model
python -m apps.generate_bias_config data/fms/model.uvl -v
python -m apps.generate_bias_files data/bias-config/model.yaml

# Generate test examples
python -m apps.generate_examples apps/conf/generate_examples_config.toml

# Run unified cross-validation (ConGen + Interactive)
python -m apps.run_cv apps/conf/run_cv_config.toml -v

# Run pure QuAcq learning (no CV, no evaluation)
python -m apps.run_quacq apps/conf/run_quacq_config.toml -v
python -m apps.run_quacq apps/conf/run_quacq_config.toml --interactive

# Compare learned KB against oracle FM
python -m apps.run_compare --kb data/results/model_kb.json --bias data/bias/model-bias.json --oracle data/fms/model.uvl -v

# Single-run ConGen (debug tool)
python -m apps.run_congen apps/conf/run_congen_config.toml -v
python -m apps.run_congen apps/conf/run_congen_config.toml --non-incremental

# Extract and generate final reports (includes fold metrics)
python -m apps.extract_results <results_dir> -v

# Run QuAcq -> ConGen evaluation pipeline (progressive checkpoints)
python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v
```

## File Size Analysis

Largest files (by line count):
- `profiling/` — top-level package (split from the former 1,220-LOC `explanation/operations/algorithms/profiler.py`); neutral infra imported directly by both `explanation` and `conacq`
- `explanation/models/task_preparation.py` — 952 LOC (SAT task setup)
- `tests/test_diagnosis.py` — 1,416 LOC (diagnosis tests)
- `apps/extract_results.py` — 621 LOC (result processing, DRY-refactored from 1,139 LOC)

Most files keep to ~200 LOC for maintainability, except specialized components.

## Next Steps for Documentation

See:
- **project-overview-pdr.md** — Goals, requirements, success criteria
- **code-standards.md** — Naming, patterns, testing conventions
- **system-architecture.md** — Data flow, integration points, design decisions
- **project-roadmap.md** — Development phases and status
