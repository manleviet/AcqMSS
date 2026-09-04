# Code Review — A1 Unify Assumption-Slicer

Date: 2026-06-21
Reviewer: code-reviewer
Branch: feat/redesign-abc
Scope: uncommitted working-tree changes (5 src files) + new `tests/test_assumption_slicer.py`
Verdict: **PASS** · Status: **DONE**

## Scope
- Files changed (5): `explanation/models/task_preparation.py`, `explanation/models/__init__.py`,
  `conacq/algorithms/acqmss/task_preparation.py`, `conacq/algorithms/quacq/task_preparation.py`,
  `conacq/oracle/fm_oracle_model.py`
- New tests: `tests/test_assumption_slicer.py` (24 tests, all green)
- Net: +53 / −25 across 5 files
- Full suite: **376 passed, 1 warning** (52s) — warning is the known pre-existing `TestSuiteReader` PytestCollectionWarning. Flaky `test_executor` parity test passed this run.

## Overall Assessment
Clean, low-risk, behavior-preserving consolidation. All 5 inline stride/offset slices now route through one
`slice_assumptions(assumptions, start, stop, stride)` helper that is literally `list(a[start:stop:stride])`.
Equivalence to the prior `range()`/comprehension/slice forms was proven exhaustively (200k randomized shapes,
all 10 distinct slice expressions identical). Characterization tests pin EXACT set contents at every site/branch.
No CRITICAL/HIGH issues. Two LOW items below are cosmetic.

## VERIFY checklist results

### 1. Behavior-preserving (CRITICAL) — PASS
Walked all 5 sites before→after; brute-forced equivalence over 200k randomized inputs (n=0..30, stride∈{1,2},
randomized start/stop). Zero mismatches. Key subtlety confirmed safe: `[a[i] for i in range(start, stop, step)]`
== `list(a[start:stop:step])` even when `stop` is NOT stride-aligned — both stop strictly before `stop`.

| Site | Before | After | Equivalent |
|------|--------|-------|------------|
| DiagnosisTask set_b (cfg, !cf_in_c) `:456` | `[a[i] for i in range(0,start_id_config,step)]` | `slice(a,0,start_id_config,stride)` | yes |
| DiagnosisTask set_c (cfg, cf_in_c) `:461` | `[a[i] for i in range(step,start_id_config,step)] + a[start_id_config:]` | `slice(a,stride,start_id_config,stride) + a[start_id_config:]` | yes |
| DiagnosisTask set_c (test_case) `:467` | `[a[i] for i in range(step,start_id_config,step)]` | `slice(a,stride,start_id_config,stride)` | yes |
| DiagnosisTask set_c (redundancy) `:471` | `a[step:len(a):step]` | `slice(a,stride,None,stride)` | yes |
| DiagnosisTask set_c (fm+root) `:475` | `[a[i] for i in range(step,len(a),step)]` | `slice(a,stride,None,stride)` | yes |
| TestCaseTask original_tc_tv `:590` | `tc_tv=a[start_id_tc:]; [tc_tv[i] for i in range(0,len(tc_tv),2)]` | `slice(a,start_id_tc,None,2)` | yes |
| ConGen set_c `acqmss:233` | `a[bias_start_id:start_id_tc:2]` | `slice(a,bias_start_id,start_id_tc,2)` | yes |
| ConGen original_tc_tv `acqmss:236` | `tc_tv=a[start_id_tc:]; [tc_tv[i] for i in range(0,len(tc_tv),2)]` | `slice(a,start_id_tc,None,2)` | yes |
| QuAcq set_c `quacq:132` | `list(a[bias_start_pos::2])` | `slice(a,bias_start_pos,None,2)` | yes |
| FMOracle _base_set_c `fm_oracle_model:198` | `[a[i] for i in range(0,assignments_start_index,2)]` | `slice(a,0,assignments_start_index,2)` | yes |

`num_tc_original` / `set_tc` / `set_tv` split arithmetic at TestCaseTask `:592` and ConGen `:238` is UNCHANGED
(still `(start_id_tv-start_id_tc)//2` then `original_tc_tv[:n]` / `[n:]`). FMOracle `set_c` defensive copy
(`list(model._base_set_c)`) and config-append (`_base_set_c + config_assumptions`, non-mutating) preserved.

### 2. Characterization quality — PASS
24 tests assert EXACT set contents (concrete ID lists), not lengths/presence alone. Coverage:
- Site 1 DiagnosisTask: all 5 branches × both stride modes — redundancy (paired), fm-diag (single), cfg/!cf_in_c
  (single + paired), cfg/cf_in_c (single), test_case (single + paired w/ redundancy). Both `with_cf_in_c` values covered.
- Site 2 TestCaseTask: pos+neg and pos-only; pins set_b/set_c/set_tc/set_tv AND set_neg_tv exact IDs.
- Site 3 ConGen (arcade-game, large): set_b/set_c (len 1755, first-5 + uniform-stride-2 invariant)/set_tc/set_tv.
- Site 4 QuAcq (REAL-FM-7): set_b/set_c (len 295, first-5 + stride invariant)/Part3+Part4 layout.
- Site 5 FMOracle `_base_set_c`: arcade + REAL-FM-7, length/first-values/last-values/stride + disjointness from Part4.
- Safety-net: `OracleAwareTaskPreparation._copy_bg_data_part3` integration pinned (assumptions, negation_map,
  set_kb clauses) + ConGen/QuAcq end-to-end set_b.

Verified non-no-op: mutation probe on Site 3 + Site 4 fixture-backed assertions → both FAIL when expected IDs
altered, confirming the `@pytest.fixture`+`@classmethod` fixtures deliver a real task and assertions execute.
All data files present → **0 skips** (the `pytest.skip` guards are dead-but-harmless).

No unpinned branch found.

### 3. No weakened assertions — PASS
All assertions are exact-equality on concrete ID lists or exact lengths + stride invariants. Nothing loosened to
`>=`, `in`, truthiness, or length-only. Stride-2 invariant tests (all consecutive diffs == 2) are a strengthening,
not a weakening.

### 4. Boundary — PASS
- `grep _ASSUMPTION_PAIR_STRIDE|_ASSUMPTION_SINGLE_STRIDE conacq/` → empty. Constant no longer crosses boundary.
- Both constants still defined + used only in `explanation/models/task_preparation.py` (`:34/:35`, used `:451`,
  and `_ASSUMPTION_PAIR_STRIDE` at `:590/:592`).
- `slice_assumptions` lives in `explanation/`, exported via `explanation/models/__init__.py` (import + `__all__`).
- Framework changes confined to `explanation/`; conacq changes confined to `conacq/`. No app-layer churn.

### 5. Is the slicer meaningful dedup or too-thin wrapper? — Verdict: KEEP (earns its place)
It is a one-liner, but it earns inclusion for three concrete reasons, all realized in this diff:
1. **Names the operation** — "select originals from paired layout (stride=2)" is the domain's most error-prone
   primitive; the plan calls it "4 copies = 4 places a stride bug hides". One change-point is real value.
2. **Removes the cross-package leak** — conacq sites drop `_ASSUMPTION_PAIR_STRIDE` import entirely (B1 leak-removal
   shrinks to zero), keeping the stride constant internal to `explanation`.
3. **Single audit surface** — replaced 3 different inline idioms (`range()` comprehension, `[a:b:2]`, `[p::2]`) with
   one call shape; future stride/off-by-one review happens in one function.

YAGNI/KISS respected: NOT recommending a heavier "section-offset" abstraction. The per-task section boundaries
(start_id_config / start_id_tc / start_id_tv / assignments_start_index) genuinely differ per task type and live at
the call sites where they belong — there is no duplicated offset-computation logic to extract. A thin strided-slice
helper is the right granularity.

### 6. No regression to callers — PASS
- DiagnosisTask / TestCaseTask / ConGen / QuAcq prep: full suite 376 passed.
- FMOracle `_base_set_c` readers (`fm_oracle.py:106`, `:192` — both read via copy, non-mutating) unaffected;
  value byte-identical to before.
- Slicer edge cases match native slicing exactly: empty list → `[]`, start>len → `[]`, stop=0 → `[]`,
  single+stride2 → `[x]`, defaults → whole list.

## Findings by severity

### CRITICAL — none
### HIGH — none
### MEDIUM — none

### LOW
- **L1 — `@classmethod` on pytest fixtures is redundant/non-idiomatic.**
  `tests/test_assumption_slicer.py:294-296` (`congen_task`) and `:356-358` (`quacq_task`) stack
  `@pytest.fixture` over `@classmethod`. It works here (proven by mutation probe — pytest calls the fixture and
  `cls` binds to the class), but `@classmethod` is unnecessary noise and can confuse future readers / break under
  fixture-ordering refactors. Fix: drop `@classmethod`, keep a plain method `def congen_task(self):` (pytest passes
  the instance). Non-blocking; tests pass as-is.
- **L2 — Stylistic asymmetry: explanation uses named constant, conacq uses literal `2`.**
  Intentional per the red-team adjustment (conacq passes literal int to avoid importing the constant; constant stays
  internal to explanation). Correct, but a one-line code comment at the conacq sites noting "stride=2 = original-only
  from paired [orig,neg,...] layout" already exists, so this is fine. No change required — documented for awareness.

## Positive Observations
- Equivalence is provable, not assumed — `range(start,stop,step)` vs slice semantics handled correctly at the one
  spot it could bite (non-stride-aligned `stop`).
- Characterization-before-swap discipline followed: exact IDs on small + large FMs (arcade-game 71c, REAL-FM-7 14c).
- Defensive-copy and non-mutating-concat semantics on `_base_set_c` preserved exactly — no new aliasing risk.
- Docstring on `slice_assumptions` documents the paired-layout intent and the constant-internalization rationale.
- Stride-uniformity invariant tests (all diffs==2) are a strong, cheap guard against future stride regressions.

## Recommended Actions
1. (LOW, optional) Drop `@classmethod` from the two fixtures (L1) for idiomatic pytest. Not a merge blocker.
2. Commit A1 as-is — quality gate passed.

## Metrics
- Tests: 376 passed / 0 failed / 0 skipped in slicer file / 1 known warning
- New tests: 24, all exact-content assertions, mutation-verified non-no-op
- Slice-equivalence: 10/10 expressions identical across 200k randomized shapes
- Type coverage: slicer fully annotated (`List[int]`/`Optional[int]` imports present)
- Boundary leak: 0 stride-constant references in conacq

## Unresolved Questions
None.
