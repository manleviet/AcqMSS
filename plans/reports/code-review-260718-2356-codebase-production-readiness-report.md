---
type: code-review
date: 2026-07-18
scope: full codebase (conacq/ + explanation/ + profiling/ + apps/)
branch: feat/redesign-abc-v2
head: 3a5bf55 (T18 docs coherence)
baseline: suite 501 green (py3.11), boundary-guard 6/6
method: 2 scoped code-reviewer subagents (conacq, explanation+profiling) + cross-cutting anti-pattern sweep; every Critical/Important re-verified against code (several reproduced by execution)
status: report-only — NO code changed
---

# Codebase Review — AcqMSS (production readiness)

## Verdict

Well-engineered and disciplined: immutability-at-construction (ADR-0012), exception-safe solver cleanup, no injection surface (no `eval`/`exec`/`pickle`/`shell=True`/`os.system`), **0 mutable-default args**, boundary guard 6/6, suite 501 green. **No silent data-corruption bug on the current AcqMSS app path** (UVL → ConGen / QuAcq-oracle → eval).

Real issues cluster in **(a) reproducibility** — load-bearing for a benchmark paper — and **(b) edge-case crashes / silent-wrong-results in library or deferred code not wired into the apps**. Blast radius is stated per finding because it drives priority.

Threat model: constraint-acquisition/SAT research system — no network/auth/DB/untrusted input, so web-security surface is negligible. Focus is algorithm correctness, resource/state management, and determinism.

---

## Critical

### 1 — QuAcq example-pool shuffled with OS entropy when `seed=None`
`conacq/example_generators/query_provider.py:60`

`random.Random(seed).shuffle(self._pool)` runs unconditionally when a pool is present; `seed=None` → OS entropy. Trace (default args): interactive CV `shuffle_bias=False` → `cross_validation.py:199` `fold_shuffle_seed=None` → `_run_example_mode` → `QueryProvider(pool=…, seed=None)`. Two identical example-mode runs learn different KBs → different per-fold accuracy → different `mean/std`.

- **Blast radius:** example modes (`example_only`/`example_first`) only — **oracle mode passes no pool, so it is deterministic**. Latent (tests pass `seed=42`), so nothing flakes today.
- **Why it matters:** reproducibility is the paper's load-bearing property; even the "no shuffle" mode (`shuffle_bias=False`) still OS-entropy-shuffles the pool.
- **Fix:** guard `if seed is not None:` before shuffling (mirror ConGen `congen_runner.py:130`), or require a concrete seed.
- **Verified:** the code comment itself notes `Random(None)` uses OS entropy — it conflates T16 RNG-*isolation* (don't touch the global stream) with reproducibility.

### 2 — `WipeOutR_T` crashes on a ≤1 test-case suite
`explanation/operations/algorithms/wipeoutr_t.py:71`

`return [], set_t.copy()` — `set_t` is `task.set_tc`, coerced to a **frozen tuple** (`task_preparation.py:193,203`); `tuple` has no `.copy()` → `AttributeError`. Line 74 does `list(set_t)`, proving the author assumed a list; the frozen-tuple refactor (T11c/T21) broke only the `≤1` branch.

- **Blast radius:** the `redundancy_testcases` op is builder-backed (`pysat_explanation_builder.py:303`) but has **no app/runner/conacq caller today** — a public *framework* op (matters for the PUBLISH milestone, not the current app path).
- **Fix:** `list(set_t)`.
- **Verified + reproduced** (AttributeError).

---

## Important

### 3 — `shuffle_bias` is a silent no-op for QuAcq
`conacq/algorithms/quacq/quacq.py:140`

`remaining_bias = set(set_c)` discards the seed-shuffled order of `set_c` (int-set iteration = hash order, not insertion). `quacq_runner.py:172-175` shuffles `task.set_c` by seed, but `learn()` throws it away. QuAcq's constraint-testing order (most impactful in oracle mode via `generate_from_sat`) is governed by assumption-ID layout, not the seed. Deterministic per-build (golden tests pass) but the experimental knob does nothing.

- **Fix:** keep `set_c` as an ordered structure for iteration; use a set only for membership.

### 4 — `REDUCE` discards MSS ordering via `set()`
`conacq/algorithms/acqmss/reduce.py:63`

`kb = list(set(set_b_prime) | set(set_neg_tv))` erases AcqMSS's deliberate `gamma1+gamma2` order (`acqmss.py:104`). When constraints are mutually redundant (`BG ∪ (KB−{c}) |= c`), *which* representative survives depends on hash order — stable within a CPython build, but fragile across interpreter versions / any assumption-ID shift, and can shift description-based TP/FP in `kb_comparator._compare_by_description`.

- **Fix:** reduce over `set_b_prime + set_neg_tv` in list order with a seen-set for dedup.
- Confidence: high on order-dependence; medium on real metric impact (needs mutually-redundant constraints with divergent descriptions).

### 5 — DIMACS `next_available_id` from comment count → assumption/variable collision (silent wrong diagnosis)
`explanation/transformations/dimacs_to_diag_pysat.py:55`

`next_available_id = len(variables) + 1` where `variables` is built only from `c` comment lines (`_parse_features_variables`); the declared `p cnf <nvars>` (`problem_list[2]`) is parsed but **never used** (only `[3]`=nclauses). A CNF with vars `1..N` and an incomplete `c` catalog → assumption/Tseitin ids alias real variables → guard clauses `[-original_id, …]` over-constrain → **silently wrong diagnoses/redundancy**.

- **Blast radius:** `DiagnosisModelBuilder.from_dimacs()` only (library/test path; apps use UVL).
- **Fix:** seed from `max(int(problem_list[2]), len(variables)) + 1` (or the max var id seen in clauses).
- **Verified** (`problem_list[2]` confirmed unused).

### 6 — FastDiagP resource bugs
`explanation/operations/algorithms/fastdiagp.py:75-91`

(a) `mp.Pool` created with **no `try/finally`** → orphaned workers if `_fd()`/`diff()` raises (subsequent `find_diagnosis` overwrites `self.pool`, leaking the prior one); (b) `min(cpu_count()-1, 4)` = `0` on a 1-vCPU host → `mp.Pool(0)` `ValueError`; (c) missing `pool.join()` after terminate.

- **Blast radius:** `FastDiagP` is instantiated **only in `tests/test_diagnosis_fastdiag.py`**, not wired into any op/builder — no current production path (deferred-executor scaffolding, ADR-0014).
- **Fix (before it's ever wired):** `with mp.Pool(max(1, min(cpu_count()-1, 4))) as self.pool:`.

---

## Minor (evidence-backed; fix opportunistically)

- **Div-by-zero, unguarded:** `cross_validation.py:252` `sum(fold_accuracies)/len(fold_accuracies)` (0 folds) · `feature_frequency.py:277` `covered/total_needed*100` with `total_needed=len(features)*4` (0-feature FM). (`metrics.py:43` and `result_loader.py:93` *are* guarded.)
- **`nwise_coverage.py:64`** — broad `except Exception` for the allpairspy version-fallback silently degrades N-wise → pairwise; catch `TypeError` or log the fallback.
- **`apps/extract_results.py:230`** — `except Exception: return None` with no logging masks corrupt-JSON/IO as "no data".
- **`kb_comparator.py:151/203/280`** — the `startswith('ne_')` guard is dead (combined-NE resolves to a real `"(… AND …)"`/`"NOT(…)"` description, never `ne_*`); NE inflates `n_kb` / understates `kb_reduction_ratio` by ≤1. Decide explicitly whether NE belongs in reported KB size.
- **8× `assert isinstance` in `explanation/operations/algorithms/hsdag/labeler/*.py`** — stripped under `python -O`; defensive type guards only.
- **FastDiagP:** `lookup_table` never reset between calls (`:43`) → stale `AsyncResult`s if an instance is reused; `if result.ready:` (`:160`) missing `()` → always-truthy method ref, `not_ready` metric never fires.
- **`profiling/core.py:174`** — `threading.Lock` gives no cross-process exclusion under `MULTI_PROCESS`+`fork` (lost metric updates); metrics-only, macOS `spawn` sidesteps it.
- **`wipeoutr_t.py:80`** — `t_pi.pop()` (last) vs spec `first(T_π)`; result still valid, differs from the paper's representative.
- **`explanation/operations/algorithms/hsdag/node.py`** — `generating_node_id` class-level counter reset in `create_root`; cosmetic (used only in `__str__`).
- **`__del__` solver cleanup** (`oracle/fm/oracle.py:169`, `eval/accuracy.py:159`) — non-deterministic finalization; both have explicit `cleanup()`, so it's a fallback.

---

## Positive observations (risk calibration)

- 0 mutable-default args · no `eval`/`exec`/`pickle`/`shell=True`/`os.system` · no bare `except:` · no `TODO/FIXME/HACK` left (T17 cleanup).
- SAT4J subprocess bounded by timeout, handles `TimeoutExpired`/`OSError`/`SubprocessError`, surfaces `SolverTimeoutError` (no silent timeout→UNSAT), cleans its temp CNF on the raise.
- PySAT solver cleanup exception-safe: `try/finally` (`oracle/fm/oracle.py:149-156`), `with Solver(...)` (`semantic_equivalence.py:88`), per-call delete in non-incremental/SAT4J backends.
- ADR-0012 frozen discipline holds: `prepare_task` is genuinely pure (no cross-fold model mutation); labeler `identify_new_node_parameters` copies (`list(param.set_c)`) before mutating; `prepare_kb` copies each clause before adding guards.
- ADR-0013 `is_consistent`/`find_model` split correct in `backend.py`.
- Example generators use per-instance `random.Random(seed)` (no global-`random` leakage — T16 holds *except* the C1 pool path).
- `atomic_io` correct (temp-in-same-dir + fsync + `os.replace`); folds seeded deterministically; `intersected_kb` is `sorted()`.
- Caller/algorithm argument-order mapping is correct (`set_b`=bias / `set_bg`=BG throughout); `negation_map` construction sound.

---

## Recommended actions (by milestone)

- **Before publishing benchmark numbers:** fix **#1, #3, #4** — they undermine reproducibility/experimental-control even though the suite is green (paths are deterministic-per-build or seeded-in-tests, so nothing flakes now).
- **For the PUBLISH-as-framework milestone:** fix **#2, #5, #6** — real crashes / silent-wrong-results in public library surfaces not exercised by the current apps.
- Nothing here blocks the current app path from producing correct results on UVL inputs in oracle mode.

---

## Verification notes (no rubber-stamp)

Every Critical/Important was re-checked against the code, not trusted from the subagents:
- #1: confirmed unconditional shuffle + `seed=None` trace; reconciled with green golden tests (tests pass `seed=42`; oracle mode has no pool).
- #2: confirmed `set_tc` tuple-coercion (`:193,203`) + tuple has no `.copy()` + op is builder-backed but unused by apps.
- #3/#4: confirmed `set(set_c)` / `set()|set()` discard order; **deterministic per-build** (int-set iteration stable) — which is *why* golden tests stay green; the defect is "knob ignored / MSS order lost", not flakiness.
- #5: confirmed `problem_list[2]` parsed-but-unused; collision guaranteed when `len(variables) < nvars`.
- #6: confirmed no `try/finally` around the pool; `mp.Pool(0)` on 1-vCPU reproduced.

---

## Unresolved questions

1. Do paper runs use interactive **example mode** with `shuffle_bias=False`? If yes, #1 is actively non-reproducible; if always oracle-mode or always seeded, #1 is latent.
2. Is the surviving combined-NE meant to count in `n_kb`/`kb_reduction_ratio` (#5-minor / Algorithm 1 line 9), or should NE be stripped before reporting KB size?
3. Are the `.cnf` test fixtures fully `c`-commented? If not, #5 is already producing wrong `from_dimacs` diagnoses — worth a test with an uncommented CNF.
