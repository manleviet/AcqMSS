# C7 Review — Labeler Template Base + test_diagnosis Migration (Twins Kept Separate)

**Scope:** working-tree changes only (`git diff`), branch `feat/redesign-abc`.
**Files:** 6 (4 labelers + base + qxtc algorithm) + `tests/test_diagnosis.py`.
**Suite:** `uv run --no-sync pytest tests/ -q` → **509 passed, 0 warnings, 0 failures** (53s, no flaky hit).
**Verdict:** **PASS.**

---

## VERDICT on the critical item (2): test_diagnosis — NO weakened matrix. CONFIRMED.

Hard-evidence checks:

- **Case count:** old `tests/test_diagnosis.py@HEAD` collects **206**; new working-tree collects **206**. Verified by `pytest --collect-only` on both (old copied to temp path, `parameterized` still installed). Exact match.
- **Test functions:** 35 in both; sorted name sets **diff-empty** (identical 35 names).
- **Assertions:** all **46** assert lines are **byte-identical** after whitespace normalization (old 12-space unittest indent → new 8-space module indent is the only delta). No `==` loosened, no exact expected-string changed, no `len()>0 / >=1 / ==2` weakened.
- **No no-ops:** zero commented-out asserts, zero `assert True`/`assert 1`, zero unconditional `pytest.skip`/`@pytest.mark.skip`.
- **Param sources preserved:** old = 34 STANDARD_PARAMS + 1 SAT4J_ONLY_PARAMS; new = 34 STANDARD + 1 SAT4J_ONLY on the 35 parametrize decorators. The lone SAT4J-only test is `test_hsdag_quickxplain_all` in BOTH — same test, same param source. No test silently narrowed.
- **sat4j params run:** present in collection (`sat4j_with_profiling`, `sat4j_no_profiling`).
- **ENABLED dicts + 3 helper builders:** byte-identical old↔new. Only the skip helper changed: `_skip_disabled` (`unittest.skipIf`) → `_skip_if_disabled` (`pytest.mark.skipif`), condition `not ENABLED_TESTS.get(name, True)` preserved (NOT inverted; same default-enabled).
- **TestSuiteReader:** aliased `as _TestSuiteReader` (import + all 9 call sites). 0 warnings on full run confirms the PytestCollectionWarning is gone.

The 206→206 claim is accurate and the matrix is fully intact.

---

## Item-by-item

**(1) Labeler base behavior-preserving — PASS.**
- `get_type` now reads `self._labeler_type`; `get_initial_parameters` returns `self.initial_parameters`. Both moved to base as concrete (de-`@abstractmethod`'d). The 3 genuinely-varying methods (`get_label`, `identify_new_node_parameters`, `get_instance`) remain `@abstractmethod`; `IHSLabelable` stays an un-instantiable ABC.
- `_labeler_type` set correctly: fastdiag/kbdiag = DIAGNOSIS, qx/qxtc = CONFLICT (`labeler.py:27,30 / 27 / 53`).
- Only 4 concrete labelers exist (spec says "5" — counts the base). No labeler lost a method: each keeps `__str__`, `__init__`, `get_label`, `identify_new_node_parameters`, `get_instance`; qxtc additionally keeps `_copy_tc_without_testcases_before`.
- Arities intact: qx labeler calls `find_conflict` (single return); qxtc labeler calls `find_conflict_set` (`test_case, conflict_set` two-tuple, unwrapped). Both consumed by `hsdag.py:51,59` via `get_type()`.
- No dead imports: `LabelerType` still used as class-attr value; `AbstractHSParameters` still in signatures (5 refs each). All files byte-compile clean.

**(3) Metric keys — UNCHANGED. CONFIRMED.** All 4 twin key sets intact and the twin algorithm files are NOT in the diff (genuinely separate):
- `qx_calls`/`qx_runtime` (quickxplain.py:61-62)
- `qx_with_testcases_calls`/`_runtime` (quickxplain_with_testcases.py:137-138)
- `wipeoutr_fm_calls`/`_runtime` (wipeoutr_fm.py:43-44)
- `wipeoutr_t_calls`/`_runtime` (wipeoutr_t.py:50-51)
The qxtc diff touches **docstrings only** (decorator-change grep returned empty); `quickxplain.py`, `wipeoutr_fm.py`, `wipeoutr_t.py` are working-tree-clean.

**(4) No weakened assertions / no plan labels / scope / green / 0 warnings — PASS.**
- Plan-stage labels in added lines: **none** (grep for C7/phase/F-codes/red-team/audit/SEQ-1 over added lines = empty; complies with no-plan-refs-in-code rule).
- Scope is framework + test only.
- Suite 509 green, 0 warnings.

**qxtc `find_conflict_set` docstring fix — correct.** Docstring changed `(None, Φ)` → `([], Φ)` to match the actual code, which already returns `[], []` (lines 101/115/123) and wraps `test_case` to a list (`if not isinstance(test_case, list): test_case = [test_case]`, line 133-135). The new docstring accurately documents "both elements always List; callers unwrap via `test_case[0]`." No behavior change.

---

## Findings

### Critical
None.

### High
None.

### Medium
None.

### Low

**L1. Stale docstring in base — references a method that does not exist.**
`labeler.py:35-37` claims three bookkeeping methods are provided: "`get_type` / `get_initial_parameters` / `_assert_param_type` are provided here as concrete templates." But `_assert_param_type` exists **nowhere** in the codebase (grep `explanation/ tests/` = only this docstring line + stale .pyc). Each labeler still hand-rolls its own `assert isinstance(...)` at the top of `get_label`/`identify_new_node_parameters`.
- *Impact:* misleading to future maintainers; implies a shared assertion helper that isn't there.
- *Fix:* drop `/ _assert_param_type` from the docstring (labeler.py:36), OR — if the assertion-helper was the intended extraction — actually add `_assert_param_type` and route the 4 labelers' `assert isinstance` calls through it. The former (doc-only) is the YAGNI choice; the duplicated isinstance asserts are cheap and self-documenting.

**L2. `_labeler_type: LabelerType = None` type annotation is unsound (cosmetic).**
`labeler.py:41` annotates the default as `LabelerType` but assigns `None`. Should be `Optional[LabelerType] = None` (or `ClassVar[Optional[LabelerType]]`). No runtime effect; the `# type: ignore` on line 49 suggests typing isn't strictly enforced here anyway. Fix only if a type-checker runs in CI.

---

## Advisory (item 5)

**Is the 2-method labeler-base extraction worth it, or trivial churn?**
Marginal but net-positive — keep it. It removes ~8 lines × 4 = ~32 lines of identical boilerplate and centralizes the `_labeler_type` contract. It's not the "~200-line" DRY win the spec headline promised (the `*Parameters.__str__` fold and `identify_new_node_parameters` fold did NOT happen — correctly, see below), so the realized payoff is modest. Given it's behavior-preserving and suite-green, the churn is justified; not worth reverting.

**Do you AGREE `identify_new_node_parameters` should stay per-labeler? YES — verified.**
The four implementations genuinely diverge: different assertion class per labeler; quickxplain (conflict) skips the C→B append entirely (B unchanged for conflict labelers); kbdiag adds `set_tcp` propagation + different constructor; qxtc filters test cases via `_copy_tc_without_testcases_before` + stores `test_case`. Folding into one template would require parameterizing the append-behavior, the param class, and the test-case propagation — exactly the kind of conditional-laden "template" that's harder to read than 4 honest small methods. Keeping per-labeler is correct (KISS over forced DRY).

**Also not folded: `*Parameters.__str__`.** The spec listed these as a DRY target, but they were left per-labeler — correctly. Each embeds its concrete class name and a different field set (kbdiag/qxtc carry extra fields). These strings feed the exact-string assertions verified in (2); folding via `type(self).__name__` introspection would be a behavior risk for zero correctness gain. Not folding = the right conservative call. (Noting only so the gap vs. spec is explicit; not a defect.)

**On the qx/qxtc keep-separate decision: AGREE.**
Merging would force converting `@measure_time`/`@count_calls` (which carry the distinct, C2-aggregate-registry-read key sets `qx_*` vs `qx_with_testcases_*`) into manual param-selected timer/counter calls inside the recursion. That is a real, asymmetric risk: a single wrong label silently zeroes one metric set in C2's by-name aggregation, and the bug would not surface in test_diagnosis (which asserts diagnoses, not metric keys). The two cores also differ structurally (qxtc threads a `test_case` through `_qx` and does the neg_tv/test-case consistency gating that plain qx lacks). The DRY win does not pay for the metric-corruption + recursion-correctness risk. Keep separate; if a merge is ever pursued, gate it behind an explicit assertion on both key sets' presence/values post-merge. (Red-team already mandated preserving both key sets — separation is the lowest-risk way to honor that.)

---

## Status

**Status:** DONE
**Summary:** C7 PASS. test_diagnosis migration is faithful — 206→206 cases, 35 identical test fns, all 46 assertions byte-identical, sat4j params run, no no-ops, no narrowed param sources. Labeler base extraction behavior-preserving (ABC intact, types correct, no method lost, no dead imports). All 4 metric key sets unchanged; twin algorithm files untouched. qxtc docstring fix accurate. Suite 509 green / 0 warnings.
**Concerns:** 2 Low (L1 stale `_assert_param_type` docstring ref; L2 cosmetic `None` type annotation). Neither blocks landing.

## Unresolved questions
- L1: was `_assert_param_type` an intended extraction that got dropped, or a copy-paste docstring artifact? If intended, the 4 duplicated `assert isinstance` blocks could route through it; if not, just delete the doc phrase. (Maintainer call — both are fine.)
