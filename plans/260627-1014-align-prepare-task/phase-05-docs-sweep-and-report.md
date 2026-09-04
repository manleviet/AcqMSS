---
phase: 5
title: Docs sweep (incl. docs/) + report
status: completed
priority: P3
effort: 2h
dependencies:
  - 4
---

# Phase 5: Docs sweep (incl. docs/) + report

## Overview

Final consistency sweep. Red-team #4: the old `prepare_task(...,oracle)` signature appears in **~22 examples
across 6 `docs/` files** plus README, and the documented contract "Oracle injected at prepare_task(), not
stored in model" must be rewritten to reflect the new mechanism (frozen BG snapshot folded at build). Then
the grep gate (broadened) and the completion report.

## Requirements

- Functional: zero remaining old-signature examples anywhere (conacq/, tests/, apps/, docs/, README).
- Non-functional: documented immutable-KB contract statements updated to "frozen OracleTaskData snapshot
  folded at build; prepare_task takes only TaskInput" — honest, not contradictory.

## Architecture

Pure documentation + verification.

## Related Code Files

- Modify: `README.md` (`:69-72` ConGen, `:105` QuAcq — note `:105` already TypeErrors today, red-team #12)
- Modify (docs examples — verified stale): `docs/system-architecture.md`
  (`:75,99,245,253,646,679,708,748` + contract lines `:645,699,752`), `docs/codebase-summary.md`
  (`:24,141,505,509`), `docs/congen.md` (`:141,333,341,381,386`), `docs/quacq.md` (`:208,357`),
  `docs/code-standards.md` (`:205,380,404,499`), `docs/README.md` (`:185`)
- Verify-only: `conacq/oracle/__init__.py` (now also exports `OracleTaskData`),
  `conacq/algorithms/acqmss/__init__.py`, `conacq/algorithms/quacq/__init__.py` (FMOracleModel /
  FeatureModelOracle / ConGenModel / QuAcqModel exports unchanged — item 2 dropped)
- Create: `plans/260627-1014-align-prepare-task/completion-report.md`

## Implementation Steps

1. Update README ConGen + QuAcq examples to `model.prepare_task(task_input)` / `model.prepare_task(TaskInput())`.
2. Update the ~22 `docs/` examples to the new signature; **rewrite the 3 contract statements**
   (`system-architecture.md:645,699,752`, `codebase-summary.md:509`) to: "ConGen/QuAcq models fold a frozen
   `OracleTaskData` BG snapshot at build; `prepare_task(task_input)` takes no oracle. The live oracle is not
   stored on the model."
3. Grep gate (broadened, red-team #9): `grep -rn "\.prepare_task(.*oracle" conacq/ tests/ apps/ docs/ README.md`
   → must be **empty** (no model-level call passes oracle). Internal `Preparation.prepare(... snapshot)` calls
   use `.prepare(`, not `.prepare_task(`, so they don't match.
4. Confirm exports: `OracleTaskData` added; the four model/oracle names unchanged.
5. Whole-plan consistency: re-read plan.md + all phases; reconcile any "stored oracle" vs "snapshot" drift.
6. Final full-suite green run; record the number.
7. Write `completion-report.md`: per item (1)(2)(3-dropped) → verify-at-tip + change + files touched + oracle
   behavior-preserving evidence (Phase-1 net green pre/post). List unresolved questions.

## Success Criteria

- [ ] README + all `docs/` examples + the 3 contract statements reflect the snapshot mechanism.
- [ ] Broadened grep gate clean across conacq/ tests/ apps/ docs/ README.
- [ ] Exports correct; full suite green (≥ baseline + safety-net count).
- [ ] completion-report.md written. No PR opened.

## Risk Assessment

- Risk: a docs example missed → teaches the removed API. Mitigation: the docs/-inclusive grep gate (step 3).

## Next Steps

STOP. No PR. Report path returned to user.
