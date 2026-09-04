---
phase: 7
title: A5 logging + error-handling hygiene
status: completed
priority: P2
effort: 1d
dependencies:
  - 1
---

# Phase 7: A5 — logging + error-handling hygiene

## Overview
Replace the remaining 48 `print()` in `conacq`+`explanation` with module loggers; fix traceback-losing re-raises (`raise ... from e`); decide-and-document the swallowed speculative-check exception in the executor. Closes the observability gap Phase R left.

## Requirements
- Functional: loggers instead of print (except legitimate interactive `user_prompt` prompts); chained exceptions; the executor swallow either handled or explicitly documented with rationale.
- Non-functional: no behavior change beyond logging/error propagation; framework loggers stay inside `explanation/`.

## Architecture
- Per-module `logger = logging.getLogger(__name__)`.
- `executor.py:285` swallow: decide (a) log + continue (if speculative-check failure is expected/benign) or (b) propagate — document the chosen invariant in a code comment (no plan-reference in the comment).

## Related Code Files (verified)
- Modify (print→logger): `explanation/operations/algorithms/profiler.py`, `explanation/.../fastdiag.py`, `explanation/.../quickxplain.py`, `conacq/bias/bias_generator.py` (:239-259, 5 prints), and the rest of the 48 sites (20 conacq + 28 explanation)
- Keep prints: `conacq/oracle/user_prompt.py` (interactive)
- Modify (error handling): `explanation/operations/algorithms/checker.py` (`raise RuntimeError(...)` :225 → add `from e`); `explanation/.../executor.py` (:285 swallow)

## Implementation Steps
1. Sweep `conacq`+`explanation` for `print(`; convert to logger calls (skip user_prompt interactive).
2. Add `from e` to bare re-raises; grep for `raise .*Error(` without `from`.
3. Resolve executor.py:285 swallow; document invariant in-code (reason, not origin).
4. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] `print()` = 0 in `conacq`+`explanation` (except interactive user_prompt)
- [ ] No traceback-losing re-raise (checker.py:225 chained)
- [ ] executor.py:285 swallow resolved + documented
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Blind-edit window guard:** `cached.py`/`user_prompt.py`/`ground_truth.py` are untested until B3 (phase 9, after this stage). A5's edits to them are LOGGING-substitution only — NO control-flow change — until their safety-nets land in B3.

## Risk Assessment
- Changing the executor swallow could surface a previously-hidden failure → if propagating breaks a test, that test encodes the intended swallow — then log+continue and document why (don't weaken the test).
