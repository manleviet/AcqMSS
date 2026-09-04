# Phase R — Task-as-unit refactor (AcqMSS prototype) — implementation plan

**Date:** 2026-06-18 · **Owner:** Claude Code (AcqMSS) · **Status:** ready, large refactor
**Role:** This repo is the **prototype/validation sandbox** (richest use cases: ConGen folds, FMOracle hot-path, QuAcq). Once green here, the framework diff is ported to the canonical `explanation` repo, then KBDiag/DiagEnergy consume it.
**Authoritative API spec (READ FIRST):** Cowork doc `phase-r-implementation-spec-2026-06-18.md`. If unavailable, the target API is restated per-stage below.
**Scope:** `explanation/` (in-repo framework copy) + `conacq/`.

## Guardrails
- **No backward compatibility.** Remove the old stateful API; rewrite call sites + tests to the new API. Do NOT keep `model.prepare()`/`execute(model)` wrappers.
- **Do NOT bump flamapy.** Stay on the current `flamapy~=2.0.1` / py3.11 stack — this refactor is orthogonal to the flamapy version; bumping would conflate with the 2.6 whitespace test churn (separate follow-up).
- This is a PROTOTYPE to validate the design. Keep the framework changes (under `explanation/`) **isolated and minimal** so they port cleanly to canonical later. conacq-side changes stay in conacq.
- Go **stage by stage**; run `PYTHONPATH=. pytest tests/ -v` after each stage (or as soon as a stage is self-consistent). All tests green before moving on. Tests are rewritten to the new API as part of the relevant stage — do NOT weaken assertions to pass.

## Target (summary; full detail in the spec)
- `model` = immutable KB (`constraint_map`, `negated_constraint_map`, `variables`, `next_available_id`, `codec`). No `_task*`, no `prepare()` stateful, no getters, no `use_incremental` on model.
- `Task` (ABC) = the unit: `set_c/set_b/set_kb/assumptions/negation_map` + `describe` (DescriptionProvider) + `codec` (VariableCodec). Keep subclass names `DiagnosisTask`/`TestCaseTask`/`ConGenTask`.
- `model.prepare_task(task_input) -> Task` (pure, no mutation; new Task each call).
- `op.execute(task)`; `use_incremental`+`solver_name` on operation builder (`with_incremental`/`with_solver`).
- `CheckerFactory.create_from_task(task, *, solver_name, use_incremental, profiler)`; drop `create_from_model` + `CheckerModel` protocol.
- `ModelProtocol` (typing.Protocol) replaces `model: Any` in strategies; strategy `prepare(model, task_input)` reads task_input from the **arg**.
- `VariableCodec` (in explanation): `id_to_name` required, `pos/neg_assumption` optional; replaces `QuAcqModel.features` + the duplicated `config_to_assumptions`/`model_to_config`.

## Stages

### R1 — `Task` ABC + fold DescriptionProvider/codec refs (explanation/models/task_preparation.py)
- Introduce `class Task(ABC)` with fields `set_c/set_b/set_kb/assumptions/negation_map` + `describe: Optional[DescriptionProvider]` + `codec: Optional[VariableCodec]` + `get_cf()`.
- Re-parent: `DiagnosisTask(Task)`, `TestCaseTask(Task)` (add `set_tc/set_tv/set_neg_tv/set_neg_tc`). conacq `ConGenTask` stays `ConGenTask(TestCaseTask)` (it needs `set_tc/set_tv/set_neg_tv`; resolves Unresolved Q3).
- **R0 fix (current hierarchy + completeness):** Today `DiagnosisTask` (base, dataclass), `TestCaseTask(DiagnosisTask)`, `ConGenTask(TestCaseTask)`, `QuAcqTask(DiagnosisTask)`. Plan re-parents `TestCaseTask` to be a direct `Task` child (sibling of `DiagnosisTask`, no longer subclass) — this changes `get_tc/get_tv` `isinstance(TestCaseTask)` guards in `pysat_diagnosis_model.py:148-184` (those getters are removed in R3 anyway). The plan's "3 subclasses" enumeration is INCOMPLETE: there is also **`QuAcqTask(DiagnosisTask)`** (conacq/algorithms/quacq/task_preparation.py:27) — keep it, re-parent transitively. `DiagnosisTask` and `TestCaseTask` are `@dataclass`es → `Task(ABC)` must be dataclass-compatible (ABC + `@dataclass` fields).
- `PreparationOutput` unchanged (still `{task, description_provider}`) for now.
- Acceptance: imports resolve; existing construction sites compile; suite green.

### R2 — `VariableCodec` + `ModelProtocol` (explanation)
- Add `VariableCodec` (spec §1) and `ModelProtocol` (spec §2) in `explanation/models/` (e.g. `codec.py` + in `task_preparation.py`).
- Change the two strategy ABCs to `prepare(self, model: ModelProtocol, task_input: TaskInput)`; concrete strategies read `task_input` from the **arg** (delete `task_input = model.task_input`).
- Acceptance: mypy/type-check sees the contract; suite green (callers updated in R3).

### R3 — `model` immutable + `prepare_task` (explanation + DiagnosisModel)
- `DiagnosisModel`: remove `_task`/`_task_input`/`_description_provider`/`prepare()`/getters/`use_incremental`. Build `codec` once (id_to_name from `variables`; pos/neg only if assignment-assumption layer exists).
- Add `prepare_task(self, task_input) -> Task`: run strategy `prepare(self, task_input)`, then `task.describe = out.description_provider`, `task.codec = self.codec`, return task.
- `DiagnosisModelBuilder`: move per-task inputs (`with_test_case/with_configuration/with_positive_testcases/...`, `use_incremental`) OUT of the model builder into `TaskInput`. Builder only constructs the KB. (Decide `for_redundancy`/`with_cf_in_c` KB-vs-task per spec §12.)
- Acceptance: `model = builder.build()` returns a KB; `model.prepare_task(TaskInput(...))` returns a fresh Task; two calls give independent Tasks.

### R4 — Checker `create_from_task` (explanation/operations/algorithms/checker.py)
- Add `create_from_task(task, *, solver_name, use_incremental, profiler)`; remove `create_from_model` + `CheckerModel` protocol. Keep `create_sat4jchecker` (task-based). `get_model()` stays.
- Acceptance: checker builds from a Task; `tests/test_checker.py` (if present here) updated to construct from a Task or directly; suite green.

### R5 — Operations `execute(task)` + `with_incremental` (explanation/operations/*)
- `PySATExplanationBuilder.with_incremental(enabled=True)`; operations store `self.use_incremental`.
- `execute(self, task)`, `prepare_hsdag(self, task)`, `_create_checker`→`create_from_task(...)`, `_create_labeler(checker, task)`. Replace every `model.get_*()` in operations + labelers with `task.*`. Result formatting uses `task.describe`.
- Acceptance: all `PySAT*` operations run from a Task; framework tests (rewritten) green.

### R6 — conacq models thin + algorithms receive (task, codec, checker)
- `ConGenModel`/`QuAcqModel`/`FMOracleModel`: reduce to KB + `codec`; add `prepare_task(...) -> Task`; delete `features`, duplicated `config_to_assumptions`/`model_to_config`, on-model getters. ConGen folds: `task = model.prepare_task(TaskInput(pos,neg))` per fold. FMOracle: build checker once from base task; per query `checker.is_consistent(base_set_c + task.codec.config_to_assumptions(cfg))`.
- `DiscriminatingGenerator`/`QueryProvider`/`FindC`/`FindScope`: take `(task, codec, checker)` instead of `model`. Replace `model.model_to_config` → `codec.model_to_config`; move `get_constraint_vars` onto codec/task.
- `QueryProvider`: make **stateless** (remove `_pool_index`).
- `GenerateNE`: **return** NE clauses instead of in-place append; caller extends its own copy.
  - **R0 fix:** `GenerateNE.generate()` (generate_ne.py:45) ALREADY returns `(results, id_assumption)` (line 82) but ALSO mutates the passed `set_kb`/`set_tv`/`assumptions` in place (lines 107-109). Refactor = stop the in-place mutation (return the deltas; caller extends its own copy). Not a new return value — a purity fix.
- Acceptance: QuAcq/ConGen/FMOracle run on the new API; their tests (rewritten) green.

### R7 — Unify TaskPreparation (conacq + explanation)
- Base `OracleAwareTaskPreparation` consolidating BG-copy-from-oracle (used by ConGen/QuAcq/FMOracle preparations). Oracle exposes `BGDataProvider` Protocol (`get_bg_data() -> BGData`).
- Acceptance: duplication removed; suite green.

### R8 — ConsistencyExecutor + parallelism (chose hướng 2: executor is the core design)

> 🟡 **SCOPE (chốt 2026-06-18):** Phase R core triển khai **L2 + L3** (executor + FastDiagP dùng executor). **L1 (parallel HSDAG node) HOÃN sang giai đoạn sau** — vì HSDAG hiện **tuần tự hoàn toàn** (best-first chỉ là ordering, KHÔNG song song), nên L1 là **tính năng MỚI** (xây mới, rủi ro cao hơn refactor thuần), không phải refactor cái đã có. R8.3 + các dòng test/acceptance liên quan L1 ⇒ chuyển xuống "After this plan". Executor (R8.1) vẫn thiết kế sẵn sàng cho L1 (Protocol + thread-safe cache) để giai đoạn sau gắn vào không phải sửa lại.

**Concept.** There are THREE parallelism levels; the unit at each is different:
- **L1 — HSDAG node (HOÃN — giai đoạn sau):** expand INDEPENDENT nodes concurrently; each node **activates a full labeler** (FastDiagP / QuickXPlain / KBDiag) to compute its label (a conflict/diagnosis). Unit = one labeler run, NOT a single CC. *Hiện HSDAG tuần tự; đây là tính năng mới.*
- **L2 — FastDiagP (Phase R core):** orchestrates one diagnosis; speculative lookahead → submits consistency-check (CC) jobs.
- **L3 — consistency check (Phase R core):** one SAT solve.

Key design: **flatten to ONE shared CC service; never nest process pools.**
- **L3 = `ConsistencyExecutor`** = the single shared process pool; the ONLY place SAT solves run. Essentially "a parallel `ConsistencyChecker` service." (Phase R core)
- **L2 = FastDiagP** submits CC to the same L3 executor. (Phase R core)
- **L1 = threads** over independent nodes (each runs its own labeler/FastDiagP — mostly orchestration waiting on L3 futures, so GIL is released on IPC). No process pool at node level. **(HOÃN — giai đoạn sau)**
- No `mp.Pool` inside an `mp.Pool` ⇒ no daemonic-nesting error; one worker budget. (Khi thêm L1 sau: threads ở L1 + 1 process pool ở L3 → vẫn không lồng pool.)

#### R8.1 — `ConsistencyExecutor` abstraction (replaces FastDiagP's internal pool)
The executor is a **parallel `ConsistencyChecker` service** — it MUST mirror the FULL checker interface (verified: 3 ops are used across algorithms), not just `is_consistent`:
```python
class ConsistencyExecutor(Protocol):
    def is_consistent(self, assumptions) -> bool: ...                         # used by FastDiag(P)/QuickXPlain/WipeOutR/Reduce/FindC/prune/DiscGen/QueryProvider/FMOracle
    def is_consistent_test_cases(self, set_c, set_tc, stop) -> list: ...      # used by KBDiag/QuickXPlainWithTestCases/ConGen/AcqMSS (batch CC → parallelizable)
    def solve(self, assumptions) -> tuple[bool, list[int] | None]: ...        # returns (sat, model_lits) — for get_model consumers
    def submit(self, assumptions) -> "Future[bool]": ...                      # async (FastDiagP lookahead / node speculation)
```
- **`get_model` consumers must be refactored** from the stateful two-step `is_consistent(...); checker.get_model()` to a single `sat, model = executor.solve(...)` — because under `ProcessExecutor` the model lives in the worker, not the caller. Affects: `query_provider.py:130` (`self.checker.get_model()`), `discriminating_generator.py:64` (`self.checker.get_model()`). `model_lits` is a list[int] → picklable.
  - **R0 fix:** `fm_oracle.py:140/143` REMOVED from this list. Those two `solver.get_model()` calls live in `complete_configuration()` (fm_oracle.py:116-147) and operate on a **local** one-shot `Solver` built from `get_fm_clauses()` (fm_oracle.py:134) — NOT on a `ConsistencyChecker`/executor. They never run under `ProcessExecutor`, so `executor.solve()` does not apply. Leave them as-is (out of executor scope). Only `query_provider.py:130` + `discriminating_generator.py:64` are true checker consumers.
- **Profiler counting at the boundary:** the executor increments count metrics (`is_consistent_calls`, `is_consistent_test_cases_calls`, and the algorithm's `paper_consistency_checks` if it owns it) in the MAIN process at the call/submit boundary → counts never lost regardless of where the solve runs (fixes §2b D for counts; serves the runners). Only per-solve `solver_time` needs option A (shared `Manager().dict()`) vs B (main wall-time). Decide whether a memo-cache HIT counts as a check (be explicit — user is precise about counting, cf. reduce.py). checker-as-serial-executor and `ProcessExecutor` MUST count identically.
- **`ConsistencyChecker` IS the serial executor (option 1, chosen).** Keep `ConsistencyChecker` and make it implement the `ConsistencyExecutor` Protocol: it already has `is_consistent`/`is_consistent_test_cases`; add `solve()` (one call = consistency + model, replacing the two-step `get_model`) and `submit()` (runs inline, returns an already-resolved future). No separate `SerialExecutor` wrapper. Sequential = pass a checker directly; no processes; no overhead.
- **`ProcessExecutor(set_kb, solver_name, n_workers, profiler_mode)`**: `mp.Pool(initializer=...)` where each worker builds its OWN checker ONCE from `set_kb` (sent once, not per call); `submit`/`is_consistent` send only `assumptions` (picklable ints) and get back a `bool`.
- **Memoizing cache lives INSIDE the executor** (replaces FastDiagP `lookup_table`): keyed by assumptions-hash, **namespaced by KB identity** (avoid cross-KB collisions); stores **resolved bool** (never futures); thread-safe. Dedups CC across all submitters (FastDiagP lookahead + multiple nodes).
- **Profiler (resolves §2b D):** `ProcessExecutor` worker `initializer` builds the checker and either (B, default) uses NullProfiler in workers + main times the executor, or (A) attaches a shared `Manager().dict()` profiler so worker CC metrics aggregate. Document the choice.
- **File layout (decided):**
  - `explanation/operations/algorithms/checker.py` (already 281 LOC) — keep the **serial** side: add the `ConsistencyExecutor` Protocol here (next to the contract it formalizes), and add `solve()`/`submit()` to `ConsistencyChecker` (option 1: the checker IS the serial executor). Also keeps `CheckerFactory`.
  - `explanation/operations/algorithms/executor.py` (**NEW**) — the **parallel/decorator** side: `ProcessExecutor` (mp.Pool + worker `initializer`), `MemoizingExecutor` + `ConsistencyCache`. `import`s Protocol + `ConsistencyChecker` from `checker.py` (one-way, no cycle).
  - Rationale: `checker.py` already exceeds the ~200-LOC modularize threshold; piling `mp.Pool`/initializer/cache on top would bloat it and mix "serial checker definition" with "parallel infrastructure". Canonical `explanation` repo mirrors the same `{checker.py, executor.py}` layout when ported.

#### R8.2 — Algorithms depend on the executor, not a raw checker
- `FastDiag`, `FastDiagP`, `QuickXPlain`, `QuickXPlainWithTestCases`, `KBDiag`, `WipeOutR_*`, and labelers depend on the `ConsistencyExecutor` Protocol. Serial runs pass a `ConsistencyChecker` directly (it implements the Protocol); parallel runs pass a `ProcessExecutor`. Optional `MemoizingExecutor` decorator (cache + boundary counting) wraps either.
- **FastDiagP**: delete its internal `mp.Pool` + `lookup_table`; lookahead = `executor.submit(...)`; cache = the executor's memo. FastDiagP keeps only algorithm state (per-instance, per-node).

#### R8.3 — L1 node parallelism in HSDAG  🟡 HOÃN — giai đoạn sau (KHÔNG trong Phase R core)
- *(Tính năng mới — HSDAG hiện tuần tự.)* Add a thread-pool option to expand **independent** nodes concurrently; each node activates its labeler (which uses the shared executor). Respect DAG dependencies (children need the parent's label) — only independent nodes/branches run concurrently. Per-node its own labeler instance; shared executor + thread-safe cache.
- Phase R chỉ cần đảm bảo executor (R8.1) đã sẵn Protocol + cache thread-safe để L1 gắn vào sau mà không sửa lại executor.

#### R8.4 — Tests rewrite + coverage + verify
- Rewrite to new API: `tests/test_diagnosis.py`, `test_profiler.py`, `test_utils.py`, `test_congen.py` (incl. `test_cv_re_prepare`/`test_last_call_wins` → independent Tasks), `test_oracle_model.py`, `test_quacq.py`, `test_checker.py`.
- Coverage matrix (results must be IDENTICAL across executor choices):
  - `ConsistencyChecker` as serial executor (no processes); `ProcessExecutor` only (FastDiagP feeds it).
  - multi-task on one KB (one model → N Tasks → independent executes).
  - *(L1 threads + both-levels-at-once → kiểm thử cùng giai đoạn L1 sau, không thuộc Phase R core.)*
- Profiler behaviour matches the chosen option (B main-only / A aggregated) — no silently partial metrics.
- Final: `PYTHONPATH=. pytest tests/ -v` fully green.

## Acceptance criteria (whole Phase R)
- `model` has no mutating method; `op.execute(task)` references no model; `use_incremental` on operation; no dead `task_input` param; `ModelProtocol` typed; `VariableCodec` is the single codec.
- Algorithms depend on `ConsistencyExecutor`; `ConsistencyChecker` (serial) and `ProcessExecutor` (parallel) give IDENTICAL results; FastDiagP has no internal pool/`lookup_table` (uses executor + its memo cache); no nested process pools; profiler behaviour matches chosen option (no silent loss).
- 2+ tasks per KB run independently.
- All tests green on flamapy 2.0.1 / py3.11.
- *(L1 parallel HSDAG KHÔNG thuộc Phase R — xem "After this plan".)*

## After this plan (NOT in scope here)
- **L1 parallel HSDAG (tính năng mới):** thread-pool expand các node độc lập, mỗi node activate labeler dùng shared executor (R8.3). Executor đã sẵn cho việc này — chỉ thêm tầng điều phối node + test "L1 only" và "both levels at once".
- Port the `explanation/`-side diff to canonical `explanation` repo (py3.11 + flamapy 2.6, has best-first HSDAG — semantic port, not file copy).
- Then KBDiag/DiagEnergy consume canonical; AcqMSS bumps to 2.6 + deletes its in-repo `explanation/` copy + adds `explanation` as dependency.

## Unresolved questions (decide while prototyping; record answers back to Cowork)
1. `for_redundancy`/`with_cf_in_c`: KB property or TaskInput? (lean: `negated_constraint_map` is KB; the per-task "use negation" flag is TaskInput.)
2. Does `use_incremental` affect how the strategy builds the KB, or only the checker? If only checker → strategy never sees it. If it does → pass the flag into `prepare_task` (never store on model).
3. `ConGenTask` extends `Task` or `TestCaseTask`?
4. Should `DescriptionProvider` + `VariableCodec` share a base `Codec`? (optional.)
5. Executor↔checker boundary: does `CheckerFactory` become the worker-init builder inside `ProcessExecutor` (each worker builds its checker from `set_kb`)? Confirm SAT4J path also fits the executor (it already takes set_kb/assumptions).
6. Profiler under `ProcessExecutor`: option B (workers NullProfiler + main times executor) or A (shared `Manager().dict()` via initializer)? Record the choice.
7. L1 node threading: how does the HSDAG decide independent nodes safe to expand concurrently (BFS frontier? best-first?)? Cache must be thread-safe.
