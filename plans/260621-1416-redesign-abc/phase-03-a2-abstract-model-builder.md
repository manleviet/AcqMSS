---
phase: 3
title: A2 abstract model builder
status: completed
priority: P1
effort: 1d
dependencies:
  - 1
---

# Phase 3: A2 — abstract model builder

## Overview
Extract `AbstractModelBuilder` base for the fluent `from_*`/`with_oracle`/`with_negation`/`build` skeleton duplicated verbatim across 3 builder pairs (Diagnosis / ConGen / QuAcq). Subclasses supply only KB construction + negation source. The `last_task` side-channel is NOT removed here — that is B4 (kept separate so this stage is a pure DRY extraction).

## Requirements
- Functional: shared base implements the fluent skeleton; ConGen/QuAcq/Diagnosis builders inherit; behavior identical.
- Non-functional: base lives where it can serve all three without creating a `conacq`→`explanation` private leak (Diagnosis builder is in `explanation/`; ConGen/QuAcq in `conacq/`). Decide base location so the shared skeleton is framework-side and conacq subclasses extend the public form — coordinate with B1. If base must be public-surface, stub the import now and finalize in B1.

## Architecture
- `AbstractModelBuilder` with template methods: `from_bias`/`with_oracle`/`with_negation`/`build`; abstract hooks for KB build + negation source.
- Verbatim blocks to collapse: `congen_model_builder.py:108-122` ≈ `quacq_model_builder.py:57-71`.

## Related Code Files (verified)
- Create: `AbstractModelBuilder` (location TBD in step 1 — likely `explanation/models/` for the skeleton)
- Modify: `explanation/models/diagnosis_model_builder.py`
- Modify: `conacq/algorithms/acqmss/congen_model_builder.py`
- Modify: `conacq/algorithms/quacq/quacq_model_builder.py`
- Rewrite affected builder tests within this stage (A7 fixtures)

## Implementation Steps
1. Decide base location (avoid private cross-boundary import; prefer a surface-able framework base). Document the choice.
2. Implement base with the fluent skeleton + abstract hooks.
3. Re-point the 3 builders to inherit; delete the verbatim `from_*`/`with_*` duplicates; leave `last_task` in place (B4).
4. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One `AbstractModelBuilder`; 3 builders inherit; no duplicated fluent skeleton
- [ ] Negation-at-build copy removed (single implementation)
- [ ] No new `conacq`→`explanation` underscore import introduced (or stubbed for B1 with a note)
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Base location is now a HARD requirement** (resolves the waffly success criterion): base lives at `explanation/models/abstract_model_builder.py` and is re-exported from `explanation/models/__init__.py` IN THIS PHASE. `explanation.models` is the de-facto public surface (not an underscore/deep-private path), so the B1 guard tolerates the conacq subclass import. B1 then only folds it into `api.py` — no move, no rework. Without this pin, A2 may hide the base in a private module and B1 must relocate it + every import.

## Risk Assessment
- Base location risks creating a boundary leak that B1 must then unwind — mitigate by choosing a public-surface-compatible location now and recording the decision for B1.
- `last_task` interplay — explicitly out of scope here; do not touch its contract until B4.
