---
title: AcqMSS redesign A+B+C (post-Phase-R)
description: >-
  Full duplication/boundary/architecture redesign on the merged Phase-R
  baseline. Scope = A+B+C, staged, no back-compat.
status: completed
priority: P1
branch: feat/redesign-abc
tags:
  - refactor
  - dry
  - boundary
  - architecture
  - packaging-prep
blockedBy: []
blocks: []
created: '2026-06-21T12:24:09.299Z'
createdBy: 'ck:plan'
source: skill
---

# AcqMSS redesign A+B+C (post-Phase-R)

## Overview

Residual-debt redesign built on the merged Phase-R baseline (task-as-unit, immutable KB, `VariableCodec`, `ConsistencyExecutor`, `OracleAwareTaskPreparation`). Targets what Phase R left untouched: residual duplication, a leaky `explanation/`↔`conacq/` boundary, two god-modules (profiler, eval metrics), `apps/` hygiene, and test scaffolding. Design source of truth = the two Cowork briefs (`acqmss-redesign-options-2026-06-21.md` + `acqmss-full-scan-2026-06-21.md`). Verified against live code on `feat/redesign-abc` 2026-06-21 — all work-item claims confirmed (see Verification).

## Inviolable principles (same as Phase R)

- **No back-compat.** Free to break public API, merge modules, rename, delete clones. No compatibility wrappers.
- **Pin lock.** Keep `flamapy~=2.0.1`, `requires-python>=3.11` (`.venv` = 3.11.14). Never bump. (README's "3.13+" is stale prose, not a pin.)
- **Staged + green-gated.** Sequential stages; after EACH stage `PYTHONPATH=. pytest tests/ -v` must be fully green before the next. Never weaken assertions to pass.
- **Framework isolation.** All framework changes stay inside `explanation/` and isolated, for a clean future port to the canonical repo. conacq-side changes stay in `conacq/`.
- **No scope creep.** Out-of-plan issues → write a note + ask, don't self-fix. If a stage balloons → split + report, don't cut.
- **Data/export format frozen (user decision 260621).** "No back-compat" applies to API/types ONLY. On-disk result JSON (`data/results/**`) must stay `from_json`-readable, and CSV/LaTeX exports must stay byte-identical — the `paper/tables/results_tables.{tex,md}` pipeline (`apps/extract_results.py`) consumes them. C2/B4/C4/A6 change in-memory types/APIs but preserve on-disk + export formats; do NOT regenerate `data/results/` or `paper/tables/`.
- **Commit cadence (user decision 260621):** one conventional commit per GREEN stage on `feat/redesign-abc`; single PR opened after all of A+B+C is complete.

## Testing policy (every stage)

- **Standardise on pytest.** pytest runs the 3 existing `unittest` files as-is → migrate incrementally (test_utils, test_executor easy; test_diagnosis when its code is touched). Suite never breaks mid-migration.
- **3 test layers, 3 timings:** (1) infra FIRST = A7 (conftest + resources). (2) safety-net characterization tests written IMMEDIATELY BEFORE refactoring a currently-untested module — never blind. (3) existing tests rewritten WITHIN their stage to the new API, no weakened assertions, on A7 fixtures.

## Phases (execution order = A→B→C, locked)

| Phase | Name | Status |
|-------|------|--------|
| 1 | [A7 pytest infra (conftest + resources)](./phase-01-a7-pytest-infra-conftest-resources.md) | Completed |
| 2 | [A1 unify assumption-slicer](./phase-02-a1-unify-assumption-slicer.md) | Completed |
| 3 | [A2 abstract model builder](./phase-03-a2-abstract-model-builder.md) | Completed |
| 4 | [A3 solver-backend strategy ops](./phase-04-a3-solver-backend-strategy-ops.md) | Completed |
| 5 | [A4 base runner profiling+metrics](./phase-05-a4-base-runner-profiling-metrics.md) | Completed |
| 6 | [A6 apps CLI harness + atomic JSON](./phase-06-a6-apps-cli-harness-atomic-json.md) | Completed |
| 7 | [A5 logging + error-handling hygiene](./phase-07-a5-logging-error-handling-hygiene.md) | Completed |
| 8 | [B2 profiler protocol + physical split](./phase-08-b2-profiler-protocol-physical-split.md) | Completed |
| 9 | [B3 unify oracle contract](./phase-09-b3-unify-oracle-contract.md) | Completed |
| 10 | [B4 builder statelessness + FMOracle purity](./phase-10-b4-builder-statelessness-fmoracle-purity.md) | Completed |
| 11 | [B1 explanation public surface + boundary](./phase-11-b1-explanation-public-surface-boundary.md) | Completed |
| 12 | [C5 codec merge + seeded RNG + oracle protocol](./phase-12-c5-codec-merge-seeded-rng-oracle-protocol.md) | Completed |
| 13 | [C7 labeler template + algorithm twins](./phase-13-c7-labeler-template-algorithm-twins.md) | Completed |
| 14 | [C1 solver-backend port + adapters](./phase-14-c1-solver-backend-port-adapters.md) | Completed |
| 15 | [C2 unified RunMetrics pipeline](./phase-15-c2-unified-runmetrics-pipeline.md) | Completed |
| 16 | [C4 config-loader + IO base](./phase-16-c4-config-loader-io-base.md) | Completed |
| 17 | [C3 operation registry plugin seam](./phase-17-c3-operation-registry-plugin-seam.md) | Completed |
| 18 | [C6 bias/clause generator cleanup + dead code](./phase-18-c6-bias-clause-generator-cleanup-dead-code.md) | Completed |

Order rationale: A1 (slicer) is imported by B1 (public surface); A2/A3/A4 delete clones so C never refactors doomed code. B2 before B1 so the facade exports the Protocol, not the module. C sits behind B's boundary (C1 port + C2 metrics live under the B1 surface).

## Global acceptance (whole A+B+C)

- 0 duplicated blocks: `_assign_sets` / model-builder / SAT4J-op / runner / config-encoding / labeler / algorithm-twin.
- Guard-test green: no `conacq`→`explanation` underscore-private import.
- All framework deps typed against Protocols: `ModelProtocol`, `Profiler`, `Oracle`, `SolverBackend`.
- 1 seeded RNG source (reproducibility test). 1 `RunMetrics` source of truth.
- `print()` count = 0 in `conacq`+`explanation`+`apps` (logging only; interactive `user_prompt` excepted).
- CV-JSON writes atomic. Single runner = pytest + `conftest.py` + `tests/resources.py`. New tests cover transformations/runners/oracles.
- Framework changes isolated under `explanation/` (clean port). Full suite green (≥351).

## Verification (live code, 2026-06-21, `feat/redesign-abc`)

All brief claims confirmed: 4× `_assign_sets`; `last_task` in both builders; dup `shuffle(task.set_c)` in both runners; `_ASSUMPTION_PAIR_STRIDE` leaked into 3 conacq files; `print()` = 254 apps / 48 conacq+explanation; profiler.py 1150 LOC; Oracle empty stubs `get_variables`/`complete_configuration`; transformations untested; performance_metrics.py 652 LOC / `_stat4`×25; redundancy ops inherit-then-stub; 2 sat4j clones; 3rd encoder `to_literals`; unseeded global RNG in 4 generator files; 5 labelers + 2 twin pairs; bias_generator 295 / clause_generator 199 LOC.
**Drift (minor, non-blocking):** profiler import sites 34 (brief said 37); `_stat4`×25 (brief ~30); the uncommitted `fm_oracle.py` fix already routes `_model_to_config`→codec, so C5's live duplication is `to_literals` vs codec only.

## Red-team review (applied 260621)

3 adversarial reviewers (sequencing / test-safety / regression) stress-tested the plan; findings verified against live code and folded into the phase files. Report: `plans/reports/from-red-team-to-planner-260621-redesign-abc-review.md`. Two cross-cutting corrections:
- **test_diagnosis ownership (was unowned):** A7 must NOT defer its migration to "a B-phase". test_diagnosis exercises SAT4J (A3), profiler (B2), qx/wipeoutr/labelers (C7), redundancy ops (C3) — so **every phase changing a diagnosis symbol updates test_diagnosis in-stage**; the `@parameterized.expand`→pytest migration is owned by **C7**. Without this the suite goes red at end of A3 (A3 deletes sat4j classes test_diagnosis imports).
- **C2 stale reference corrected:** the "5th inline metrics path" is NOT in `progressive_evaluation.py` (brief's `:315-325` is wrong); real `EvaluationMetrics(` sites are `kb_comparator.py:163/319`, `metrics.py:144`, `accuracy.py:117`. C2 re-scouts these.
- **Highest residual regression risk = B4** (FMOracle map-move vs the landed codec fix — ordering cycle + 5 unlisted reader/test sites, now widened in phase-10).

## Validate interview (resolved 260621)

- **Data/export compat** → API-only break; on-disk JSON + CSV/LaTeX exports FROZEN (paper pipeline depends). Encoded as an inviolable principle above + C2/C4/A6/B4 requirements.
- **B4 approach** → full restructure (`prepare()` hands maps directly to `prepare_task()`/codec, no model round-trip) — kills the ordering cycle. phase-10.
- **Commit cadence** → commit per green stage, 1 PR at end. Principle above.
- **dimacs_to_configuration.py** → confirmed deletable; removed in C6 (phase-18).

## Dependencies

- Cross-plan: `plans/260216-1425-bias-package-refactoring/` (status: **complete**) earlier touched `bias_generator.py` / `config_loader.py` / `bias_io.py` — now C4/C6 targets. Not a blocker; C4/C6 MUST read its reports first to avoid undoing intentional decisions.
- External baseline: Phase R (`plans/260618-phase-r-task-as-unit/`, merged). This plan extends, never reverts it.
