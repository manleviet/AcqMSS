# R0 — Plan validation report (Phase R)

**Date:** 2026-06-19 · **Gate:** before R1 · **Verdict:** plan implementable as written; mechanical fixes applied to `plan.md`; no blocking design disagreement; 1 env blocker + design-ish unresolved Qs need user input.

## Verified against real code (OK)
- `checker.py` = 281 LOC ✓ (matches plan "already 281 LOC").
- `query_provider.py:130` = `self.checker.get_model()` ✓ true checker consumer.
- `discriminating_generator.py:64` = `self.model.model_to_config(self.checker.get_model())` ✓ true checker consumer.
- `fastdiagp.py`: `import multiprocessing as mp` (l14), `self.lookup_table` (l42), `self.pool = mp.Pool(...)` (l76) ✓ — R8 removes these.
- Checker picklability: `ConsistencyChecker.__getstate__` nulls `profiler`; `IncrementalPySATChecker.__getstate__/__setstate__` null `solver` then rebuild from `set_kb` in worker (checker.py:140-149). ✓ ProcessExecutor "build checker in worker" assumption FEASIBLE (already how fastdiagp pickles across its pool today).
- `create_from_model(model: CheckerModel)` uses `model.use_incremental` + `model.get_kb()` + `model.get_assumptions()` (checker.py:269-281) → `create_from_task(task, *, use_incremental, ...)` swaps source to task + explicit flag. ✓
- `_pool_index` stateful in `query_provider.py:49,61,66,84-86,102` ✓ — R6 makes stateless.
- `features` dict in `quacq_model.py:52` + builder:64; `get_constraint_vars` quacq_model:130 used by discriminating_generator:51 ✓ — R6 moves to codec.

## Mechanical fixes applied to plan.md (marked "R0 fix:")
1. **§R8.1 get_model list:** removed `fm_oracle.py:140/143`. Those are `solver.get_model()` on a **local** one-shot `Solver` in `complete_configuration()` (fm_oracle.py:116-147, solver built l134 from `get_fm_clauses()`) — NOT a checker/executor consumer, never runs under ProcessExecutor. `executor.solve()` does not apply. Only `query_provider:130` + `discriminating_generator:64` are checker consumers.
2. **§R1 hierarchy:** plan's "3 subclasses" enumeration incomplete. Real today: `DiagnosisTask`(base dataclass), `TestCaseTask(DiagnosisTask)`, `ConGenTask(TestCaseTask)`, **`QuAcqTask(DiagnosisTask)`** (quacq/task_preparation.py:27 — plan never names it). Keep all. Re-parent `TestCaseTask` → direct `Task` child changes `isinstance(TestCaseTask)` guards in model getters (removed in R3 anyway). `Task(ABC)` must be `@dataclass`-compatible (DiagnosisTask/TestCaseTask are dataclasses).
3. **§R6 GenerateNE:** `generate()` (generate_ne.py:45) ALREADY returns `(results, id)` (l82) but ALSO mutates `set_kb/set_tv/assumptions` in place (l107-109). Refactor = drop in-place mutation (purity fix), not a new return.

## Full call-site inventory (for R3–R6 execution; none missed by plan beyond above)
- `create_from_model` (8 prod + 6 test): fm_oracle.py:52, quacq/__init__.py:28, congen_runner.py:166, quacq_runner.py:247, **pysat_abstract_explanation.py:182** (operations-layer — R5), checker.py:269 (def); tests: test_oracle_model:63,73, test_quacq:84,272, test_diagnosis:206, test_congen:72.
- `model.prepare(...)` stateful: congen_model_builder.py:38,127, quacq_model_builder.py:77, congen_runner.py:153, quacq_runner.py:239, diagnosis_model_builder.py:324, fm_oracle_model.py:168; tests: test_oracle_model:15, test_congen:344,348.
- `def execute(self, model)`: pysat_abstract_explanation.py:218, pysat_redundancy_constraints.py:45, pysat_redundancy_testcases.py:44 (R5 → `execute(self, task)`). Test call-sites: test_diagnosis.py (~30 `hsdag.execute(model)`/`op.execute(model)`).
- `model_to_config`/`config_to_assumptions` dup: quacq_model:116,174, fm_oracle_model:108,130,240, query_provider:89,134, findc:74, sat_utils:29, discriminating_generator:64 (R6 → codec).

> **CONFIRMED by user 2026-06-19:** Q2 (strategy incremental-blind), Q6 (profiler option B), memo-HIT ≠ check. Test runner: user supplies interpreter path.

## Answers to plan "Unresolved questions" (proposed; reasoning)
1. **for_redundancy / with_cf_in_c — KB or TaskInput?** → **TaskInput** (per-task flags). `negated_constraint_map` stays KB-level (it's a property of the constraint set). The decision to *use* negation / put CF-in-C is per-task. Matches plan lean.
2. **use_incremental affects KB build or only checker?** → **only checker** (VERIFIED: sole consumer is `CheckerFactory.create_from_model`; `TaskPreparationFactory.create_*(use_incremental)` switches only Description key-hashing, not KB clauses — strategy never needs it for KB). → strategy doesn't receive it; `with_incremental` lives on operation; checker built with explicit flag. **(needs confirm — see Q below; this is the one borderline design item.)**
3. **ConGenTask extends Task or TestCaseTask?** → **TestCaseTask** (already is; needs set_tc/set_tv/set_neg_tv). Recorded.
4. **DescriptionProvider + VariableCodec share base Codec?** → **No** (YAGNI; different responsibilities — describe=formatting, codec=id↔name+assumptions). Optional, skip.
5. **CheckerFactory as worker-init builder in ProcessExecutor? SAT4J fits?** → **Yes.** Worker `initializer` calls a task-free builder from `set_kb`+`solver_name`+`use_incremental`. SAT4J already takes `set_kb`/`assumptions` (checker.py:191) → fits same Protocol.
6. **Profiler under ProcessExecutor — A or B?** → **B (default)**: workers use NullProfiler, main times the executor + counts at submit/solve boundary. Rationale: counts never lost (boundary-counted in main); per-solve `solver_time` from workers is the only loss, acceptable for prototype; avoids `Manager().dict()` IPC overhead. (Plan §91 already leans B.) **(confirm acceptable.)**
7. **L1 node threading frontier** → OUT of Phase R core (R8.3 deferred). N/A this round.

Extra decided: **memo-cache HIT counts as a consistency check? → NO** (a HIT means no SAT solve ran; `is_consistent_calls`/`paper_consistency_checks` count actual solves). Boundary counter increments only on MISS→solve. User is precise about counting (cf. commit 8fb6517 disabling a profiler increment) → conservative: cache HIT ≠ check. **(confirm.)**

## Blockers / questions for user
- **ENV (blocking):** `pytest` not installed in active interpreter `/usr/local/bin/python3` (`ModuleNotFoundError: pytest`); project `.venv` has it but is blocked by scout-block hook (`~/.claude/.ckignore` pattern `.venv`). Cannot run mandated per-stage `PYTHONPATH=. pytest tests/ -v`. Need: unblock `.venv` (add `!.venv` to `.ckignore`) OR a runnable interpreter path.
- **DESIGN confirm (not disagreements, but shape R-stages):** Q2 (use_incremental strategy-blind), Q6 (profiler B), memo-HIT-not-counted. Lean as above; confirm before R5/R8.

## Unresolved questions (open)
- None blocking beyond the env runner + the 3 confirm-items above.
