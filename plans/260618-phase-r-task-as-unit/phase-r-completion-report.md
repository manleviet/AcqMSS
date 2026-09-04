# Phase R — completion report (task-as-unit refactor)

**Date:** 2026-06-19 · **Result:** R0–R8 core DONE (L1 deferred per plan). **351 tests green**, flamapy ~=2.0.1 / py3.11. No back-compat shims; no weakened assertions. Code-reviewed (4/4 hard guardrails PASS).

## Per-stage outcome
- **R0** — plan validated vs real code. 3 mechanical fixes applied in plan.md (`R0 fix:`): fm_oracle.py:140/143 are a LOCAL solver in complete_configuration (not a checker/executor consumer) → removed from get_model→solve list; R1 subclass list completed (added QuAcqTask, dataclass/ABC note); GenerateNE already returns but also mutates → refactor = drop mutation. Report: `R0-validation-report.md`.
- **R1** — `Task(ABC)` base (shared sets+assumptions+describe+codec+get_cf); re-parented `DiagnosisTask(Task)`, `TestCaseTask(Task)`; `ConGenTask(TestCaseTask)`, `QuAcqTask(DiagnosisTask)` kept. Forward-ref strings for describe/codec.
- **R2** — `VariableCodec` (explanation/models/codec.py) consolidating id↔name + config↔assumptions; `ModelProtocol` (typing.Protocol); strategies → `prepare(model, task_input)`.
- **R3** — `DiagnosisModel` immutable KB + `prepare_task(task_input)->Task` (pure; independent Tasks; KB-level codec). Builder → KB-only (`with_negation`); per-task inputs → `TaskInput`.
- **R4** — `CheckerFactory.create_from_task(task, *, solver_name, use_incremental, profiler)`. `create_from_model`+`CheckerModel` retained through R5, DELETED in R6 (last caller = conacq).
- **R5** — operations `execute(task)`; `with_incremental` on op builder; `task.*` replaces `model.get_*`; formatting via `task.describe`. test_diagnosis.py rewritten (assertions preserved).
- **R6** — conacq models thin KB+codec; `prepare_task` sole entry (no `_task`/`.task`/stateful `prepare`); consumers (FindC/FindScope/DiscriminatingGenerator/QueryProvider/prune_rejecting) take `(task, codec, checker)`; `get_constraint_vars`/`get_constraints_with_scope` moved onto `QuAcqTask`; `QueryProvider` cursor de-shared; `GenerateNE` pure (no caller-kb mutation); FMOracle hot-path = `checker.is_consistent(base_set_c + codec.config_to_assumptions(cfg))`; `create_from_model`+`CheckerModel` deleted.
- **R7** — `OracleAwareTaskPreparation` mixin + `BGDataProvider` Protocol; BG-copy single-sourced (part3 both; part4 QuAcq-only — matches original).
- **R8 (L2+L3)** — `ConsistencyExecutor` Protocol + `ConsistencyChecker.solve()/submit()` (serial executor). NEW `executor.py`: `ProcessExecutor` (shared mp.Pool; worker builds checker once from KB; option-B boundary counting), `MemoizingExecutor` (in-flight pending-future dedup + resolved-bool cache; HIT≠check), `ConsistencyCache` (thread-safe, per-executor ⇒ KB-namespaced). FastDiagP rewritten: no internal pool/lookup_table, uses executor + memo. `get_model→solve` at query_provider + discriminating_generator (only true checker consumers). New `tests/test_executor.py`: serial≡parallel diagnosis, count parity, HIT-no-recompute, multi-task-one-KB.

## Acceptance criteria (plan §"Acceptance criteria") — ALL met (minus deferred L1)
model has no mutating method ✓ · `execute(task)` references no model ✓ · use_incremental on operation ✓ · no dead task_input ✓ · ModelProtocol typed ✓ · VariableCodec single codec ✓ · algorithms depend on ConsistencyExecutor ✓ · ConsistencyChecker(serial) & ProcessExecutor(parallel) IDENTICAL results ✓ (test) · FastDiagP no internal pool/lookup_table ✓ · no nested pools ✓ · profiler option B ✓ · 2+ tasks/KB independent ✓ (test) · 351 green flamapy 2.0.1/py3.11 ✓.

## Unresolved questions (plan §end) — ANSWERED
1. **for_redundancy/with_cf_in_c KB or Task?** → TaskInput (per-task flags); `negated_constraint_map` stays KB; builder `with_negation()` controls KB negation creation.
2. **use_incremental affects KB build or only checker?** → ONLY checker (verified: sole consumer was CheckerFactory; strategies never see it). On operation via `with_incremental`; checker built with explicit flag.
3. **ConGenTask extends Task or TestCaseTask?** → TestCaseTask (needs set_tc/set_tv/set_neg_tv).
4. **DescriptionProvider+VariableCodec share base Codec?** → No (YAGNI; distinct responsibilities).
5. **CheckerFactory as worker-init builder in ProcessExecutor? SAT4J fits?** → Worker `_init_worker` builds checker from set_kb (Incremental/NonIncremental). SAT4J already takes set_kb/assumptions → same Protocol shape (not wired into the pool path; pool path uses PySAT checkers).
6. **Profiler under ProcessExecutor — A or B?** → **B** (workers NullProfiler; main boundary-counts). Enforced by `test_consistency_check_count_parity` (serial==parallel is_consistent_calls).
7. **memo-cache HIT counts as a check?** → **No** (HIT runs no solve → no `is_consistent_calls` increment). Enforced by `test_hit_does_not_recompute`.

## Deviations (within hard constraints; no design change)
- **Coarser green checkpoints, not 8.** "Green after each stage" + "no shims" + call-graph coupling ⇒ R3+R4+R5 landed together (explanation execute-by-task); each deletion deferred to its last caller (`create_from_model` removed at R6, not R4). Final API exactly as specified; nothing shim survived.
- **R8.2 typing:** FastDiagP depends on the Protocol explicitly; FastDiag/QuickXPlain/KBDiag/WipeOutR remain typed `ConsistencyChecker` (which IMPLEMENTS `ConsistencyExecutor`) — Protocol-compatible already. Explicit retyping deferred with L1 (only FastDiagP needs the executor for L2/L3; the others matter for L1 node-parallelism).
- **QueryProvider** cursor de-shared & renamed but still a persisted run-local cursor; true statelessness deferred with L1 (its only motivation is L1 thread-safety). Docstring corrected to be honest.

## Code review (code-reviewer) — DONE_WITH_CONCERNS, all addressed
4/4 hard guardrails PASS. Fixes applied: removed dead `_use_incremental` builder flag + 3 chained call sites; removed stale "Legacy prepare() shim" comment; dropped 2 unused imports; corrected QueryProvider docstring; made `MemoizingExecutor.is_consistent` register a pending future on the sync-miss path (true thread-safety for future L1 — closes the one latent race the reviewer flagged).

## NOT in scope (deferred, per plan "After this plan")
- **L1** parallel HSDAG node-threads (R8.3) — executor is L1-ready (Protocol + thread-safe cache + in-flight dedup).
- Port explanation/ diff to canonical `explanation` repo; bump to flamapy 2.6.

## Unresolved questions (open)
- None. (Q5 SAT4J-in-pool: PySAT checkers wired into ProcessExecutor; SAT4J fits the Protocol but isn't pool-wired — fine, no current need.)
