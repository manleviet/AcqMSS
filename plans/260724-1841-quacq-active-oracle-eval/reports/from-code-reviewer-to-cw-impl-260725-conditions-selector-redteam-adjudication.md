# Code Red-Team Adjudication — `--conditions` selector (444a805) + hardening (f21a1e5)

2 hostile reviewers (surgical-merge correctness; guardrail/regression/Stage-1-skip) + controller
checks. Read-only review; **all accepted findings FIXED** in `f21a1e5`; `pytest -q` green (589p/1s).

## Verdict
The core feature is sound (both reviewers refuted the guardrail attacks with evidence), but the
new config/merge surface had **1 Critical + 2 High silent-data-loss paths** — all fixed.

## Refuted (verified SAFE — the feature does what it claims)
- **Full-run byte-identity:** A/B vs parent (cb28412) — 0 deterministic-content mismatches, identical
  keys/order/provenance; only wall-clock/memory fields differ (nondeterministic pre-commit too).
- **Stage-1 genuinely skipped:** `acquire_pool_and_cover` **6→0 calls** under `--conditions quacq`;
  measured **2.76× (arcade-game) / 2.26× (REAL-FM-7) / 1.90× (fqa)** speedup; the still-built ConMin
  model is <10 ms (immaterial).
- Per-KB CSV complete (multiset-matches merged JSON); `--merge` clean; QuAcq-active learn-skip works;
  alias parsing robust; preserved A/C/C∪S rows byte-identical at the serialization level.

## Findings (all Accept → Fixed in f21a1e5)

| # | Finding | Sev | Fix |
|---|---------|-----|-----|
| C1 | Merge replaces by `condition` only, not `(condition,k,negatives)` → narrower `--k`/`--negatives` or config drift silently DROPS rows + corrupts `aggregated` | **Crit** | Coverage guard: refuse if the recompute would drop any existing `(condition,k,neg)` key of a selected condition |
| H1 | `--conditions quacq-active` while QuAcq-active disabled → deletes existing active rows + nulls provenance | **High** | Same coverage guard (0 recomputed rows vs existing keys → refuse); verified JSON untouched |
| H2 | `quacq_query_mode` unvalidated → `automated` mislabels oracle output as passive QuAcq; `interactive` hangs on stdin | **High** | Validate ∈ {example_only, example_first} at the boundary → error |
| M1 | Empty/degenerate `--conditions` (`,`/``) → silent no-op + misleading `conditions=ALL` log | Med | Error on empty parse; banner uses `is not None` |
| M2 | In-loop existence guard rewrites earlier es before a later missing es aborts → partial sweep + stale per-KB CSV | Med | Pre-flight: check every target JSON exists before any write |
| M3 | No code-version/semantics stamp → recomputing a condition onto a pre-fix JSON mixes semantics (latent) | Med | Documented in RUN.md (recompute only onto same-version JSON); no versioning infra added (YAGNI) |
| L1 | "byte-identical" is row-verbatim (confirmed) but not whole-file (QuAcq rows reorder to tail) | Low | Comment wording softened to "row content unchanged; rows may be reordered" |

### The coverage guard (closes C1 + H1 with one check)
Before merging, `dropped = {(cond,k,neg) of existing rows for selected conditions} − {(cond,k,neg) of
recomputed rows}`. If `dropped` is non-empty → the recompute doesn't cover what it would replace →
`sys.exit` (no write). Adding a new condition (recompute ⊇ existing) is still allowed. Verified:
`--conditions cus --k 1` → refuses (drops C∪S k=2,3,5); `--conditions quacq-active --no-quacq-active`
on a JSON with active rows → refuses, JSON + provenance untouched; normal `--conditions quacq` → OK.

## Tests added (f21a1e5)
coverage-guard rejects narrowed k · quacq-active-selected-but-disabled preserves rows · invalid
`quacq_query_mode` rejected · empty `--conditions` rejected. (Existing happy-path + pre-flight tests kept.)

## Unresolved questions
1. Should `--conditions` ever be combined with `--k`/`--negatives`? Current stance: allowed only if it
   doesn't drop existing coverage (guard), else refuse. If never intended, forbidding the combo outright
   is simpler — CW call.
2. M3: is a `code_rev` stamp in the payload + a `--merge` version-skew warning worth adding, or is the
   RUN.md caveat ("recompute onto a same-version JSON") sufficient for the workflow?
