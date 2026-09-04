# Implementation Plan — ConMin (passive maximally-general acquisition)

> **SEED** created at the Cowork→Claude Code handoff (2026-07-21). This is the **HOW**, anchored to `main`. Claude Code owns and expands it; it re-syncs against the design brief before each task (DELTA-CHECK — **the brief wins**).

- **Design source (WHAT/WHY — Cowork owns, do NOT re-decide here):**
  `<vault>/Cowork/AcqMSS/ConMin - Implementation Design Spec.md` (the brief). Supporting: `Cowork/AcqMSS/ConMin - AcqMinCover v2.md` (Phase-2 authoritative), `ConMin - Maximally General Constraint Acquisition.md` (v1), and the paper `Cowork/AcqMSS/Overleaf/AAAI/main.pdf` (ground truth). All 4 design decisions are locked in the brief §8; the eval-layer contract is brief §9.
- **Branch:** `feat/conmin` (from `main` `62bfb9e`).
- **Baseline (confirm before starting):** `PYTHONPATH=. pytest tests/ -q` → **507 passed + 1 skipped** (`test_extraction_tables_are_byte_identical`, known debt B3/ADR-0017). ConMin must add without regressing this. `../explanation` installed editable.
- **Boundary:** `conacq/` imports **only** the `explanation.api` **and** `profiling` façades — **two** façades, `test_boundary_guard.py:42-43` (ConGen already imports `profiling`, `congen.py:31-33`) — run `tests/test_boundary_guard.py` first after any structural change. New min-cover engine is in-repo (HSDAG is not on the façade).
- **Package:** `conacq/algorithms/conmin/` (sibling of `acqmss/`); reuse `acqmss.py`, `generate_ne.py`, `reduce.py` by import (do NOT fork).

## Common per-task framework (repeated, not restated per task)

1. **Re-sync with the brief first** (DELTA-CHECK). If code reality diverges from the brief, STOP and ask Cowork — do not silently re-decide.
2. **Read main behaviour** for anything you touch/mirror (`acqmss/` is the template).
3. **Safety-net tests before** non-trivial logic; unit-test cover/support with a stub checker (mirror `_MutualRedundancyChecker` in `test_congen.py`).
4. Implement → `PYTHONPATH=. pytest tests/ -v` **GREEN** (never weaken an assertion; re-pin characterization only to a verified new value).
5. **Docs in-stage:** API/structure change → update `docs/system-architecture.md` / `docs/codebase-summary.md` / docstrings immediately; a settled architecture *why* → a new ADR under `docs/adr/` (Plan ≠ ADR).
6. Conventional commit (no AI refs) → **STOP, summarise for user review** → next task.

## Task order (maps to brief §7 phases)

- **P1 — scaffold + Stage 1 parity.** `conmin/` package: `conmin.py` (`ConMin`+`ConMinResult` with the three eval slices, brief §5/§9a), `conmin_model.py` (`ConMinModel(KBModel)`), `conmin_model_builder.py` (one-method subclass), `task_preparation.py` (`ConMinTaskInput`/`ConMinTask`/`ConMinTaskPreparation` — for P1 only Stage-1 fields). `ConMin.acquire` runs Algorithm 1 lines 1–4 (gate + `AcqMSS.find_mss` under `BG∪NE`), returns `A` as maximally specific. **Accept:** builder purity/repeatability test + Stage-1 output equals ConGen's MSS on shared inputs (`data/fms/REAL-FM-7.uvl` + bias + examples).
- **P2 — AcqMinCover (`w≡1`).** `acqmincover.py`: `cand` build (cache), compound `QuickXplain` branch, `connected_components` (union-find), `exact_cover` (min-cardinality-first, `tau=15`), `greedy_cover` (`H(d)` fallback), irredundancy post-pass. Retain E⁻ first-class (`neg_encodings`, brief §2). **Accept:** `TestAcqMinCover` (a)–(e) on the v2 worked example — exact returns the 2 true constraints, not greedy's 3.
- **P3 — support⁺ + Reduce + full ConMin.** `support.py` at prep layer (general CNF, "≥1 clause critical", brief §4) → `build_support_count` → `ConMinTask.support_count`. Assemble KB in Reduce order (fallbacks, S, C); `¬e⁻` fallbacks for `U`. **Accept:** `TestConMinReducesToWorkingExample` — `C_τ` exactly for `k∈{1,2}`; pure min cover for `k≥3`.
- **P4 — weight + metrics + CLI/runner.** `weight`=arity over the `w≡1` base; `ConMinRunner(BaseRunner)`; `apps/run_conmin.py` + `apps/conf/run_conmin_config.toml`; `CONMIN_METRICS` in `conacq/runners/metrics.py` with the **per-call-site consistency-check taxonomy** (brief §9c: `admpool_gate_checks`, `admpool_checks`, `cover_rejection_checks`, `cover_quickxplain_checks`, `redundancy_consistency_checks`, + derived total incl. Reduce+QX per SoSyM R1-Q4) and cover-specific counters (#components, largest_component, n_greedy_fallback, |U|). **⚠ P4-ESCALATION (from red-team, finding 5):** the §9c `admpool_gate_checks` vs `admpool_checks` split is NOT a metrics-layer reclassification — the two sum into one scalar `paper_consistency_checks` at source (`acqmss.py:79`, gate), so disaggregation needs a **source-level** change: parameterize the counter key inside the shared, frozen `AcqMSS`/gate (default preserves ConGen). That edits code shared with ConGen → **STOP and ask Cowork at P4** (likely an ADR); do **not** patch at the metrics layer. The P4 fix is **dual-emit (additive)** — add `admpool_gate_checks` *alongside* `paper_consistency_checks` — never a rename (a rename drops ConMin's gate from the universal total). **Accept:** metrics surfaced; runner parity with ConGen; full suite green.
- **P5 (later) — refinements.** scope-restricted config-count `weight`; partial-example eval. Out of scope now: ≥5000-feature model (SoSyM R1-Q8, keep harness size-agnostic), RIPPER/CN2 (SoSyM item, not AAAI).

## Tests to add (mirror `tests/test_congen.py`)

`tests/test_conmin.py`: `TestConMin` (e2e inc/non-inc, RS+FF), `TestAcqMinCover` (stub-checker units), `TestComponents`, `TestSupport` (per-operator: requires/excludes single-clause, mandatory/alternative/or multi-clause, "≥1 clause critical", partial-`e⁺` no support), `TestConMinReducesToWorkingExample`, `TestConMinModelBuilder`. Pre-check: `test_boundary_guard.py` first; baseline 507+1 not regressed. **(P1 introduces `TestConMinModelBuilder` (trimmed), `TestConMinGate`, `TestConMinStage1` — see the detailed P1 test design; the full-e2e `TestConMin` and the cover/support/reduces classes land with P2–P3.)**

---

# P1 — Detailed HOW (expanded 2026-07-21, DELTA-CHECK clean @ `main` 62bfb9e)

**Scope:** scaffold `conacq/algorithms/conmin/` + Stage-1 parity ONLY. `ConMin.acquire` runs paper Algorithm 1 **lines 1–4** (gate + `AcqMSS.find_mss` under `BG∪NE`), returns `A` (maximally specific, **unreduced**). No cover, no support, no Reduce (P2/P3). P2–P5 stay at seed level above until touched.

## DELTA-CHECK (brief §1 vs code) — verified, no divergence

| Brief §1 | Code (file:line) | Verdict |
|---|---|---|
| `AcqMSS.find_mss(delta,set_b,set_neg_tv,set_tc,set_bg)` under NE+BG | `acqmss/acqmss.py:52`; ConGen calls `congen.py:119` | reuse as-is |
| Checker gate `is_consistent_test_cases(NE∪BG, E⁺, stop=True)` | `congen.py:98` | mirror |
| `KBModel` (constraint_map/negated_constraint_map/next_available_id/name↔id) | `kb_model.py:15` | inherit |
| `OracleBiasModelBuilder[TModel]`, hook `_create_model_instance()` | `oracle_bias_model_builder.py:84` | subclass |
| `ConGenTaskPreparation` factors `_prepare_negative_examples` (GenerateNE) | `acqmss/task_preparation.py:187` | reuse by delegation |
| Boundary guard scans `conacq/` only (tests exempt; use deep checker path in test) | `test_boundary_guard.py:46` | safe |

**Finding (not a divergence):** `ConGenResult` exposes no MSS list (only `n_mss` + post-Reduce `kb_assumption_ids`). Parity reference ⇒ call `AcqMSS.find_mss` directly (== ConGen internal Stage-1). No brief conflict → **proceed, no stop-and-ask.**

## Files

**Create** (`conacq/algorithms/conmin/`):
- `__init__.py` — export `ConMin, ConMinResult, ConMinModel, ConMinModelBuilder, ConMinTask, ConMinTaskInput, ConMinTaskPreparation`.
- `conmin.py` — `ConMin` + `ConMinResult` (mirror `congen.py`).
- `conmin_model.py` — `ConMinModel(KBModel)`, **P1: `prepare_task` only** (resolve_result deferred, see decisions).
- `conmin_model_builder.py` — `ConMinModelBuilder(OracleBiasModelBuilder[ConMinModel])`, one method.
- `task_preparation.py` — `ConMinTaskInput` / `ConMinTask` / `ConMinTaskPreparation` (P1: Stage-1 fields; **delegates** to ConGen prep).

**Modify:**
- `conacq/algorithms/__init__.py` — add ConMin block mirroring the ConGen block (import + `__all__`).
- `docs/codebase-summary.md` — add `conmin/` to file inventory (docs-in-stage).

**Create (test):** `tests/test_conmin.py`.

## Per-file HOW

### `conmin.py`
```python
@dataclass
class ConMinResult:
    # P1-filled (no default): the Stage-1 slice + its sizes.
    mss_ids: List[int]            # A = Stage-1 admissible pool (maximally specific)
    n_bias: int
    n_mss: int
    # Stage-2..5 slices + counts — DEFAULTED so partial construction (P1 success AND the
    # inconsistent-gate error return) can never omit a required field → no TypeError.
    # (Kept in P1 per the locked scope: ConMinResult exposes all three eval slices.)
    cover_ids: List[int] = field(default_factory=list)         # C                        [P2]
    support_ids: List[int] = field(default_factory=list)       # S                        [P3]
    fallback_ids: List[int] = field(default_factory=list)      # ¬e⁻ for e⁻∈U             [P3]
    uncoverable: List[int] = field(default_factory=list)       # U                        [P2/P3]
    kb_assumption_ids: List[int] = field(default_factory=list) # ConMin final post-Reduce [P3]
    n_kb: int = 0
    n_components: int = 0
    largest_component: int = 0
    n_greedy_fallback: int = 0
    metadata: Dict = field(default_factory=dict)
```
Dataclass rule respected: the 3 non-default fields precede all defaulted ones. Rejecting the red-team "cut to 4 fields" (contradicts locked P1 scope) — instead the slices stay *and* default, which also removes the phantom-assertion risk (the test asserts `kb_assumption_ids == []`, the one meaningful "ConMin theory not yet assembled" check, not every empty slice).

```python
class ConMin:
    def __init__(self, checker: ConsistencyChecker, profiler_instance: AbstractProfiler = None): ...
    @measure_time('conmin_runtime')
    @count_calls('conmin_calls')
    def acquire(self, set_b, set_bg, set_tc, set_neg_tv=None, negation_map=None) -> ConMinResult:
```
`acquire` body = ConGen `acquire` **minus Reduce**:
1. Normalise `set_neg_tv/negation_map` → `[]`/`{}`; coerce tuple task-fields → list (mirror `congen.py:88-92`).
2. **Gate (line 2):** `inconsistent = checker.is_consistent_test_cases(set_neg_tv + set_bg, set_tc, stop_at_first_violation=True)`; `profiler.increment("paper_consistency_checks")` (correct for P1 — parity with `congen.py:98-103`; the §9c taxonomy split is the P4-ESCALATION above, **not** done here). If `len(inconsistent) > 0` → `return ConMinResult(mss_ids=[], n_bias=len(set_b), n_mss=0, metadata={'error': 'E+ inconsistent with NE ∪ BG'})` (every slice/count now defaulted → no missing-arg `TypeError`).
3. **Stage 1 (line 4):** `acqmss = AcqMSS(checker, m=1, profiler_instance=profiler)`; `A = acqmss.find_mss(delta=[], set_b=set_b, set_neg_tv=set_neg_tv, set_tc=set_tc, set_bg=set_bg)`.
4. `return ConMinResult(mss_ids=A, n_bias=len(set_b), n_mss=len(A), metadata={'n_neg_tv': len(set_neg_tv), 'n_e_pos': len(set_tc), 'stage': 'P1-stage1-only'})` — Stage-2..5 slices/counts stay at their defaults.

Imports (façade-safe): `from conacq.algorithms.acqmss import AcqMSS`; `from explanation.api import ConsistencyChecker`; `from profiling import get_global_profiler, measure_time, count_calls, AbstractProfiler`.

### `task_preparation.py` — delegation (no fork, no ConGen-file change)
```python
@dataclass(frozen=True)
class ConMinTaskInput:          # ConMin's own type (ADR-0006), same fields as ConGen's
    oracle_data; positive_test_cases: TestSuite; negative_test_cases: Optional[TestSuite] = None
    @classmethod
    def from_examples(cls, oracle_data, positive_examples, negative_examples): ...  # copy ConGen

@dataclass(frozen=True)
class ConMinTask(TestCaseTask):
    pass  # P1: no extra fields. P3 adds neg_encodings + support_count (with defaults).

class ConMinTaskPreparation(TaskPreparationStrategy):
    def prepare(self, model, task_input: ConMinTaskInput) -> PreparedTask:
        # Pass task_input straight in (no ConGenTaskInput clone): ConGenTaskPreparation.prepare
        # reads the input only by attribute — .oracle_data (task_preparation.py:131),
        # .positive_test_cases (:160), .negative_test_cases (:167) — all present on ConMinTaskInput.
        # Duck-typed on BOTH model and input; consistent with the model duck-typing below.
        prepared = ConGenTaskPreparation().prepare(model, task_input)
        ct = prepared.task
        task = ConMinTask(set_c=ct.set_c, set_b=ct.set_b, set_kb=ct.set_kb,
                          negation_map=ct.negation_map, assumptions=ct.assumptions,
                          set_tc=ct.set_tc, set_tv=ct.set_tv,
                          set_neg_tv=ct.set_neg_tv, set_neg_tc=ct.set_neg_tc)
        return PreparedTask(task, prepared.describe)
```
Delegation ⇒ ConMin task fields are **byte-identical** to a ConGen task on the same inputs (same `oracle_data`, same alloc order) ⇒ Stage-1 ID parity by construction. Duck-typing note: `ConGenTaskPreparation.prepare` type-hints `ConGenModel` but touches only `KBModel` fields (`next_available_id`, `constraint_map`, `negated_constraint_map`, `name_to_id`); a `ConMinModel(KBModel)` is semantically valid (mypy-only mismatch, not in CI).

**Delegation is a P1-local choice, not the arc endpoint (honest framing — red-team finding 4).** Delegation calls `ConGenTaskPreparation().prepare()` as a **black box** and gets back only the finished task; the per-`e⁻` NE assignment-assumption IDs are computed and consumed *inside* `_prepare_negative_examples` (`task_preparation.py:205-208`) and never surface (only the combined `ne_id` lands in `set_neg_tv`). But brief §2 defines `neg_encodings` as exactly those per-`e⁻` assignment-assumption IDs — data the black box **discards**. So **P3 will tear this seam down**: it must either (a) subclass `ConGenTaskPreparation` and override the already-factored `_prepare_negative_examples` hook (`task_preparation.py:187`), and/or (b) surface the assignment IDs out of `GenerateNE` (brief §2) — the latter would touch a shared file and needs its own DELTA-CHECK. P1 keeps delegation because it is the zero-baseline-risk minimum *for P1's Stage-1-only need*; it is **not** claimed as "diverge only in the neg step." The seam is re-decided when P3 is reached (per "leave later phases at seed until touched").

### `conmin_model.py`
```python
class ConMinModel(KBModel):
    def prepare_task(self, task_input: ConMinTaskInput) -> PreparedTask:
        return ConMinTaskPreparation().prepare(self, task_input)
    # resolve_result: DEFERRED to P3/P4 — additive, no rework (verified: KBModel is concrete,
    # BaseRunner declares no resolve, so a ConMinModel with only prepare_task is valid).
```
**Pinned contract for P3/P4 (red-team finding 9):** ConMin **Reduces** (like ConGen), so its resolver mirrors `ConGenModel.resolve_result(result, describe, root_clauses) -> (bg_clauses, kb_clauses, kb_names, redundant_names)` (the 4-tuple, `congen_model.py:54-73`) — **not** QuAcq's 2-tuple `resolve_kb`. **Caveat:** `ConMinResult` has **no `redundant_ids`** field (it carries slices instead), so P3/P4 cannot copy ConGen's resolver verbatim (`congen_model.py:72` reads `result.redundant_ids` → `AttributeError`); it must map ConMin's slice-based result onto the 4-tuple (redundant names sourced from the Reduce step over `C∪S`).

### `conmin_model_builder.py`
```python
class ConMinModelBuilder(OracleBiasModelBuilder[ConMinModel]):
    def _create_model_instance(self) -> ConMinModel:
        return ConMinModel()
```

### `conacq/algorithms/__init__.py`
Add mirror of the ConGen block: `from .conmin import (ConMin, ConMinResult, ConMinModel, ConMinModelBuilder, ConMinTaskInput)` + `__all__` entries. (`conmin/__init__.py` re-exports the full set.)

## Test design — `tests/test_conmin.py` (mirror `test_congen.py`)

Shared paths/fixtures copied from `test_congen.py` (FM/BIAS/EXAMPLES_RS_1N/EXAMPLES_FF). Test imports use the **deep checker path** like ConGen's test (`from explanation.checker.backend import build_checker, SolverBackend`) — tests are outside the boundary-guard scan. `profiler = get_global_profiler()`; **no assertions on counter values in P1** (that is P4). Note per review rule: test names/docstrings explain the *invariant*, not finding codes (the `(RT-n)` tags below are plan-doc traceability only, never copied into code).

**`TestConMinModelBuilder`** — right-sized, NOT a 1:1 mirror (RT-10). `ConMinModelBuilder` is a one-method subclass; 100% of build/validate/negation is inherited from `OracleBiasModelBuilder` and already proven by `TestConGenModelBuilder` — re-testing it all is phantom coverage. Keep only:
- `test_prepare_task_is_pure_and_repeatable` (the load-bearing one: `p1.task.set_kb == p2.task.set_kb` and `p1.task is not p2.task`).
- `test_prepare_task_from_file` (build + prepare smoke — proves the ConMin wiring builds a task).
- `test_build_without_oracle_raises` (`ValueError match="OracleData required"` — cheap, documents the ConMin builder contract).
(Dropped ConGen's near-duplicate `prepare_task_from_data`.)

**`TestConMinGate`** — covers ConMin's ONLY new logic, which the parity path CANNOT (RT-1/RT-3 — on consistent REAL-FM-7 the gate is a no-op, so a broken/deleted gate still passes parity). Stub checker (mirrors `_MutualRedundancyChecker` in `test_congen.py:274`), no solver:
```python
class _GateTripChecker:  # reports E+ inconsistent with NE∪BG on the gate call; records calls
    def __init__(self): self.tc_calls = 0; self.gate_active = None; self.gate_tcs = None
    def is_consistent_test_cases(self, active, testcases, stop_at_first_violation=False):
        self.tc_calls += 1
        if self.tc_calls == 1: self.gate_active = list(active); self.gate_tcs = list(testcases)
        return list(testcases)                 # non-empty ⇒ "inconsistent"
    def is_consistent(self, test_set): return True
```
- `test_gate_short_circuits_on_inconsistent_examples`: `ck=_GateTripChecker(); r=ConMin(ck).acquire(set_b=[10,11,12], set_bg=[1], set_tc=[20,21], set_neg_tv=[30], negation_map={})`. Assert `r.mss_ids == []`, `r.n_bias == 3`, `r.n_mss == 0`, `'error' in r.metadata`, **`ck.tc_calls == 1`** (gate ran, `AcqMSS` did NOT). **Teeth (this is the user's falsification target):** delete the gate → `acquire` proceeds into `AcqMSS.find_mss` → `tc_calls > 1` AND `mss_ids != []` → RED.
- `test_gate_uses_NE_plus_BG_over_Epos`: same stub, assert `ck.gate_active == [30, 1]` (`set_neg_tv + set_bg`, order per `congen.py:98-99`) and `ck.gate_tcs == [20, 21]` (`set_tc`). **Teeth:** wrong-set / wrong-order wiring of the gate.

**`TestConMinStage1`** — Stage-1 parity on real REAL-FM-7 data (teeth in parens):
1. `test_stage1_mss_is_unreduced_admissible_pool` — build ONE ConMin task; build TWO checkers from it; `result = ConMin(ck_a).acquire(set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc, set_neg_tv=task.set_neg_tv, negation_map=task.negation_map)`; `reference = AcqMSS(ck_b, m=1).find_mss(delta=[], set_b=list(task.set_c), set_neg_tv=list(task.set_neg_tv), set_tc=list(task.set_tc), set_bg=list(task.set_b))`; assert `sorted(result.mss_ids) == sorted(reference)` (**teeth:** ConMin accidentally Reducing / truncating), `result.n_mss == len(result.mss_ids)`, `result.kb_assumption_ids == []` (the one meaningful "ConMin theory not yet assembled" check). `finally: ck_a.cleanup(); ck_b.cleanup()`.
   **Docstring must state the two invariants this rests on:** (i) the reference is `AcqMSS.find_mss` directly, **not** `ConGenResult`, because Reduce discards/reorders the MSS so ConGen exposes only `n_mss` — **ADR-0017** (reduce-discards-mss-order); (ii) `ck_a` (gate + find_mss) and pristine `ck_b` (find_mss) agree because Stage-1 uses SAT/UNSAT only (`is_consistent`), invariant under learned clauses — **ADR-0013** (is_consistent vs find_model; glucose hides model-divergence, cadical exposes). Verify both ADR files exist under `docs/adr/` at code time; if `ADR-0013` is still "pending", cite the invariant in prose and drop the file ref.
2. `test_stage1_matches_congen` — cross-pipeline: build a `ConGenModel` task + a `ConMinModel` task from the **same** oracle+bias+examples. Assert task-field parity `conmin.set_c==congen.set_c`, `set_b`, `set_tc`, `set_neg_tv`, `negation_map` (**teeth:** prep divergence). Then assert `sorted(ConMin(...).acquire(...).mss_ids) == sorted(AcqMSS(...).find_mss(...))` on the ConGen task — **exact-set, no fallback** (RT-2: the size-parity fallback is REMOVED — it would pass two different same-cardinality sets and contradicts "never weaken an assertion"). Exact-set holds by delegation-ID-parity; **if it ever fails → that is a real divergence: STOP + investigate per DELTA-CHECK, do not downgrade.**
3. `test_stage1_characterization_golden` (RT-1 extra — absolute anchor beyond the near-tautological `mss==find_mss`): resolve `ConMin(...).acquire(...).mss_ids` → sorted constraint **names** via `provider.get_description`; assert equals a `GOLDEN_MSS_RS_1N` recorded **during implementation from the verified `AcqMSS` run** (memory: golden frozen from pre-existing code, not self-recorded). **Teeth:** any change in *which* constraints Stage-1 selects (shared-AcqMSS drift, wrong wiring surviving both pipelines) → RED. Implement-time sizing call: if `|MSS|` small (<~30) pin the full sorted-name list; if large, pin `n_mss` + a `sha256` of the joined sorted names (compact, still teeth). Names (not assumption IDs) so the golden survives ID renumbering.
4. Mode grid: **2 e2e runs** (RT-10, down from 4) — one **incremental** (RS-1n) + one **non-incremental** (FF) — proving mode-agnosticism (AcqMSS is already mode-agnostic; ConGen ships 3, ConMin Stage-1 needs no more).

## P1 micro-decisions (HOW-level, within "làm HOW" remit — not design re-decisions)

1. **Prep = delegation/composition for P1** (zero change to any ConGen file ⇒ zero regression risk to 507+1; guarantees Stage-1 ID parity by construction). **Not oversold as the arc endpoint (RT-4):** delegation is a black box that discards the per-`e⁻` NE assignment-assumption IDs (`task_preparation.py:205-208`) which brief §2 `neg_encodings` requires, so **P3 re-decides the seam** (subclass the existing `_prepare_negative_examples` hook and/or surface IDs from `GenerateNE`). Chosen for P1 because it is the minimum for Stage-1-only; the P3 re-decision is expected, per "leave later phases at seed until touched."
2. **`resolve_result` deferred** to P3/P4 (verified additive — `KBModel` is concrete, `BaseRunner` declares no resolve, so `ConMinModel` with only `prepare_task` is valid; the P1 tests never call resolve). **Pinned (RT-9):** mirror ConGen's **4-tuple** resolver (ConMin Reduces), but map the slice-based `ConMinResult` (no `redundant_ids`) rather than copy ConGen verbatim.
3. **Gate counter = `paper_consistency_checks`** — **correct for P1** (parity with `congen.py:103`), NOT a shortcut. **P4 debt reframed (RT-5, and confirmed by user as a P4-ESCALATION):** the §9c `admpool_gate_checks`/`admpool_checks` split is **not** a metrics-layer reclassification — gate + reused `AcqMSS` (`acqmss.py:79`) sum into one scalar at source, and `metrics.py:67` maps that one scalar, so no downstream layer can disaggregate. The real fix is **source-level**: parameterize the counter key inside the shared, frozen `AcqMSS`/gate (default preserves ConGen). That edits code shared with ConGen → at P4 **STOP and ask Cowork** (likely an ADR); do **not** patch at the metrics layer. It is **dual-emit (additive)** — add `admpool_gate_checks` alongside `paper_consistency_checks` — **never a rename** (a rename drops ConMin's gate from the universal total). Adding the taxonomy counter *now* is also wrong (a dead counter until P4's `CONMIN_METRICS`). See the seed P4 bullet's ⚠ marker.
4. **`kb_assumption_ids = []` in P1** (ConMin theory unassembled until Stage 2). `mss_ids = A`. Keeps the maximally-specific slice distinct from the ConMin slice per §9a (do not conflate).
5. **`acquire` signature mirrors ConGen** (`set_neg_tv=None, negation_map=None`). `negation_map` unused in P1 (no Reduce) but kept for P3 forward-compat + template symmetry; documented as reserved.

## Acceptance (P1)

- `PYTHONPATH=. pytest tests/test_boundary_guard.py -q` GREEN **before and after** (no new import escapes the façade).
- `PYTHONPATH=. pytest tests/test_conmin.py -v` GREEN.
- `PYTHONPATH=. pytest tests/ -q` → **507+N passed + 1 skipped**, no regression (N = new ConMin tests).
- Conventional commit, no AI refs (e.g. `feat(conmin): scaffold conmin package + Stage-1 parity`).
- Log the task in `plans/260721-conmin-impl/progress.md` (repo-local; the external Cowork `progress.md` is not this file).

## Docs-in-stage (P1)

- `docs/codebase-summary.md`: add `conacq/algorithms/conmin/` to the package inventory (5 files, "Stage-1 scaffold; cover/support/Reduce land P2–P3").
- **No new ADR** — no settled architecture *why* yet (the cover engine boundary + check-taxonomy ADRs arrive with P2/P4).

## Execution order (khung chung mỗi task, applied to P1)

1. Branch `feat/conmin` from `main` 62bfb9e; confirm baseline `pytest tests/ -q` = 507+1; `pip install -e ../explanation` present.
2. Boundary guard green (pre).
3. Scaffold files (model → builder → task_preparation → conmin → __init__ exports).
4. Write `tests/test_conmin.py`; `pytest tests/test_conmin.py -v` green.
5. Boundary guard green (post) → full suite no-regress.
6. Docs-in-stage; conventional commit; log `progress.md`; **STOP — summarise for review before P2.**

---

## Red Team Review

### Session — 2026-07-21 (3 hostile reviewers: Assumption Destroyer, Failure Mode Analyst, Scope & Complexity Critic; all findings `file:line`-backed)

**Verdict:** architecture sound (all 3 independently verified delegation/duck-typing/`TestCaseTask` constructor/`resolve_result`-deferral hold in code); fire concentrated on tests + debt-framing. **10 accepted (3 High), 3 rejected** (protecting locked scope). User adjudicated Option 1 (apply all accepted) + 2 additions.

| # | Finding | Sev | Disposition | Applied to |
|---|---------|-----|-------------|-----------|
| 1 | Gate untested; parity test near-tautological (`find_mss`==`find_mss`) | High | Accept | `TestConMinGate` (short-circuit + set/order stub tests) |
| 2 | Pre-authorized size-parity fallback weakens assertion | High | Accept | `test_stage1_matches_congen` — fallback removed, exact-set only |
| 3 | Inconsistent-return `TypeError` (required fields) | High | Accept | `ConMinResult` slice fields defaulted; error return safe |
| 4 | Delegation over-sold as arc endpoint (P3 tears it down) | High | Accept | `task_preparation.py` prose + micro-decision 1 reframed |
| 5 | P4 counter debt mis-framed as "rename" (metrics-layer split infeasible) | Med | Accept | micro-decision 3 + seed P4 ⚠ P4-ESCALATION (dual-emit, source-level, STOP-ask-Cowork) |
| 6 | Plan line 9 boundary false (guard is TWO façades) | Med | Accept | Boundary line corrected (`explanation.api` + `profiling`) — user confirmed `test_boundary_guard.py:42-43` |
| 7 | Two-checker equality rests on unstated ADR-0013 invariant | Med | Accept | `test_stage1_mss_is_unreduced...` docstring cites ADR-0013 (+ ADR-0017, user) |
| 8 | `ConMinTaskInput→ConGenTaskInput` clone-and-convert ceremony | Med | Accept | `prepare()` passes `task_input` directly (duck-typed) |
| 9 | `resolve_result` contract implicit; `ConMinResult` has no `redundant_ids` | Low | Accept | `conmin_model.py` note + micro-decision 2 (pin ConGen 4-tuple, map slices) |
| 10 | e2e grid over-scoped (4→2); builder tests over-cover inherited base | Low | Accept | `TestConMinModelBuilder` trimmed; grid = 2 runs |
| R1 | "Cut `ConMinResult` to 4 fields" (C2) | — | **Reject** | contradicts locked P1 scope (3 eval slices); kept + defaulted instead |
| R2 | "Drop `ConMinTaskInput` in P1" (C3) | — | **Reject** | contradicts locked P1 file list; kept type, dropped only conversion |
| R3 | "Add `admpool_gate_checks` now" | — | **Reject** | dead counter until P4 (both B/C reviewers agree) |

**User additions (beyond the 10):**
- **Extra-1 (characterization pin):** `test_stage1_characterization_golden` — pin the expected Stage-1 MSS on REAL-FM-7 by constraint **names** (golden recorded during implementation from the verified AcqMSS run), giving the Stage-1 test an *absolute* anchor beyond the near-tautological `mss==find_mss`. Optional-but-adopted.
- **Extra-2 (P4-ESCALATION):** the real finding-5 fix (parameterize the counter key in the frozen, ConGen-shared `AcqMSS`) is logged as a **P4-ESCALATION**: at P4, STOP and ask Cowork (likely an ADR) before touching shared code — never patch at the metrics layer.

### Whole-Plan Consistency Sweep — 2026-07-21, after applying the 10 findings

Re-read `impl-plan.md` in full (seed + detailed P1 + red-team log). Checks:
- **Boundary statement** (line 9) now matches the two-façade guard; `conmin.py`'s `profiling` import (line 106) labelled façade-safe — consistent. No stale "only explanation.api" left.
- **Counter debt** consistent across all three mentions (acquire step 2, micro-decision 3, seed P4 ⚠) — all say *P1 emits `paper_consistency_checks` (correct)*, *P4 = dual-emit source-level, STOP-ask-Cowork*, *never a rename*. No contradiction.
- **Delegation framing** consistent (task_preparation prose + micro-decision 1): P1-local, P3 re-decides the seam; no surviving "arc choice / diverge only in neg step" claim.
- **`ConMinResult` shape** consistent: slices kept + defaulted; error return (step 2) and success return (step 4) both valid under the defaults; test asserts only `kb_assumption_ids == []` (no phantom multi-slice assertion).
- **Test naming** reconciled: seed "Tests to add" now points to the P1 classes (`TestConMinModelBuilder`/`TestConMinGate`/`TestConMinStage1`); no `TestConMin`-vs-`TestConMinStage1` ambiguity.
- **ADR refs**: ADR-0017 (line 8, 183) consistent; ADR-0013 (line 183) carries a code-time existence check.
- **Rejected findings** (R1–R3) do not leak into any accepted edit (slices kept, `ConMinTaskInput` kept, no taxonomy counter added in P1).

**Result: zero unresolved contradictions.** Plan is internally consistent and ready to implement P1.

---

# P2 — Detailed HOW (expanded 2026-07-22, on `feat/conmin` @ `a0e1e79`) — DONE, committed `1c0d941`

**Scope:** the `AcqMinCover` engine (`w≡1`) as a standalone, unit-tested module. **NOT** wired into `ConMin.acquire` yet, and it does **NOT** consume real `neg_encodings` from the prep — both are P3 (the delegation seam stays intact, per P1 micro-decision 1). P2 tests feed synthetic cover maps + a stub checker (the worked example is the oracle).

## DELTA-CHECK (v2 authoritative sources vs code) — clean

Re-synced against `ConMin - AcqMinCover v2.md` (§3 algorithm) + `ConMin - AcqMinCover v2 Worked Example.md` (the frozen oracle) + brief §3.
- `QuickXPlain(checker, profiler).find_conflict(set_c, set_b) -> List` — on `explanation.api`, exact match to brief §3 `QuickXPlain(A, BG∪{e⁻})`. ✅
- `ConsistencyChecker.is_consistent(set_c) -> bool` — exact match to brief §3 `Inconsistent({c}∪BG∪{e⁻})`. ✅
- **Stale seed ref:** seed **P4** bullet says `tau=20`; brief §8 decision 3 resolves **`tau=15`** ("20 was rejected as needlessly generous"). Brief wins → default `tau=15`. (Seed P2 already says 15.) Fix the seed P4 `tau=20` at P4.
- Worked-example oracle (checked programmatically in the note, frozen 2026-07-03): G₃ = ⟨{n1→n2, n3→n4, n5→n6}, {mb1..mb6}⟩ → **exact = {n1→n2, n3→n4}** (2), **greedy = 3** (keeps over-fit n5→n6), **irredundant** recovers 2 from greedy's 3.

## Files

**Create** (`conacq/algorithms/conmin/`):
- `min_cover.py` — the **pure** combinatorial solver (no checker/solver import): `weight`, `connected_components`, `exact_cover`, `greedy_cover`, `irredundant`. Unit-tested with hand-built cover maps.
- `acqmincover.py` — the **checker-driven** engine: `NegEncoding`, `CoverResult`, `AcqMinCover` class (Phase A build via checker + QuickXplain; Phases B–D via `min_cover`).

**Modify:** `conacq/algorithms/conmin/__init__.py` (export `AcqMinCover, CoverResult, NegEncoding`); `tests/test_conmin.py` (add `TestMinCover`, `TestAcqMinCover`); `docs/codebase-summary.md` (inventory).

Split rationale (modularization): the pure combinatorial core (~120 LOC) and the checker-driven Phase-A/orchestrator (~110 LOC) are a real logical boundary and match the test split (pure cover-map units vs stub-checker units); both stay well under the 200-line Python threshold.

## `min_cover.py` — pure solver (Element = `frozenset[int]` of constraint aids; Neg = any hashable)

- `weight(element, unit_weight=None) -> number` — `unit_weight is None` ⇒ `len(element)` (w≡1); else `sum(unit_weight(c) for c in element)`. Compound elements weigh Σ (dispreferred).
- `connected_components(cover: Dict[Element, Set[Neg]]) -> List[Tuple[Set[Element], Set[Neg]]]` — union-find over elements; link `x,y` iff `cover[x] ∩ cover[y] ≠ ∅`; each returned `negs_i = ⋃ cover[x]`. Deterministic order (sort elements by `sorted(element)` key).
- `exact_cover(elements, negs, cover, unit_weight=None) -> Set[Element]` — **min-cardinality-first**: for `k=1,2,…`, `itertools.combinations` over elements sorted by key; keep combos whose `⋃ cover ⊇ negs`; return the first-size non-empty result's **min-Σweight** combo (tie → lexicographically smallest by sorted keys). Deterministic.
- `greedy_cover(elements, negs, cover, unit_weight=None) -> Set[Element]` — repeatedly take the element covering the most still-uncovered negs (tie → min `weight`, then key). `H(d)` fallback.
- `irredundant(selected, negs, cover) -> Set[Element]` — iterate selected in key order; drop `x` if `selected∖{x}` still covers `negs`. Set-based, no solver.

## `acqmincover.py` — checker-driven engine (mirrors `AcqMSS` class shape)

```python
@dataclass(frozen=True)
class NegEncoding:                 # engine input contract (brief §2 produces these in P3)
    neg_id: int
    assumption_ids: Tuple[int, ...]   # e⁻'s assignment-assumption IDs to activate

@dataclass
class CoverResult:
    cover_elements: List[FrozenSet[int]]   # C (flatten via ⋃ at P3 line 5)
    uncoverable: List[int]                 # U (neg_ids)
    n_components: int
    largest_component: int
    n_greedy_fallback: int

class AcqMinCover:
    def __init__(self, checker, tau=15, unit_weight=None, profiler_instance=None): ...
    def cover(self, admissible, neg_encodings, bg) -> CoverResult:
        # Phase A: per e⁻, cand = [c in admissible if not checker.is_consistent([c]+bg+aids)]
        #   cand≠∅ → each {c} a singleton element; else QuickXplain(A, bg+aids) → compound Sx
        #   (partial-neg only, v2 §5); Sx=∅ → neg_id → U.  Increments cover_rejection_checks /
        #   cover_quickxplain_checks at the natural site (see decision 3).
        # Phase B: components = connected_components(cover)
        # Phase C: per comp, exact_cover if |elems|≤tau else greedy_cover (n_greedy++)
        # Phase D: irredundant(C, all_coverable_negs, cover)
```

## Test design (append to `tests/test_conmin.py`)

**`TestMinCover`** — pure, hand-built cover maps from the worked example (§4/§5), no checker:
- `test_exact_beats_greedy_on_G3` (oracle b): cover = {`{n1→n2}`:{mb1,mb2,mb3}, `{n3→n4}`:{mb4,mb5,mb6}, `{n5→n6}`:{mb2,mb3,mb4,mb5}}; `exact_cover` returns `{ {n1→n2},{n3→n4} }` (2); `greedy_cover` returns 3 (incl `{n5→n6}`). **Teeth:** the whole point of v2.
- `test_irredundant_recovers_exact_from_greedy` (oracle e): `irredundant(greedy_result, negs, cover)` → the 2-element cover.
- `test_connected_components_separates` (oracle a): the full 8-negative worked-example cover fragments into the expected components (G₁,G₂,G₃; G₄/u⁻ handled in Phase-A tests); union of per-component exact covers = `{id→db, id→¬ga, n1→n2, n3→n4}`.
- `test_weight_tiebreak`: two equal-cardinality covers → the lower-Σweight one wins (w≡1 ⇒ prefers fewer/smaller compounds).

**`TestAcqMinCover`** — Phase A with a rule-based stub checker (mirrors `_MutualRedundancyChecker`):
- `test_compound_branch_places_Sx` (oracle c): stub models block-C — `pc⁻` consistent with `t→u` alone and `u→¬v` alone, inconsistent with both. `cand=∅` → `QuickXplain` returns `{t→u, u→¬v}` → one compound element; `cover()` terminates. (Verify `QuickXPlain` needs only `is_consistent`; add `find_model`/`cleanup` no-ops to the stub if required.)
- `test_uncoverable_goes_to_U` (oracle d): stub `is_consistent`≡True → `cand=∅`, `QuickXplain`→∅ → neg_id in `U`, `C` empty.
- `test_singletons_end_to_end`: stub where each e⁻ is rejected by exactly one c → `cover()` returns the singleton cover, correct `n_components`.

## P2 micro-decisions

1. **Split `min_cover.py` (pure) / `acqmincover.py` (checker-driven)** — modularization + testability boundary; the pure solver has zero `explanation`/`profiling` coupling.
2. **`AcqMinCover` is a class** (holds checker/tau/weight/profiler) mirroring `AcqMSS`; the pure solver is module-level functions (stateless).
3. **Counter instrumentation IS done in P2** (`cover_rejection_checks`, `cover_quickxplain_checks`) at their natural Phase-A sites — unlike the rejected "add `admpool_gate_checks` now", these are **fresh, ConMin-only** sites (no frozen-shared-code split, no retrofit), exactly how every algorithm counts its own checks. P4 only declares the `MetricSpec` to surface them; no reporting added in P2.
4. **`tau=15` default** (brief §8, not seed-P4's stale 20); **`w≡1` default** (arity weight is P4).
5. **No `ConMin.acquire` wiring, no real `neg_encodings`** — P3. The engine takes `neg_encodings` as a parameter; P2 proves it in isolation.

## Acceptance (P2)

- `TestMinCover` + `TestAcqMinCover` green (worked-example oracle a–e).
- boundary guard green (`min_cover.py` imports nothing from `explanation`; `acqmincover.py` imports `QuickXPlain` via `explanation.api` only).
- full suite no-regress (`517 + M` passed + 1 skipped).
- docs-in-stage (`codebase-summary.md`); conventional commit; log `progress.md`; **STOP — summarise for review before P3.**

## Deferred to P3 (reminders carried from P1)
- **De-delegate the prep** to capture `neg_encodings` (the delegation black box discards per-`e⁻` assignment-assumption IDs); wire `AcqMinCover` into `ConMin.acquire` (lines 5–8: `Cflat = ⋃C`, `S`, `¬e⁻` fallbacks, `Reduce`).
- **P4-ESCALATION** unchanged (counter split touches frozen shared `AcqMSS` → STOP-ask-Cowork).

---

# P3 — Detailed HOW (expanded 2026-07-22, on `feat/conmin` @ `1c0d941`) — PLANNED, awaiting review

**Scope (integration, heavy):** (a) de-delegate the prep to capture **real** `neg_encodings` (brief §2); (b) `support⁺` general-CNF "≥1 clause critical" at the prep layer (brief §4, `build_support_count`); (c) wire `ConMin.acquire` lines 5–8. **Acceptance:** on the paper working-example inputs, ConMin returns `C_τ` for `k∈{1,2}` and the pure minimum cover for `k≥3`. Full suite + P1/P2 no-regress.

## DELTA-CHECK (brief §2/§4 + code) — one gap surfaced (test strategy), rest clean

- **`GenerateNE` discards the assignment aids (verified `generate_ne.py:107,110,137`).** Per `e⁻`, it allocates an `aid` per assignment and adds the guard clause `[var, -aid]` (aid ⇒ var) to a **local** `set_kb` for the QuickXplain probe, then persists **only** `ne_clause` (line 137). So the per-`e⁻` assignment aids + their guard clauses never reach the task KB. **Brief §2 sanctions the fix** ("keep the assignment assumptions accessible rather than only emitting the blocking clause").
- **ID-preservation constraint (load-bearing).** P3 must keep the Stage-1 allocation order **identical** so P1's `test_stage1_matches_congen` + `test_stage1_characterization_golden` (sha `d13274bc…`) stay green. This holds *iff*: (i) ConMin allocates the exact same aids in the same order as ConGen (it already allocates the assignment aids — `generate_ne.py:107` — even though it discards the clauses), and (ii) the newly-**persisted** guard clauses `[var, -aid]` stay **vacuous** when their guard aid is inactive (`¬aid ∨ var` is trivially true), so AcqMSS — which never activates them — computes the same MSS. **Verify by re-running the golden after the change** (a changed sha = a real divergence to investigate).
- **`Reduce.reduce(set_b_prime, set_neg_tv, set_bg, negation_map)`** builds `kb = dict.fromkeys(set_b_prime + set_neg_tv)` in order and drops `c` when `is_consistent(BG ∪ (kb∖{c}) ∪ {¬c})` is False (`reduce.py:66,83-84`). Needs a `negation_map` entry per KB constraint — **already present**: bias constraints via `prepare_kb` (→ `model.negated_constraint_map`), NE ids via `_create_negated_ne`.
- **Rejection test isolation (verified sound).** AcqMinCover's `is_consistent([c] + BG + e⁻.aids)` on the task checker: bias/E+/NE clauses are guarded by *inactive* aids (vacuous), so only `c`'s clause + BG root + the activated assignment guards are live → False iff `c` contradicts `e⁻`'s assignment. Correct; not polluted by NE.

## Key design (worked out from code + brief)

**`neg_encodings` identity — `neg_id := ne_id`.** Make each negative's identifier its NE assumption id. Then `AcqMinCover`'s `CoverResult.uncoverable` (a list of `neg_id`s) **is** the list of fallback NE ids directly — no separate `e⁻ → NE` map. `NegEncoding(neg_id=ne_id, assumption_ids=<full per-feature assignment aids of e⁻>)`. (P2's engine already keys on `neg_id`; synthetic P2 tests unaffected.)

**De-delegation (touches shared code, additive, default-preserving):**
1. **Extend `GenerateNE`** with `capture_assignments: bool = False`. When True: persist each guard clause `[var, -aid]` into `result_set_kb` (so the task checker can activate it) and return the per-`e⁻` assignment aids alongside `ne_id`. Default False ⇒ ConGen path byte-identical.
2. **Refactor `ConGenTaskPreparation` minimally** (additive): extract a `_make_task(**fields) -> TestCaseTask` factory (returns `ConGenTask`); have `_prepare_negative_examples` optionally collect `(ne_id, assignment_aids)` per `e⁻` when capture is on.
3. **`ConMinTaskPreparation(ConGenTaskPreparation)`** overrides `_make_task` → `ConMinTask` (with `neg_encodings` + `support_count`), enables capture, and calls `build_support_count`. This **replaces the P1 delegation** with subclassing via the existing `_prepare_negative_examples` hook (the seam re-decision promised in P1 micro-decision 1).

**`ConMinTask` gains** (frozen, defaulted so P1/P2 construction still works): `neg_encodings: Tuple[NegEncoding, ...] = ()`, `support_count: Mapping[int, int] = <empty>`.

**`support.py` (prep layer, solver-free, brief §4):**
- `exercises(clauses, amap) -> bool` — the brief §4 sketch verbatim: `e⁺` satisfies every clause AND ≥1 clause is *critically satisfied* (exactly one literal true, all its vars assigned). Returns False on any unsatisfied clause.
- `build_support_count(constraint_aids, describe, constraint_map, name_to_id, positive_testsuite) -> Dict[int,int]` — for each bias aid: name via `describe.get_description(aid)` → CNF via `constraint_map[name]`; count `e⁺` (assignments mapped through `name_to_id` to `{var_id: bool}`) that `exercises` it.

**`ConMin.acquire` lines 5–8** (extend the P1 body; new params `neg_encodings`, `support_count`, `k`):
```
A = AcqMSS(...)                                   # P1, unchanged
cover = AcqMinCover(checker, tau, profiler).cover(A, neg_encodings, BG)   # line 4/5 (P2 engine)
Cflat = ⋃ cover.cover_elements                     # flatten compounds (v2 §0 item 2)
S = [c for c in A if c not in Cflat and support_count.get(c,0) >= k]      # line 6
fallbacks = cover.uncoverable                       # {¬e⁻ : e⁻∈U} == the uncoverable NE ids
assembled = list(fallbacks) + list(S) + sorted(Cflat)   # Reduce order: fallbacks → S → C
redundant, kb = Reduce(checker, profiler).reduce(assembled, [], BG, negation_map)  # line 8
```
Populate `ConMinResult` all slices: `mss_ids=A`, `cover_ids=Cflat`, `support_ids=S`, `fallback_ids=fallbacks`, `uncoverable=U`, `kb_assumption_ids=kb`, counts, + cover metrics from `CoverResult`.

## Test strategy — RESOLVED 2026-07-22: **B now, A later** (user)

Implement **strategy B (synthetic assembly test)** in P3 — a fast, precise gate on the *new* P3 logic (S-filter, fallbacks, Reduce order). Defer **strategy A (full 3-block dataset + full-pipeline e2e)** to the paper-writing/eval phase when the faithful numbers are needed for the paper table. (AcqMinCover + support⁺ are already unit-tested, so B has real teeth on what P3 adds.)

Original framing (both strategies, for the deferred A):
- **(A) Build the working-example dataset** — author `data/fms/conmin-working-example.uvl` (3 blocks) + bias JSON + E⁺/E⁻ JSON, run the **full** `ConMin.acquire` pipeline, assert the resolved KB == `C_τ` for `k∈{1,2}` and the min-cover for `k≥3`. Most faithful; ~1–2h of careful UVL/bias authoring + oracle risk (must match the note's hand-computed verdicts).
- **(B) Synthetic assembly unit-test** — hand-build `A`, `cover_elements`, `support_count`, `U` matching the worked example (§3–§8 values), drive the **assembly + Reduce** (lines 5–8) directly, assert `C_τ`/min-cover per `k`. Lighter; tests the *new* P3 logic (S-filter, fallbacks, order) precisely; the AcqMinCover + support pieces are already unit-tested (P2 + TestSupport). Less end-to-end.

## Tests (P3)
- `TestSupport` — `exercises`/`build_support_count` per operator (requires/excludes single-clause; mandatory/alternative/or multi-clause; "≥1 clause critical"; partial-`e⁺` accrues none), from brief §4.
- `TestConMinReducesToWorkingExample` — strategy (A) or (B) per the open question.
- P1/P2 regression incl. **re-pin/confirm the golden sha** (should be unchanged).

## P3 micro-decisions
1. `neg_id := ne_id` (fallbacks fall out of `U` for free).
2. De-delegation = extend `GenerateNE` (capture flag) + subclass `ConGenTaskPreparation` via `_make_task` + `_prepare_negative_examples` hook; **additive, default-preserving** (ConGen suite is the safety net). Brief §2 sanctions the GenerateNE extension, so this is HOW, not a design re-decision.
3. Reduce input = assembled KB (`fallbacks + S + Cflat`), `set_neg_tv=[]` (the theory already contains the memorised NEs as fallbacks; coverable NEs are replaced by cover constraints). Order fallbacks→S→C per your instruction (survivor order, ADR-0017).
4. `cover_ids = Cflat` (flattened), not raw compound elements — the algorithm-core slice stays assumption-only.

## Risks
- **ID drift** breaking the golden (mitigation: identical alloc order + vacuous guard clauses; the golden test is the tripwire).
- **Shared-code touch** (`GenerateNE`, `ConGenTaskPreparation`): additive + default-off, but the ConGen suite (`test_congen.py`) + P1 parity tests must stay green — run them explicitly.
- **Working-example fidelity** (strategy A): the UVL/bias must reproduce the note's hand-computed rejection sets exactly.

---

## P3 — RED-TEAM REVISION (2026-07-22): supersedes the above where it conflicts

P3 red-team (3 hostile reviewers, all `file:line`-backed) → **1 Critical + 4 High + 7 Med, ALL accepted** (user, no rejects). **Brief §2 was updated by Cowork the same day and now matches these findings + my fix** (verified: the spec §2 documents the combine trap + "register the already-built per-`e⁻` negated form, keep combined for Stage-1, golden unchanged"). Split into **P3a (ff-gate first)** then **P3b**.

### Critical fix (confirmed on code + brief §2)
`_combine_ne_constraints` (`task_preparation.py:234-245`) registers only the **combined** `ne_id` in `negation_map` (`:217`); the per-`e⁻` negated forms **are built** in `_create_negated_ne`'s multi-branch (`:263-270`) but **never registered** → a per-`e⁻` fallback hits `reduce.py:76` (warn + **silent skip**). Masked by the 1-negative `rs_1n` golden. **Fix (no id shift):** ConMin's prep registers `negation_map[per-e⁻ ne_id] = its already-built negated form`; keeps the combined NE in `set_neg_tv` → Stage-1 golden `d13274bc…` unchanged.

### The 12 accepted fixes (dispositions)
1. **[Crit]** register per-`e⁻` negations (above); `neg_encodings` per-`e⁻`, `neg_id := per-e⁻ ne_id`.
2. **[High]** capture **full-config** assignment aids from `assumption_to_var.keys()` (NOT the post-QuickXplain `set_tv`, overwritten to `minimal_conflict` at `generate_ne.py:~124`).
3. **[High]** `ConMinResult += redundant_ids` (defaulted); populate from `Reduce`'s `(redundant, kb)` — also completes the resolve_result 4-tuple.
4. **[High]** **ff-3-negative real-checker gate test FIRST** (user requirement) — the fallback-reduce path must be green before the rest of P3 lands; it catches the Critical the 1-neg golden cannot.
5. **[High→Med]** `exercises()` guarded lookup (`v not in amap` → unassigned, never `KeyError`); `TestSupport` asserts **exact counts**, not `>0`.
6. **[Med]** `GenerateNE` capture = **additive** defaulted `assignment_aids` field on `NEPerTestcase` (do not reshape the return); persist guard clauses gated by the flag.
7. **[Med]** ConGen tripwire gates (run before+after): `test_t11_prepared_task_ids`, `test_t11_e2e_learned_kb`, `generate_ne` subproblem tests, and `next_available_id` unmoved. **NOT a P4-ESCALATION** (in-repo `acqmss/`, not the frozen framework — user-confirmed).
8. **[Med]** `build_support_count` validates each aid resolves to a `constraint_map` key (fail loud; no silent `.get([])`).
9. **[Med]** `TestSupport` pins exact per-operator counts incl. satisfied-but-not-critical (see §support conflict below).
10. **[Med]** `acquire(..., k: int = 1)` default; P4 sources `k` from config. Acquire params come **from the task** (mirror ConGen runner); document `fallback_ids == uncoverable` under `neg_id:=ne_id`.
11. **[Med]** de-delegation overrides `_prepare_negative_examples` additively (+ `_make_task` factory in ConGen prep) — deeper than "just `_make_task`".
12. **[Med]** `Reduce(assembled, set_neg_tv=[], BG, negation_map)`: **resolved equivalent** to paper `Reduce(KB, NE, BG)` — coverable NEs are redundant (entailed by cover) so omitting them = same result. Document, don't assert.

### Acceptance — UPDATED to the new multi-valued working example (`ConMin - new working example (multi-valued) - proposal.md`, hand-verified)
Domains `os∈{lin,win,mac}, db∈{none,lite,srv}, ide∈{none,std,pro}`; bias `c1..c48` (requires+excludes over 7 literals); BG=`{c44: pro→lin}`. `A` = 16 constraints `{c12,c16,c17..c24,c31,c32,c36,c42,c44,c48}`; `cand(e⁻₁)={c31,c48}, cand(e⁻₂)={c48}, cand(e⁻₃)={c12,c32}`; cover **`C={c48,c12}`** (c48 covers 2; tie-break "most general" picks c12 over c32); `U=∅`.
- **k∈{1,2}: final KB = `{c48,c32,c42}` = `C_τ`** (Reduce removes c16,c31,c36,c44 [entailed] + c12 [subsumed by S-recovered c32]).
- **k≥3: S=∅ → pure cover `{c48,c12}`** (min-cover, maximally-general boundary).

### support⁺ — RESOLVED 2026-07-22 (brief §4 updated; re-sync §4 before coding P3b)
**Unified 6-operator definition:** `support(c) = min over c's minimal violations, of [ min over the literals that violation forces PRESENT, of #{e⁺ ⊨ literal} ]`. Count only **present** triggers; a trigger never observed ⇒ support 0 ⇒ vacuous ⇒ drop (unless the cover forces it in). Per-operator (present-literal set of each minimal violation → witness):

| operator | minimal-violation present-literals | support |
|---|---|---|
| requires `A→B` | `{A}` | `#A` |
| excludes `¬(A∧B)` | `{A,B}` | `min(#A,#B)` |
| optional `C→P` | `{C}` | `#C` |
| mandatory `P⟺C` | `{P},{C}` | `min(#P,#C)` |
| or `P⟺∨Cᵢ` | `{P},{C₁}..{Cₙ}` | `min(#P, minᵢ #Cᵢ)` |
| alternative | as `or` (+ `{Cᵢ,Cⱼ}` dominated) | `min(#P, minᵢ #Cᵢ)` (**alternative == or**, proven) |

Strict: any child unobserved (`#Cᵢ=0`) ⇒ group support 0; `#A=0` ⇒ drop `A→B`. Reproduces the paper table (`c48=1`, `c16=1`, `mac=0`). `TestSupport` pins all 6 operators + alternative==or + strict-zero, plus the k-sweep (k∈{1,2}→C_τ, k≥3→min-cover).

### ⏸ P4-DECISION (deferred, awaiting Viet-Man): rejection-test BG on real FMs
On real FMs the ff negatives violate the FM root, so `is_consistent(root ∪ e⁻)` is UNSAT (cand degenerates to all of A: 732→102, 762→102; only the BG-consistent 747→16/102; BG=∅ → 33/16/19). Brief §2 records a block "Rejection-test BG on real feature models". **Decision (rejection-test + Stage-1 BG = minimal for real FM) is P4 — do NOT touch Stage-1 BG / the golden now.** The synthetic working example (P3b) is BG-consistent by construction, so it is unaffected. The ff-gate therefore asserts **de-delegation invariants only** (option #2), NOT cover-correctness.

### P3a scope (this milestone): de-delegation + fallback-reduce + ff-gate
Extend `GenerateNE` (capture) → ConMin prep (`neg_encodings` + per-`e⁻` negation) → `acquire` cover→flatten→fallbacks→assemble(F→S→C, S empty for now)→Reduce → **ff-3-neg real-checker gate green** + ConGen tripwires green + full suite no-regress. **STOP for verification.** support⁺ + working-example test = **P3b** (after the §7 conflict is resolved).

---

# P4 — Evaluation (seed 2026-07-22; critical path, AAAI deadline 2026-07-28)

**Authoritative ordering + acceptance:** brief §7 P4a–P4g (graceful degradation — core quality tables first). Re-sync §7 + the note `Root-constraint BG semantics (ConGen + ConMin).md` before touching anything. Detail each sub-step in this file before coding it, same as P1–P3.

**Order (do NOT reorder without asking):**
1. **P4a — root-constraint BG refactor** (START HERE). Root non-emptiness = post-acquisition axiom, NOT in BG at runtime; Reduce BG = **domain-only** (keep multi-valued domain axioms, NOT unconditionally empty); fix eval negatives to **root-present**. Apply across Stage 1 AND Stage 2; the Stage-1 golden `d13274bc` **will flip → re-pin it deliberately** (record the new value + reason; loud characterization, not silent). ConGen tripwires must stay green (this changes ConMin's BG usage, not ConGen's). **STOP after P4a — Cowork verifies the re-pin + non-degenerate real-FM cover before P4b.**
2. P4b — `resolve_result` 4-tuple.
3. P4c — `ConMinRunner` + `run_conmin.py` + CV (emit the shared KB JSON).
4. P4d — comparison conditions (3 slices + existing QuAcq) + run experiments → fill quality tables. **Core paper story done here.**
5. P4e — §9c metrics taxonomy (shared-`AcqMSS` counter dual-emit → tripwires + likely ADR).
6. P4f — passive baseline (Coulombe & Quimper 2022) — LAST; degrade to argued-discussion if time runs out.
7. P4g — `conmin.py` split (hygiene).

`weight`=arity lands with P4d/P4e; `tau=15`. Out of scope (AAAI): ≥5000-feature model.

---

# P4a — Detailed HOW (2026-07-22): root-constraint BG refactor

**Re-sync:** note `Root-constraint BG semantics (ConGen + ConMin).md` + brief §7 (both updated by Cowork). Root non-emptiness fact = **post-acquisition axiom**, out of the acquisition BG; Reduce/gate/AcqMSS/cover BG = **domain-only**. Applies to ConMin only (ConGen unchanged — a SoSyM revision item, not this task).

## ⭐ DELTA-CHECK (golden is INERT — brief's "re-pin" was wrong, confirmed by user)
Probed on REAL-FM-7/rs_1n: `AcqMSS.find_mss` gives the **byte-identical 78-constraint MSS, sha `d13274bc…`** with `set_bg=[28]` (root) OR `set_bg=[]`. A complete positive already selects the root, so `root→jplug` adds nothing to Stage-1. **⇒ the Stage-1 golden HOLDS; it is NOT re-pinned.** The golden test staying green is the loud, honest confirmation that Stage-1 is unaffected. (What changes is *downstream*: Reduce keeps `X→root`; the cover stops degenerating.)

## The change (generic: drop root, keep domain axioms)
- **`root_id = bg_data.assumptions[0]`** (REAL-FM-7 = `28`; `set_b = [28]`). ConMin's acquisition BG = `domain_bg = tuple(a for a in task.set_b if a != root_id)`. For boolean FMs `set_b = (root,)` ⇒ `domain_bg = ()`; for multi-valued, the domain axioms in `set_b` survive. **Do NOT hardcode `()`** — derive by dropping the root.
- ConMin's prep (already overrides `prepare`) additionally: `root_axiom = tuple(task.set_b)`; `replace(task, set_b=domain_bg, root_axiom=root_axiom, support_count=…)`. So `acquire`'s `set_bg = task.set_b` is now domain-only — gate, `AcqMSS`, `AcqMinCover`, `Reduce` all see it; no acquire-signature change.
- **`ConMinTask += root_axiom: Tuple[int,...] = ()`** — the non-emptiness axiom, appended to the delivered/eval theory in P4b (`delivered = acquired ∪ {root}`). Apples-to-apples: ground truth also carries the root, so the comparison is consistent.

## Effects (verified/expected)
- **Cover non-degenerate** (P4a acceptance): `is_consistent([c] + domain_bg + aids)` with `domain_bg=()` ⇒ `cand` a proper subset (root no longer trivially UNSAT with root-absent negatives).
- **`X→root` acquired**: Reduce no longer entailed-drops them (`root ⊨ X→root` gone). On rs_1n, `c6/c14/c18` (optional children of root) survive → verify in-code.
- **Stage-1 golden**: HOLDS `d13274bc` (inert). `test_stage1_characterization_golden` passes unchanged; docstring notes the inertness.

## Test impacts
- `test_stage1_characterization_golden` — **holds green** (no re-pin); add a docstring line: Stage-1 inert to the root-BG drop (verified).
- `test_stage1_matches_congen` — ConMin `set_b` now diverges: assert `conmin.set_b == ()` (domain-only) vs `congen.set_b == (28,)` (root); the **MSS still matches** (inert), keep that assertion.
- `TestConMinDeDelegation` (ff-gate) — `domain_bg=()` ⇒ cand discriminates on **all** negatives: assert a proper-subset cand for each; **remove** the "P4-DECISION deferred / rejection-test BG" note (resolved here). The root-absent ff negatives are still FM-malformed → eval-negative regeneration (root-present) is a **P4d** concern (the shared ff fixture stays; ConGen depends on it).
- **New:** a real-FM check that `X→root` survives Reduce under domain-only BG (rs_1n: assert `c6/c14/c18` in the acquired KB, or ≥1 `X→root` kept).
- **ConGen tripwires** (`test_congen`, `test_t11_*`) — green; ConMin's prep override is the only change, ConGen's prep untouched.

## Acceptance (P4a) — user verifies at STOP
golden green (inert, proof recorded); cover non-degenerate on real FM (cand proper subsets); `X→root` acquired; ConGen tripwires green. Then STOP (no P4b).

## P4 forward-notes (captured at P4a; land in the named phase)

- **P4c — `ConMinRunner` MUST wire the task + assert (foot-gun #5, code-review + user):** the runner passes `task.neg_encodings` **and** `task.support_count` into `ConMin.acquire` (they are on the task, not auto-read). **ADD AN ASSERT**: if there are negatives (`task.set_tv`/E⁻ non-empty) but `neg_encodings` is empty → **raise**, do NOT silently return an empty KB. `acquire` currently no-ops the cover/support tail when `neg_encodings=()` (correct for a Stage-1-only call, but a silent foot-gun once a runner exists — the user hit it while probing). Land the guard in `ConMinRunner`, not in `acquire` (Stage-1-only callers legitimately omit it).
- **P4b — `resolve_result` appends the root axiom:** the resolved/delivered theory = `acquired KB ∪ {root_axiom}` (from `ConMinTask.root_axiom`). Ground truth also carries the root, so the eval comparison is apples-to-apples. Without this, `X→root` recall would look inflated/deflated vs a root-bearing ground truth.

---

# P4b — Detailed HOW (2026-07-22): resolve_result (4-tuple) + root re-append

**Re-sync:** brief §5 (`conmin_model.py` = `ConMinModel(KBModel)`; `prepare_task` + `resolve_result`), §7 P4b, note "Root-constraint BG semantics" (delivered theory = acquired ∪ {root}).

## DELTA-CHECK (verified in code)
- **Mirror source** `ConGenModel.resolve_result(result, describe, root_clauses) -> (bg_clauses, kb_clauses, kb_names, redundant_names)` (`congen_model.py:54-73`): `bg_clauses = root_clauses`; `kb_clauses/kb_names = _resolve_ids(describe, result.kb_assumption_ids)`; `redundant_names = _resolve_ids(describe, result.redundant_ids)`. `_resolve_ids` maps aid→name via `describe` and name→CNF via `self.constraint_map`.
- **`ConMinResult` already has `kb_assumption_ids` + `redundant_ids`** (P3, `conmin.py:56-57`).
- **The eval UNIONS bg into the compared theory** — `cross_validation.py:215` (`kb_clauses + bg_clauses`), `kb_comparator.py:211-214` (adds `bg_clauses` to the compared set). So `bg_clauses = root` ⇒ root IS in the delivered theory, **separate from `kb_clauses` (acquired)** → apples-to-apples with the root-bearing ground truth; root NOT counted as a learned constraint. This is exactly the P4a intent, achieved by mirroring ConGen.
- **Root source** `oracle_data.get_root_clauses() = [[1]]` (jplug=true) — the same root `task.root_axiom=[28]` records (P4a). `resolve_result` is stateless (takes pre-resolved `root_clauses`); the caller (P4c runner) passes `get_root_clauses()`.

## Change (conmin/ only — no ConGen/shared touch)
`ConMinModel.resolve_result(result, describe, root_clauses)` — copy ConGen's pattern into `conmin/conmin_model.py` (a mirror, not a shared-code edit): `bg_clauses = root_clauses` (the post-acquisition root axiom); `kb_clauses,kb_names = _resolve_ids(describe, result.kb_assumption_ids)`; `_,redundant_names = _resolve_ids(describe, result.redundant_ids)`. Add a private `_resolve_ids` (copy). Docstring: `bg_clauses` is the given root axiom (`task.root_axiom`), re-appended for delivery; `kb_clauses` is the acquired theory (root excluded), so metrics never count the root as learned.

## Test (`tests/test_conmin.py`, mirror the ConGen runner-net resolve style)
`TestConMinResolveResult` on REAL-FM-7 rs_1n: build model+task, `acquire` (KB=16 incl c6/c14/c18), then `resolve_result(result, describe, oracle.oracle_data.get_root_clauses())`:
- `kb_names` == the acquired constraint names (incl `c6/c14/c18`); `kb_clauses` == their CNF (from constraint_map).
- `bg_clauses == [[1]]` (root axiom) == `get_root_clauses()`; and `task.root_axiom != ()` (P4a record present).
- **Root separation:** the root axiom clause `[1]` (jplug=true) is in `bg_clauses`, NOT in `kb_clauses` (acquired) — the metric can't miscount it.
- `redundant_names` == `_resolve_ids` of `result.redundant_ids` (resolve consistency).

## Acceptance / guardrails
resolve returns correct clauses/names for a real acquired KB; root axiom in the delivered theory (bg), not in acquired (kb); redundant_names match redundant_ids. Boundary guard green; full suite no regress; ConGen untouched. Code-review gate before "done"; STOP for user verify (self-resolve a real KB, check root + name mapping).

**P4b landed as a 5-part decomposition + red-team hardening** (commits `ae1f73d`, `c07e21a`) — supersedes the 4-tuple above: `(bg, kb_clauses, kb_names, fallback_clauses, redundant_names)`; loud guard on unresolvable non-FM ids (incl neg=None); A3 = FM-only redundant, deferred to §9c/P4e.

# P4c — Detailed HOW (2026-07-22): ConMinRunner + CLI + CV wiring

## Scout (mirror sources read)
`congen_runner.py` (build-once model → per-fold prepare→build_checker→acquire→collect→resolve), `base_runner.py` (BaseRunResult/BaseRunner), `metrics.py` (MetricSpec tables + `_CORE`/`COMMON_KEYS` + disjointness), `cross_validation.py` (`_run_cv_loop` is GENERIC over any `BaseRunner`), `run_congen.py`/`run_cv.py`/config, `report.py` (`save_kb_result(..., metadata=)`), `test_t9_metrics_safety_net.py` + `test_evaluation.py:377` (disjointness = `CONGEN∩QUACQ ⊆ COMMON_KEYS`).

## ⭐ DELTA-CHECK (brief vs code — 2 additive scope nuances, no blocker)
1. **COMMON_KEYS**: `CONMIN_METRICS` reuses `n_mss`/`n_kb`/`acqmss_runtime_ms`/`acqmss_calls` (genuinely shared with ConGen — both build an MSS, call AcqMSS, emit a KB) but they are NOT in `COMMON_KEYS`. To give ConMin the SAME disjointness guard the other tables have, I add a declared `_MSS_SHARED` set into `COMMON_KEYS` (additive; the existing `CONGEN∩QUACQ` test is unaffected since QuAcq lacks those keys). This touches the shared allowlist in `metrics.py` but changes neither the ConGen/QuAcq tables nor their output. Brief said "don't touch ConGen/QuAcq metrics" — this is additive-shared-declaration, flagged.
2. **cross_validation.py** (eval/): "Cắm vào run_cv" needs a `n_fold_cross_validation_conmin` entry (mirror of the two existing functions, additive). Slightly beyond "runners+apps" but required + idiomatic; the generic `_run_cv_loop` already accepts any `BaseRunner`.

## Deliverables
1. **`conacq/runners/conmin_runner.py`** — `ConMinRunner(BaseRunner)` + `ConMinRunResult(BaseRunResult)`. Mirror ConGenRunner: build `ConMinModelBuilder` once; `run()` = `profiler.timer("conmin_total_time")` + tracemalloc → `prepare_task` → **ASSERT E⁻ present but `task.neg_encodings` empty → raise** (foot-gun #5, runner-side twin of the resolve guard) → `build_checker` → `ConMin(checker,profiler).acquire(set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc, set_neg_tv=task.set_neg_tv, negation_map=task.negation_map, neg_encodings=task.neg_encodings, support_count=task.support_count, k=self.k)` → `collect(profiler, CONMIN_METRICS, extra=...)` → `resolve_result(result, describe, root_clauses, task.set_kb, task.negation_map)`. `k` in `__init__` (default 1), mirror QuAcq's `max_queries`. `ConMinRunResult` fields: mirror ConGen (redundant_constraints, n_mss) + decomposition (fallback_clauses, mss_ids, cover_ids, kb_assumption_ids) + cover counters; `to_dict` emits them under a `conmin` block (non-breaking).
2. **`CONMIN_METRICS`** in metrics.py (additive table): `runtime_ms`→`conmin_total_time`; `_CORE[0]` consistency_checks; `_CORE[1]` memory; `n_mss`,`n_kb` (extra, group `kb_size`); `conmin_runtime_ms`→`conmin_runtime`; `acqmss_runtime_ms`,`acqmss_calls`; `_CORE[2..6]`; + cover counters `n_components`/`largest_component`/`n_greedy_fallback`/`n_uncoverable` (extra, group `conmin_cover`, stats `('mean',)`). `_MSS_SHARED`→`COMMON_KEYS`. Add `test_conmin_table_disjoint` + phantom-source check on live e2e profiler.
3. **`apps/run_conmin.py`** + **`apps/conf/run_conmin_config.toml`** — mirror run_congen; `save_kb_result(kb_constraints=kb_names, redundant_constraints, n_bias, n_mss, n_kb, bg_clauses, metadata={decomposition})`.
4. **CV wiring**: `n_fold_cross_validation_conmin` in cross_validation.py (build ConMinRunner → `_run_cv_loop`, label 'ConMin'); export from `conacq.eval`; `elif algorithm == 'conmin'` branch in `run_cv.py` (k from `eval_config`).

## Result JSON (decomposition for P4d)
Top-level compatible (kb_constraints/bg_clauses/statistics via save_kb_result); `metadata.conmin = {kb_clauses, fallback_clauses, slices:{mss_ids,cover_ids,kb_assumption_ids}, cover:{n_components,largest_component,n_greedy_fallback,n_uncoverable}}`. Does NOT alter run_compare/extract_results' consumed schema.

## Tests (`tests/test_conmin.py` runner section + metrics)
- **e2e** on REAL-FM-7 rs_1n: `ConMinRunner(bias,fm).run(pos,neg)` → KB non-empty, `{c6,c14,c18} ⊆ kb_constraints` (X→root), `bg_clauses==[[1]]`, decomposition present, `metrics` is CONMIN spec.
- **assert-test**: E⁻ present + monkeypatched empty `neg_encodings` → `run()` raises (foot-gun #5).
- **metrics**: CONMIN disjoint from CONGEN/QUACQ (⊆ COMMON_KEYS); no phantom source (CONMIN sources ⊆ live profiler ∪ extra).

## Acceptance / guardrails (P4c)
Runner e2e produces a real non-empty KB with X→root; assert fires on empty neg_encodings; CONMIN_METRICS additive + disjoint; `test_t9_metrics_safety_net` + `test_evaluation` green; boundary guard green; ConGen/QuAcq runner+metrics+tripwires UNTOUCHED; full suite no regress. HOLD after: user self-runs the runner e2e (KB non-empty + X→root + assert fires). DEFER: 4 comparison conditions / k-sweep / semantic P/R/F1 = P4d; §9c per-phase taxonomy = P4e.

## P4c — DONE + COMMITTED (`a71f856` feat + `2d236b8` fix(eval)), user-verified. P4d forward-notes:
Red-team (2 lenses) surfaced these, user-adjudicated — carry into P4d:
- **B1 (eval-semantics DECISION, user lean = INCLUDE):** CV held-out accuracy (`cross_validation.py:215`) scores `kb_clauses + bg_clauses` but OMITS `fallback_clauses` → when U>0 the scored theory ≠ the DELIVERED theory (learned ∪ ¬e⁻ ∪ root). Proved acc 0.0 vs 1.0. Latent now (rs_1n/ff U=∅). Decision: ¬e⁻ = negation of the minimal conflict (a GENERALIZING clause, not a full-config memorization) → including it is fair, and consistent with the P4b delivered theory. **Cowork paper chốt the exact rule + apply it CONSISTENTLY across all 4 comparison conditions** (some conditions may deliberately score learned-FM-only). When implementing: `AccuracyCalculator(list(kb_clauses)+list(bg_clauses)+list(getattr(run_result,'fallback_clauses',[])), …)` is shared code (ConGen has none → getattr [] → no change), OR a per-condition theory selector. Do NOT bake silently — it's a documented eval choice.
- **B2 (CV robustness, touches ConGen):** `_run_cv_loop` has no per-fold `try/except` → one fold raising (e.g. resolve's loud guard on an unforeseen shape) voids the whole model's CV, swallowed by `run_cv`'s `except`. P4d hardening: per-fold try/except that records a failed fold + continues (or surfaces partial).
- **B3 (CV contract, touches ConGen):** a training split with zero negatives (|E⁻| < n_folds) → ConMin KB = S-only (support-filtered, no cover/memorization) → skews `mean_accuracy`. Decide: require |E⁻| ≥ n_folds, or flag/exclude zero-neg folds.
- **B5/A6 (note/defer):** all runners call global `tracemalloc.stop()` (disables an outer profiler's tracing — pre-existing, shared); no ConMin metric-completeness guard (needs recorded U>0 data — add `CONMIN_IGNORED` + a completeness test when P4d/P4e produce ConMin CV JSON).
- **§9c per-phase check taxonomy = P4e** (AcqMSS dual-emit); k-sweep + baseline = P4d/P4f.

# P4d — Detailed HOW (2026-07-23): comparison conditions + run experiments

## Scout (reuse targets, brief §5)
`conacq/eval/kb_comparator.py` — `KBComparator(GroundTruthData, Bias).compare(result_data, strategy)` → P/R/F1 for DESCRIPTION/CLAUSE/SEMANTIC (result_data = names in `kb_constraints`). `accuracy.py` — held-out accuracy. `semantic_equivalence.py` — exact-equivalence (SAT). `run_compare.py` — loads unified CV JSON, compares each fold × strategy, `compute_summary` = CV mean/std P/R/F1. `GroundTruthData.from_uvl(fm)`. All 5 KBs have fm+bias+6 example-sets in `data/`.

## ⭐ DELTA-CHECK (brief §9 vs code/handoff)
1. **run_compare compares ONE kb/fold; P4d needs THREE slices/fold** (A=`mss_ids`, C=`cover_ids`, C∪S=`kb_assumption_ids`) each × 3 strategies. The slice IDs are emitted (P4c `metadata.conmin`) but NOT resolved to NAMES; KBComparator needs names. → extend the ConMin runner/CV to emit A-names + C-names per fold (additive; the describe provider is per-fold, lives in the runner).
2. **§9b per-phase cost vs §9c taxonomy (P4e):** P4d handoff §5 asks per-phase cost (Stage1/AcqMinCover/Reduce runtime + checks); the RIGOROUS per-call-site check taxonomy (dual-emit, ADR) is P4e. → P4d reports per-phase cost from EXISTING counters (acqmss_runtime, reduce_runtime, cover_rejection_checks, cover_quickxplain_checks, admpool checks); AcqMinCover total runtime if a timer exists, else note gap. Full §9c classification deferred to P4e (per brief line 200).
3. **B1 (apply, §6):** delivered theory = kb_clauses ∪ fallback_clauses ∪ bg(root) for accuracy + exact-equivalence; P/R/F1 range over FM/bias vocab (names, ¬e⁻/root excluded — already how KBComparator works on kb_constraints). U=∅ expected on these KBs.
4. **B2/B3 (§7, shared CV):** per-fold try/except + zero-neg-fold flag in `_run_cv_loop` — additive+guarded; ConGen/QuAcq tripwires must stay byte-identical (STOP+ask if not).

## Design — new `apps/run_conmin_eval.py` orchestration (reuse eval primitives)
Per (KB × example-set × k × raw|reduced): run ConMin 3-fold CV (fixed seed) → per fold resolve A/C/C∪S names + delivered theory → `KBComparator.compare` each slice × 3 strategies (P/R/F1) + `semantic_equivalence` exact-equiv + `accuracy` on delivered theory → CV mean±std → + QuAcq reference (existing `run_quacq`/interactive CV). Export JSON per (KB×ex×condition) + one consolidated CSV (rows = KB×ex×condition, cols = §9d metrics) feeding the 9 target tables. Seed + order-dependence threat-note in metadata (§8).

## Sub-phases
- **P4d.1 — machinery + B2/B3 hardening.** Extend `ConMinRunResult`/CV fold dict to emit `mss_names`/`cover_names` (resolve slices to FM names) + delivered-theory clauses. B2/B3 additive guards in `_run_cv_loop`. Tests: slice-name resolution + zero-neg-fold flag + per-fold-raise-continues + ConGen/QuAcq byte-identical.
- **P4d.2 — eval orchestration** `run_conmin_eval.py`: 3-slice × 3-strategy compare + exact-equiv + accuracy + size + per-phase cost; JSON + consolidated CSV.
- **P4d.3 — verify on REAL-FM-7** (small, fast): sanity numbers (|C|≈13, A/C/C∪S spectrum, QuAcq ref), all 9 table cells populate.
- **P4d.4 — full sweep** 5 KBs × 6 ex × 4 cond × k∈{1,2,3,5} × raw/reduced (busybox/REAL-FM-4 heavy → staged/background).
- **P4d.5 — export + run report** (`plans/reports/`): what ran, seed, wall-clock, fold failures, anomalies → report numbers to Cowork.

## Acceptance / guardrails (P4d)
No invented/tuned numbers; eval-policy = §9 (not mine). Full suite 552+1; boundary + ConGen/QuAcq tripwires green + their metrics byte-identical; don't edit `../explanation`; no RIPPER/CN2. STOP + report numbers to Cowork before paper.
