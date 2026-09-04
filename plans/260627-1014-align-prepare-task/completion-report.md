# Completion Report — Align conacq prepare_task with explanation

**Branch:** feat/redesign-abc · **Commits:** `85cb93b..35d6cb3` (6) on top of `9c32bfb` · **No PR (per directive).**
**Suite:** 579 → **593 passed** (+14 safety-net/guard tests). Green-gated after every phase.

## Result

All four KB models now share one signature:

| Model | Before | After |
|---|---|---|
| `DiagnosisModel` | `prepare_task(task_input) -> Task` | unchanged (reference) |
| `ConGenModel` | `prepare_task(task_input, oracle)` | `prepare_task(task_input) -> ConGenTask` |
| `QuAcqModel` | `prepare_task(oracle)` | `prepare_task(task_input=None) -> QuAcqTask` (rejects non-empty) |
| `FMOracleModel` | `prepare_task(configuration)` | `prepare_task(task_input=None) -> DiagnosisTask` |

**Mechanism:** a frozen `OracleTaskData` snapshot (`conacq/oracle/oracle_task_data.py`) is folded onto
ConGen/QuAcq models at build (`_post_negation_build` hook); `prepare_task` reads `self._oracle_data`. The live
oracle (with its SAT checker) is **not** stored on the model — the immutable-KB contract is preserved.

## Per-item

### (1) Unify prepare_task signatures — DONE
- **Verify-at-tip:** confirmed divergent: `ConGenModel.prepare_task(task_input, oracle)`,
  `QuAcqModel.prepare_task(oracle)`, `FMOracleModel.prepare_task(configuration)`; builders held the oracle but
  never stashed it on the model.
- **Change:** snapshot folded at build; oracle param dropped from all three; QuAcq rejects non-empty TaskInput;
  FMOracle's dead `configuration` path cut. `GenerateNE` + ConGen/QuAcq `TaskPreparation` re-typed to the snapshot.
- **Files:** `conacq/oracle/oracle_task_data.py` (new), `conacq/oracle/__init__.py`,
  `conacq/algorithms/acqmss/{congen_model,congen_model_builder,generate_ne,task_preparation}.py`,
  `conacq/algorithms/quacq/{quacq_model,quacq_model_builder,task_preparation,__init__}.py`,
  `conacq/oracle/fm_oracle_model.py`, `conacq/runners/{congen_runner,quacq_runner}.py`, README + 6 `docs/` files,
  tests (`test_congen`, `test_quacq`, `test_assumption_slicer`, 2 new safety-nets).

### (2) Split FMOracleModel — DROPPED (already done at tip)
- **Verify-at-tip:** `FMOracleModel` is already a thin KB container (zero oracle methods); `FeatureModelOracle`
  already composes it (`self._oracle_model = FMOracleModel.from_fm(...).build()`). The "oracle HAS-A KB-model"
  state already existed (B4). User chose **Drop**. No rename/collapse.

### (3) Update callers — DONE
- Runners (`congen_runner.py:118`, `quacq_runner.py:280`), all test call-sites, builder/`__init__`/README +
  22 `docs/` examples + the 3 documented contract statements. Grep gate
  `grep -rn "\.prepare_task(.*oracle" conacq/ tests/ apps/ docs/ README.md` → **empty**.

## Behavior-preserving evidence (oracle + task content)
- **Phase-1 safety-net (added first, green pre/post):** `is_valid`/`complete_configuration`/`model_to_config`
  invariants on REAL-FM-7 + arcade-game; ConGen/QuAcq **task content** pinned on a negative-example fixture —
  `set_neg_tv == [763]`, `len(negation_map) == 303`, `set_kb` SHA-256 `553a7124f047f38d` (len 1093), QuAcq layout.
  All still green after the snapshot rewire → byte-identical task output.
- **Code review (mandatory gate):** DONE, all 6 checks PASS, zero Critical/High/Medium. Snapshot reproduces the
  oracle's 4 reads exactly; one-oracle-per-runner identity holds; `OracleTaskData` frozen (no live solver on model).
  3 Low nits — 2 fixed (`Optional[TaskInput]`, `GenerateNE` test uses snapshot), 1 noted (FMOracle silent-ignore
  of task_input — internal, no-arg only).

## Red-team
13 findings (4H/6M/3L): 11 applied, 2 user-decided (frozen snapshot; QuAcq reject non-empty), 1 rejected
(over-split — kept per-phase green-gates). See `plan.md` § Red Team Review.

## Unresolved questions
None. FMOracleModel's asymmetric silent-ignore of a non-empty `task_input` (vs QuAcq's reject) is intentional
and documented (FMOracle is internal, only ever called no-arg).
