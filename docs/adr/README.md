# Architecture Decision Records

Each ADR captures **one architectural decision and the reasoning behind it** — including the options that were rejected and why.

## Why these exist

The tests tell you *what* the architecture is. `tests/test_boundary_guard.py` will fail if `explanation` imports `conacq`; it will not tell you why that rule exists, what it protects, or what breaks if you "just add one import". A guard can enforce a boundary; only an ADR can explain it.

These decisions were made during the **ABC-v2 redesign** (July 2026), a rebuild of the `conacq` / `explanation` / `profiling` architecture from `main` with behaviour held identical. The construction plan for that redesign was a temporary working document and no longer exists. The reasoning does — here.

**When you are about to "tidy up" something in this codebase that looks misplaced, read the relevant ADR first.** Several of these decisions look wrong until you know what they are protecting.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-redesign-from-baseline.md) | Rebuild from `main` rather than re-apply the old branch | Accepted |
| [0002](0002-three-package-layering.md) | Three-package layering, enforced by an AST guard | Accepted |
| [0003](0003-profiling-as-top-level-package.md) | `profiling` is a top-level package, not part of `explanation` | Accepted |
| [0004](0004-checker-is-the-port-backend-is-the-adapter.md) | `checker` = port (algorithm-facing), `solver_backend` = adapter (solver-facing) | Accepted |
| [0005](0005-oracle-bias-builder-lives-in-conacq.md) | `OracleBiasModelBuilder` lives in `conacq`, not `explanation` | Accepted |
| [0006](0006-evaluation-stays-inside-conacq.md) | `evaluation` stays inside `conacq` — it is *not* the next `profiling` | Accepted |
| [0007](0007-no-runtime-read-only-views.md) | The name↔id catalog is a plain `dict` — no runtime read-only view | Accepted |
| [0008](0008-run-result-and-result-data-stay-separate.md) | `ConGenRunResult` and `ConGenResultData` stay separate — write-product ≠ read-projection | Accepted |
| [0009](0009-the-oracle-answers-it-does-not-provision.md) | The oracle answers questions; it does not provision the algorithm | Accepted |

## Writing a new one

Copy the shape of an existing ADR: Context → Decision → Options considered → Trade-offs → Consequences. Write it **when the decision is made**, not at the end of the project — by then the alternatives you rejected have faded, and those are the most valuable part of the record.

Number sequentially. Never edit a decision after it is accepted: supersede it with a new ADR and mark the old one `Superseded by ADR-XXXX`.
