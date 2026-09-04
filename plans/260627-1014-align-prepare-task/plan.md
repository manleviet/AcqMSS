---
title: Align conacq prepare_task signatures with explanation
description: >-
  Unify ConGen/QuAcq/FMOracle prepare_task to prepare_task(task_input:
  TaskInput) -> Task; a frozen oracle BG-snapshot is folded onto the model at
  build.
status: completed
priority: P2
branch: feat/redesign-abc
tags: []
blockedBy: []
blocks: []
created: '2026-06-27T10:11:43.802Z'
createdBy: 'ck:plan'
source: skill
---

# Align conacq prepare_task signatures with explanation

## Overview

**Context / why.** After redesign A+B+C, `DiagnosisModel.prepare_task(task_input: TaskInput) -> Task`
is the canonical KB→Task entry. The three conacq KB models diverge, forcing every caller to know a
per-model convention and to thread `oracle` by hand:

| Model | Current (tip) | Target |
|---|---|---|
| `DiagnosisModel` | `prepare_task(task_input=None) -> Task` | (reference — unchanged) |
| `ConGenModel` | `prepare_task(task_input, oracle) -> ConGenTask` | `prepare_task(task_input) -> ConGenTask` |
| `QuAcqModel` | `prepare_task(oracle) -> QuAcqTask` | `prepare_task(task_input=None) -> QuAcqTask` (rejects non-empty) |
| `FMOracleModel` | `prepare_task(configuration=None) -> DiagnosisTask` | `prepare_task(task_input=None) -> DiagnosisTask` |

**Mechanism (revised after red-team).** Do NOT stash the live oracle on the model — that reverses the
documented "Oracle injected at prepare_task(), **not stored in model**" contract
(`docs/system-architecture.md:699,752`, `docs/codebase-summary.md:509`) and puts a live SAT solver on the
"immutable KB" model. Task preparation only needs *pure snapshot reads* of the oracle
(`get_bg_data`, `get_c`, `get_kb`, `get_assumptions` — all read `oracle._base_task`/`bg_data`). So define a
**frozen `OracleTaskData`** carrier, build it once from the oracle at model build, and stash THAT on the
model. `prepare_task` reads `self._oracle_data`; `GenerateNE` and the conacq preparations are re-typed to
the carrier. Result: model stays pure immutable data, signature unified, no live-resource coupling.

## Verify-at-tip findings (drive this plan)

- **Item (2) "split FMOracleModel" is ALREADY DONE (B4).** `FMOracleModel` is a thin KB container with zero
  oracle methods; `FeatureModelOracle.__init__` already composes it (`self._oracle_model = FMOracleModel
  .from_fm(...).build()`). → **User decision: DROP item (2).**
- `builder.last_task` / FMOracle self-mutation: **already gone** (grep-clean).
- **Safety-net gap is BROADER than first thought:** existing tests pin `set_c/set_tc/set_tv/set_b/assumptions`
  via `test_assumption_slicer.py`, BUT **`set_neg_tv`/`negation_map` are NOT pinned end-to-end** and the only
  ConGen fixture has **zero negative examples**. Phase 1 closes this with a negative-example fixture.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Oracle + task-content safety-net](./phase-01-oracle-safety-net.md) | Completed |
| 2 | [Unify FMOracleModel](./phase-02-unify-fmoraclemodel.md) | Completed |
| 3 | [OracleTaskData snapshot + ConGenModel](./phase-03-unify-congenmodel.md) | Completed |
| 4 | [Unify QuAcqModel](./phase-04-unify-quacqmodel.md) | Completed |
| 5 | [Docs sweep (incl. docs/) + report](./phase-05-docs-sweep-and-report.md) | Completed |

## Scope / non-goals

- **In:** unify the 3 signatures; frozen `OracleTaskData` snapshot folded onto the model at build; re-type
  `GenerateNE`/preparations to the carrier; update every call-site (runners, tests, builder/__init__/README +
  **docs/**); extend safety-net to ConGen/QuAcq task content.
- **Out (deliberate):** NO Operation facade for ConGen/QuAcq; NO FMOracleModel rename/collapse (item 2 dropped);
  NO back-compat aliases.

## Global rules (every phase)

- Behavior-preserving: diagnoses/results/metrics unchanged; no weakened assertions.
- Sequential; after EACH phase `uv run --no-sync pytest tests/ -q` green before the next; test count must not
  drop. Per-phase split kept intentionally for green-gate isolation (rejects red-team "collapse to 3").
- No PR. Out-of-plan issues → record + ask.
- Commit per phase (conventional, no plan-artifact refs).

## Verification (end-to-end)

`uv run --no-sync pytest tests/ -q` green after every phase; final
`grep -rn "\.prepare_task(.*oracle" conacq/ tests/ apps/ docs/ README.md` returns **empty** (no model-level
call passes oracle). Final report under this dir per item: verify-at-tip + change + files touched + oracle
behavior-preserving evidence (Phase-1 net green pre/post).

## Red Team Review

### Session — 2026-06-27 (3 hostile reviewers: Assumption Destroyer, Failure Mode Analyst, Scope/Complexity Critic)
**Findings:** 13 unique (11 accepted into phases, 2 escalated to user decision). **Severity:** 4 High, 6 Medium, 3 Low.
**Core mechanism survived:** call-site inventory complete (no missed caller); runner uses one oracle instance
(identity safe); item (2) "already split" confirmed.

| # | Finding | Sev | Disposition | Applied To |
|---|---------|-----|-------------|------------|
| 1 | Whole-oracle stash reverses documented "not stored in model" contract + live solver on immutable model | High | **User → frozen snapshot** | Completed |
| 2 | "Unified" signature hides disjoint contracts; QuAcq silently drops TaskInput | High | **User → reject non-empty** | Completed |
| 3 | Safety-net under-scoped: no ConGen/QuAcq task-content pin; `set_neg_tv` + negative-example path uncovered | High | Accept | Completed |
| 4 | Phase-5 docs sweep misses ~22 stale `prepare_task(...,oracle)` examples across 6 `docs/` files | High | Accept | Completed |
| 5 | Stash via raw base-`build()` injection → undeclared-attr window; use `_post_negation_build` hook + declare field both models | Med | Accept | Completed |
| 6 | Oracle-identity (`model._oracle_data` derived from runner's oracle) unasserted | Med | Accept | Phase 3,4 |
| 7 | Shared `test_assumption_slicer.py` split across phases → cross-boundary edit hazard | Med | Accept | Phase 3,4 |
| 8 | Phase-2 re-plumbs a provably-dead `configuration` path | Med | Accept (cut it) | Phase 2 |
| 9 | Phase-5 grep gate can't match what it claims; broaden to `\.prepare_task(.*oracle` over apps/+docs/ | Med | Accept | Phase 5 |
| 10 | `_oracle`-None guard unreachable (`build()._validate` already enforces) — inverted risk text | Low | Accept (reframe) | Phase 3,4 |
| 11 | Phase-1 invalid-config derivation brittle (hand-authored/mandatory-violation) | Low | Accept | Phase 1 |
| 12 | README:105 already TypeErrors today (pre-existing doc rot) | Low | Accept (note) | Phase 5 |
| 13 | 5-phase over-split | Med | Reject | — (per-phase green-gates intentional) |

### Whole-Plan Consistency Sweep
Mechanism changed whole-oracle → frozen `OracleTaskData` snapshot across plan.md + all phases; "stored on
model" prose reconciled (model holds a frozen BG snapshot, not the live oracle). Phase 5 now updates the 3
documented contract lines to match. No unresolved contradictions.

## Dependencies

None. Sits on `feat/redesign-abc` after `9c32bfb`.
