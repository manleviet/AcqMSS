# Code Review — C5: codec encode-merge + seeded RNG + ExampleGenerator on Oracle Protocol

Date: 2026-06-21
Reviewer: code-reviewer
Scope: uncommitted working-tree changes on `feat/redesign-abc` + new `tests/test_generator_characterization.py`
Spec: `plans/260621-1416-redesign-abc/phase-12-c5-codec-merge-seeded-rng-oracle-protocol.md`

## Verdict

- **(1) Single config→literal encoder:** CONFIRMED — exactly one impl (`VariableCodec.config_to_literals`); `Example.to_literals` delegates; output provably identical to pre-refactor.
- **(2) Seeded-RNG correct + reproducible:** CONFIRMED — zero global `random.*` state in generators; per-instance `random.Random(seed)` threaded through; reproducibility proven; `seed=None` works.
- **C5 overall: PASS** (with one MEDIUM advisory on FF test strength; no blockers).

## Scope
- Files: `explanation/models/codec.py`, `conacq/examples/data_structures.py`, `conacq/example_generators/{base,feature_frequency,random_sampling,query_provider}.py`, new `tests/test_generator_characterization.py`
- LOC: ~84 changed + 208 new test
- Tests: full suite **509 passed, 1 warning** (known `TestSuiteReader` PytestCollectionWarning); 53s. Targeted: 14 passed (characterization + boundary guard). No flaky failure surfaced; no re-run needed.

## Overall Assessment
Clean, well-scoped refactor. The two CRITICAL items are correct and verified empirically, not just by reading. Delegation is output-identical, global RNG is fully eliminated, the boundary stays intact, and no plan-stage labels leaked into code. One non-blocking weakness: the FeatureFrequency "exact-content" characterization test is effectively a duplicate of its reproducibility test and does NOT provide the distribution-regression coverage the Red-team brief asked for.

---

## CRITICAL verification (E1 — codec single encoder)

**PASS.** Verified:
- Grep confirms exactly two symbols repo-wide: `VariableCodec.config_to_literals` (codec.py:42, the impl) and `Example.to_literals` (data_structures.py:81, the wrapper). No `_config_to_literals` duplicate remains anywhere in `conacq/` or `explanation/`.
- `Example.to_literals` (data_structures.py:96-98) delegates: builds `VariableCodec(id_to_name={vid:name ...})` (inverting the `feature_ids` name→id map) and calls `config_to_literals`. Not a re-implementation.
- **Output identity proven empirically** across 6 edge cases (sorted vs unsorted insertion order, skip-unknown, empty config, empty feature_ids, mixed signs): old hand-rolled loop == new delegation in ALL cases. Both sort by feature name and skip names absent from the id map — identical sort + identical skip semantics.
- `config_to_assumptions` (codec.py:32-40) vs `config_to_literals` (42-55) are genuinely DIFFERENT encodings: the former maps feature→assumption ID via `pos/neg_assignment_to_assumption` (assumption layer), the latter maps feature→SAT variable ID via inverted `id_to_name` (variable layer). Different source dicts, different skip predicate, no accidental dup. Confirmed.

## CRITICAL verification (E2 — seeded RNG)

**PASS.** Verified:
- Grep for `random.(seed|shuffle|choice|randint|random|sample)` across `conacq/example_generators/` → **zero matches**. All global mutation gone.
- Every generator builds a local `rng = random.Random(seed)` and threads it through helpers (`base._generate_valid_config(rng)`, FF `_generate_valid_config_for_coverage(rng)` / `_generate_biased_invalid_config(rng)`). `query_provider` always uses `random.Random(seed).shuffle(self._pool)` — `Random(None)` is a fresh entropy-seeded instance, no global state. Correct.
- `seed=None` confirmed working (`test_no_seed_does_not_error` for both RS and FF; verified `random.Random(None)` is entropy-seeded).
- **No caller API broke.** `generate()` public signatures unchanged (`seed: Optional[int]`). The `rng` param was added only to *private* helpers (`_generate_valid_config`, FF internals); all internal call sites updated in-diff. `nwise_coverage.py` correctly untouched (uses `allpairspy`, no `random`).
- Reproducibility: same-seed-twice tests present for both RS and FF; RS additionally cross-process stable (verified: identical hash across separate processes).

## Boundary (E3) — PASS
- `Example.to_literals` imports via `from explanation.api import VariableCodec` (data_structures.py:96) — allowed conacq→explanation surface, not a deep path. `VariableCodec` is exported from `explanation/api.py` (line 37 import, line 97 `__all__`).
- Boundary guard is AST import-line based; the inline import is on the allowed `explanation.api` module → green (verified: `test_boundary_guard.py` passes).
- `ExampleGenerator` no longer imports `FeatureModelOracle`; typed against `Oracle` Protocol; `oracle.get_variables()` still called (B3 contract honored). Confirmed no concrete import in `base.py`.

## Hygiene (E4) — PASS
- No `E1`/`E2`/placeholder/`TODO`/`FIXME`/`phase-12`/`C5`/`red-team` strings in changed source or test files. Cleanup confirmed complete.
- Docstrings updated to reflect Oracle (not FeatureModelOracle) and the rng-threading contract. Comments explain the *why* (e.g., query_provider's `Random(None)` rationale), no plan refs. Compliant with the no-plan-labels rule.

---

## Findings by severity

### MEDIUM — FF `test_exact_assignments` is a duplicate of `test_reproducibility_same_seed`, not a content pin
File: `tests/test_generator_characterization.py:129-143` (and 145-151)

`TestFeatureFrequencyCharacterization.test_exact_assignments` runs two generators with the same seed and asserts equality — **byte-for-byte the same logic** as `test_reproducibility_same_seed`. Its docstring claims it pins "exact assignments" but it does not pin any constant. This is precisely the gap the Red-team brief called out: "same-seed-twice is necessary but NOT sufficient — passes by construction even if distribution/coverage logic broke." So FF currently has **no test that would catch a distribution/coverage-logic regression** — only RS does (via `_RS_SEED42_N20_PINNED`).

Why the report's cross-process rationale is half-right: I verified empirically that
- FF IS cross-process nondeterministic (different hash AND length 10 vs 9 across separate `python -c` runs) — so a hard-coded constant pin like RS's would be flaky. The decision to NOT hard-pin FF is sound.
- BUT FF is **deterministic within a single process**, including across fresh oracles (verified: identical hash for 3 in-process calls, and for 2 fresh-oracle calls in one process). The characterization fixture is `scope="module"`, so within a test session FF output is stable.

Recommendation (non-blocking, strengthens regression coverage):
Replace the misleading duplicate with an **in-process capture-once pin** that actually exercises distribution logic:
```python
def test_exact_assignments(self, fm_oracle):
    """In-process content pin: capture once, assert structural invariants that
    a distribution/coverage regression would break (FF is process-deterministic
    but not cross-process, so we pin shape, not a frozen constant)."""
    gen = FeatureFrequencyGenerator(fm_oracle)
    result = gen.generate(max_examples=self.MAX_EXAMPLES, seed=self.SEED)
    ordered = _assignments_ordered(result)
    # coverage-logic invariants the duplicate test cannot catch:
    assert len(ordered) == len(set(ordered))          # FF dedups configs
    assert all(len(a) == len(self.features_or_14) for a in ordered)  # full configs
    # plus: assert a stable count band, or pin the covered (feature,value) set
```
At minimum, rename the current method to reflect that it is a reproducibility check, OR add a distinct assertion (dedup invariant, full-assignment width, covered-pair set) so the test earns its "characterization" name. As-is it is dead weight relative to `test_reproducibility_same_seed`.

### LOW — `name_to_id` rebuilt on every `config_to_literals` / `config_to_assumptions` call
File: `explanation/models/codec.py:50`

`config_to_literals` recomputes `name_to_id = {name: vid ...}` from `id_to_name` on each call. `to_literals` also constructs a throwaway `VariableCodec` per call (data_structures.py:97). For the per-example encode path this is O(features) dict rebuild per literal conversion. Functionally correct and matches prior behavior (old code also did per-call work), so not a regression. If `to_literals` is ever called in a hot acquisition loop over many examples, consider caching the inverse map on the codec (it is a frozen dataclass field's inverse) or having callers reuse one codec. YAGNI for now — flag only.

### LOW (informational) — RS pinned baseline is the right choice and is robust
File: `tests/test_generator_characterization.py:185-206`

RS never calls `complete_configuration`, so its output is a pure `random.Random(42)` stream → cross-process deterministic (verified: identical hash across processes). `generate()` uses `for i in range(n)` with no dedup, so `len == n == 20` always holds, consistent with the 20-row pin. This is exactly the generator that SHOULD be hard-pinned. Good.

---

## Edge cases checked
- Empty `config` / empty `feature_ids` → `to_literals` returns `[]` (both old and new). OK.
- Unknown feature names skipped identically in both impls. OK.
- Insertion-order independence: both impls sort by name before emitting. OK.
- `seed=None` entropy path for all generators + query_provider pool shuffle. OK.
- nwise generator (out of scope, no `random`) correctly left untouched. OK.

## Positive observations
- E1 delegation is output-identical, verified by differential testing, not assumed.
- E2 eliminates a real reproducibility hole (global `random.seed` mutating process-wide state) — important for a benchmark codebase.
- Docstrings now state the reproducibility contract explicitly ("same seed and oracle produce identical ExampleSets").
- query_provider comment correctly documents the `Random(None)` entropy-seed rationale.
- Boundary respected via `explanation.api`; guard stays green.

## Recommended actions (priority order)
1. (MEDIUM) Strengthen or rename FF `test_exact_assignments` (262-1416...test:129) — currently a duplicate reproducibility check; add a distribution/coverage invariant (in-process pin) so it can catch the regression class the Red-team brief targeted. Non-blocking for C5 commit.
2. (LOW) Optionally cache inverse `name_to_id` if `to_literals` enters a hot loop later. Defer (YAGNI).

## Answer to spec Q5 (FF cross-process pin)
Sound decision to NOT hard-pin FF cross-process — empirically confirmed nondeterministic across processes (different content AND length). NOT a hidden bug; it stems from flamapy SAT solver model selection varying with process startup state, which sits behind `oracle.complete_configuration`. However, the chosen substitute (two-call equality) is too weak — it is identical to the reproducibility test and adds no coverage. Better: an in-process capture-once pin (FF is deterministic within a process and across fresh oracles in-process, verified), or assert coverage invariants (dedup, full-config width, covered (feature,value) set). This is a test-quality improvement, not a correctness blocker.

## Metrics
- Global `random.*` in generators: 0 (was: 4 files with global state)
- config→literal encoders: 1 (was: 2)
- Full suite: 509 passed / 1 known warning
- Boundary violations: 0

## Status
**Status:** DONE_WITH_CONCERNS
**Summary:** C5 PASS — both CRITICAL items (single encoder, seeded RNG) verified empirically; full suite green (509). One MEDIUM non-blocking concern: FF `test_exact_assignments` is a duplicate reproducibility check, not the distribution-regression content pin the Red-team brief required.
**Concerns:** FF characterization test does not catch distribution/coverage logic regressions (only RS does). Recommend in-process pin or coverage invariants before considering generator test coverage complete. Does not block the C5 commit.

## Unresolved questions
- Is FF's distribution/coverage logic considered stable enough that the weaker test is acceptable for now, or should the in-process pin land within C5 vs a follow-up? (Recommend follow-up; not a commit blocker.)
