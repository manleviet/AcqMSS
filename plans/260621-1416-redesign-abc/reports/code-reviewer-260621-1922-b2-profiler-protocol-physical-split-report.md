# Code Review — B2 Profiler Protocol + Physical Split

Date: 2026-06-21
Reviewer: code-reviewer (independent; implementing agent died mid-run — this is the primary check)
Scope: working-tree changes on `feat/redesign-abc`
Spec: `plans/260621-1416-redesign-abc/phase-08-b2-profiler-protocol-physical-split.md`

## Verdict: PASS

- (1) Nothing lost in the split: **VERIFIED — nothing lost.**
- (3) Pickling/parallel path intact: **VERIFIED — intact (and never depended on profiler picklability).**
- Full suite: **437 passed** (`uv run --no-sync pytest tests/ -q`, 52.9s). The known-flaky `test_consistency_check_count_parity` passed this run; pre-existing parallel race, not a B2 defect.

---

## Scope
- Deleted: `explanation/operations/algorithms/profiler.py` (1151 LOC).
- Added package `explanation/operations/algorithms/profiler/`: `protocol.py` (224), `core.py` (401), `decorators.py` (120), `presets.py` (66), `registry.py` (107), `__init__.py` (62).
- Modified: `tests/test_profiler.py` (hardcoded `/tmp/profiler_test.csv` → `tmp_path` fixture).
- `conacq/oracle/fm_oracle.py` shows in `git status` but `git diff` is EMPTY — not a B2 change, ignore.

---

## (1) Nothing-Lost Verification — VERIFIED

AST-level comparison of HEAD `profiler.py` vs union of the 5 submodules (docstrings stripped, logic compared):
- **49 members in original, 49 in package. Zero missing.**
- Zero genuine duplicates (the apparent dupes — `increment`/`record_time`/`timer`/`is_profiling` — are the Protocol stubs in `protocol.py` vs the concrete impl in `core.py`; legitimately same-named on different classes).
- **Only 3 bodies differ, all benign deferred-imports** introduced solely to break import cycles, behavior identical:
  - `measure_time`, `count_calls` (`decorators.py:54,105`): `get_global_profiler` moved to a function-local import on the fallback branch.
  - `create_profiler` (`presets.py:62`): `Profiler` moved to a function-local import.
- Concrete `Profiler` metric/CSV/console/timer/stats logic in `core.py` is byte-identical to original (verified incl. `_lock = Lock()` at `core.py:54` == orig:522, `write_to_csv` dir-creation + `;` delimiter, `print_summary` emoji headers, `get_stats` median/stddev guard).
- `gprofiler` module global + `use_global_profiler(DISABLED)` bootstrap preserved at `registry.py:106` (== orig:1152).

## (2) Import Surface — VERIFIED
- All 14 `__all__` symbols resolve at runtime; `__all__` exactly matches the expected set.
- The 7-symbol "actually used" set (AbstractProfiler, ProfilerPreset, count_calls, get_global_profiler, measure_time, profiler_session, use_global_profiler) all import.
- **34 import sites** confirmed (matches `__init__.py` docstring + spec). None re-pointed — unnecessary: the new package path `explanation.operations.algorithms.profiler` is identical to the old module path, so every existing import (absolute + relative `.profiler`/`..profiler`) keeps working with zero churn. Smart, low-risk.
- No circular imports: `protocol` (leaf) ← `core`, `presets`; `presets` ← `registry`; `decorators` (leaf, lazy→registry); `__init__` aggregates. Package imports cleanly.

## (3) Pickling / Parallel Path — VERIFIED INTACT
- **The profiler is never pickled across the process boundary.** `ProcessExecutor.__init__` (`executor.py:139-143`) passes only `(set_kb, assumptions, solver_name, use_incremental)` — all picklable primitives — via `initargs`. Each worker builds its OWN profiler locally in `_init_worker` (`executor.py:69` `create_profiler(BENCHMARK)`). Workers return a picklable `float` `dt`; the MAIN process records it on `self.profiler` (option-B pattern).
- Concrete `Profiler` is NOT picklable (contains `threading.Lock`) — **but this is unchanged from the original** (`Lock()` present in both, identical line). No code path requires it. The split introduced no new module-level lock/global into any pickled path.
- All 8 `tests/test_executor.py` tests pass (incl. the parallel `solver_time` round-trip + count-parity checks).

## (4) Protocol Quality — Sound
- `Profiler` Protocol (`protocol.py:34`, `@runtime_checkable`) declares `increment`, `record_time`, `timer`, `is_profiling` — matches what consumers actually call on the hot path. Verified structurally compatible: `isinstance(Profiler(), Proto)` and `isinstance(NullProfiler(), Proto)` both True at runtime.
- Public-name decision is **sound for back-compat**: public `Profiler` stays the concrete class (consumers like `test_profiler.py` import `Profiler` expecting the concrete impl); the Protocol is aliased `_ProfilerProtocol`. The `_`-prefix on a public-API alias is mildly unusual but acceptable as a transitional name — spec explicitly defers consumer re-pointing to B1 ("keep `__init__` re-exports stable until B1 redirects them to the surface"). No consumer uses the Protocol type yet; that is on-plan, not a gap.

## (5) Split Quality — Good, with one advisory
- Submodules are cohesive: protocol/ABC/null, concrete+reporting, decorators, presets, registry. Sensible concern boundaries.
- **Deviation from spec's named submodules, both defensible:**
  - Spec named `reporting.py` + `multiprocessing.py`; impl folded reporting into `core.py` and omitted `multiprocessing.py`. The omission is correct — there is **zero mp code** in the original (only `mp.Pool` inside docstring examples), so a `multiprocessing.py` would be empty. YAGNI-correct.
  - `core.py` is 401 LOC — over the ~200 Python guideline. The concrete class + its reporting (`print_summary`/`to_csv_row`/`write_to_csv`, ~135 LOC) could split into a `reporting.py` mixin per the spec's original intent. **Advisory only** — single cohesive class, no functional issue.

## (6) Other Checks
- No weakened test assertions (only the `/tmp` → `tmp_path` isolation fix; `tmp_path` auto-cleans, so the removed manual cleanup is fine).
- Framework-only changes (all under `explanation/` + its tests). No app/algorithm logic touched.
- No plan-stage labels (phase/B2/F#/audit/§) in any new comment or docstring. Clean.
- `__pycache__` untracked and gitignored.

---

## Findings by Severity

### Critical / High
None.

### Medium
None.

### Low (advisory / non-blocking)
1. **`core.py` 401 LOC > 200 guideline.** `presets.py:62` / `decorators.py:54,105` already break cycles, so extracting the ~135-LOC reporting block (`print_summary`/`to_csv_row`/`write_to_csv`) into `reporting.py` per the spec's original architecture would land core under threshold. Defer or do as cleanup — no behavior impact.
2. **Stale docs (separate from code; build unaffected).** `docs/codebase-summary.md:225,300,570`, `docs/system-architecture.md:787`, `docs/project-roadmap.md:259` still describe `profiler.py` as a single 800/1192-LOC module. `pyproject.toml` has no path ref, so packaging is fine. Flag for docs-manager (likely a later-stage docs-sync task).
3. **`_ProfilerProtocol` public alias naming.** A `_`-prefixed name in `__all__` is unusual. Acceptable as transitional (B1 will redirect consumers to the surface), but B1 should rename it to a clean public name (e.g. `ProfilerProtocol`) or settle the `Profiler`-name story then.

---

## Spec Success Criteria
- [x] `Profiler` Protocol exists (consumer re-pointing deferred to B1 per plan).
- [x] Split into ≥4 submodules (5); no 1150-LOC file.
- [x] 34 import sites resolve (re-point unnecessary — path-identical package).
- [x] `test_profiler` uses `tmp_path`; covers core/reporting(CSV)/registry.
- [x] Full suite green (437 ≥ 351).
- [x] Red-team: every old symbol re-exported (verified); `AbstractProfiler` kept re-exported for `fm_oracle.py:18`; `test_diagnosis.py:34` imports (`ProfilerPreset`, `profiler_session`) resolve.

---

## Unresolved Questions
1. Is the Low-#1 reporting extraction wanted now, or rolled into a later cleanup stage? (Advisory; B2 passes either way.)
2. Docs sync (Low-#2): in-scope for B2, or owned by a docs-sync task later in the A+B+C plan?
3. B1 should confirm the intended final public name for the Protocol (currently `_ProfilerProtocol`).
