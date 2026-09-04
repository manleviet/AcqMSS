---
phase: 18
title: C6 bias/clause generator cleanup + dead code
status: completed
priority: P3
effort: 1d
dependencies:
  - 11
  - 16
---

# Phase 18: C6 — bias/clause generator cleanup + dead code

## Overview
Final cleanup: deep-read and clean `bias_generator.py` (295 LOC) + `clause_generator.py` (199 LOC) — both flagged for review but not yet deep-read in the scan; remove dead commented code (`testsuite.py:36/:45-46/:75-76`, `reduce.py:83` commented `paper_consistency_checks` increment). Last stage so it sits on the fully cleaned base.

## Cross-plan note
`bias_generator.py` was touched by the completed `260216-1425-bias-package-refactoring` plan — read its `phase-01-refactor-bias-generator.md` + reports before further refactoring (same guard as C4).

## Requirements
- Functional: bias_generator/clause_generator simplified per logical-separation boundaries (modularize if >200 LOC threshold per repo convention); dead comments removed; `reduce.py:83` intent decided (remove or restore with a clear comment — it currently affects a profiler metric count).
- Non-functional: no behavior change; bias print()s already handled in A5 — verify none reintroduced.

## Architecture
- Deep-read first to find real separation boundaries; modularize only where it improves cohesion (KISS/YAGNI — don't over-split).

## Related Code Files (verified)
- Modify: `conacq/bias/bias_generator.py` (295), `conacq/bias/clause_generator.py` (199)
- Modify (dead code): `explanation/.../testsuite.py` (:36/:45-46/:75-76), `conacq/algorithms/acqmss/reduce.py` (:83 commented increment)

## Implementation Steps
1. Read prior bias-package-refactoring artifacts for bias_generator.
2. Deep-read bias_generator + clause_generator; identify cohesion boundaries; simplify/modularize as warranted.
3. Decide `reduce.py:83` intent (metric correctness) — remove the dead comment or restore the increment with a why-comment (no plan-reference).
4. Remove `testsuite.py` dead comments.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] bias_generator/clause_generator deep-read + simplified (no dead/duplicated logic)
- [ ] Dead comments removed (testsuite.py, reduce.py:83 resolved)
- [ ] `reduce.py:83` intent decided + documented
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Add dead-code deletion (routed from B1):** DELETE `explanation/transformations/dimacs_to_configuration.py` — zero importers confirmed. Re-verify no importer reappeared after B1's import rewrite, then remove. (Also re-check `dimacs_to_diag_pysat.py` DIMACS-parse duplication noted in the scan while here.)

## Risk Assessment
- `reduce.py:83` touches a profiler metric (`paper_consistency_checks`) — decide intent deliberately; if unclear whether the metric should count, FLAG to user rather than silently removing/restoring.
- Over-modularizing small generators → respect KISS; split only on real boundaries.
