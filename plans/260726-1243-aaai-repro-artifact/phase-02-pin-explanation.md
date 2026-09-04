---
phase: 2
title: "Pin Explanation"
status: pending
effort: "~0.75h"
priority: P1
dependencies: []
---

# Phase 2: Pin the ../explanation dependency for external reproducers

## Overview
Neither `README.md`, `CLAUDE.md` nor `pyproject.toml` names an `explanation` version — only `pip install -e ../explanation`. An external reproducer cannot rebuild the environment, and `explanation` pins `flamapy==2.6.0.dev4` exactly (floating to 2.6.0 final breaks the suite). Record the **verified** pin in a form an external AAAI reviewer can actually install.

## Verified pin (do not guess — checked against the installed package, 2026-07-26)
- version: `0.1.0` (`pip show explanation`)
- tag `v0.1.0` **== HEAD** `9d63a6382856bc513b49773e9b647951ba68075e` (`git -C ../explanation rev-list -n1 v0.1.0` == `rev-parse HEAD`)
- remote: `https://github.com/manleviet/explanation.git`
- transitive pin: `flamapy-{fw,fm,sat}==2.6.0.dev4` (these ARE on PyPI, installable)

## CRITICAL constraint (Red Team #1): the explanation repo is PRIVATE
`gh api repos/manleviet/explanation` → `"private": true`; AcqMSS is public. So `pip install "git+https://…/explanation.git@…"` **fails for every external reviewer** (auth wall). Decision (interview): **ship a pinned wheel** as the primary reproducer install; git+SHA is a secondary path for maintainers with repo access.

## Deliverable — primary install = vendored wheel
- Build `explanation-0.1.0-py3-none-any.whl` from the **clean** `v0.1.0` checkout (SHA `9d63a63…`): in a clean clone/worktree of `../explanation` at the tag, `python -m build` → `dist/explanation-0.1.0-py3-none-any.whl` (+ sdist). Record `sha256` for integrity.
- Commit it to AcqMSS under `vendor/explanation-0.1.0-py3-none-any.whl` (+ `vendor/README.md` noting provenance: built from `manleviet/explanation@v0.1.0` / SHA `9d63a63…`, sha256=…).
- **Primary reproducer install** (works offline, no private-repo access):
  `pip install vendor/explanation-0.1.0-py3-none-any.whl`
  (flamapy `2.6.0.dev4` deps resolve from PyPI; if dev releases need it, document `--pre`.)
- **Secondary / maintainer path** (has repo access): pin the **immutable SHA**, not the movable tag (Red Team #9):
  `pip install "git+https://github.com/manleviet/explanation.git@9d63a6382856bc513b49773e9b647951ba68075e"`

## Requirements
- Functional: a fresh venv with **no access to the private repo** can install the pinned `explanation` from the committed wheel and import it (version 0.1.0).
- Constraint: **do NOT add `explanation` to `pyproject.toml` dependencies.** Correct rationale (Red Team #14): it's not that a dep "breaks the suite/editable dev" — it's that the canonical package **is not on PyPI** and the repo follows a deliberate **two-repo editable convention** (CLAUDE.md). Keep the flamapy-`2.6.0.dev4` caveat as a SEPARATE note. A reproducer-pin **comment** near pyproject lines 25–26 is fine (non-breaking).

## Related Code Files
- Create: `vendor/explanation-0.1.0-py3-none-any.whl` + `vendor/README.md` (provenance + sha256)
- Modify: `README.md` (install block ~lines 13–14; note at ~line 144) — add "Reproducing the paper environment: `pip install vendor/explanation-0.1.0-py3-none-any.whl`"; keep `pip install -e ../explanation` as the DEV path.
- Modify: `docs/eval-pipeline.md` ("Environment" prerequisite added in Phase 1) — same wheel install + SHA provenance + flamapy caveat.
- Modify (comment only): `pyproject.toml` (~lines 25–26) — `# reproducer pin: explanation 0.1.0 == git SHA 9d63a63 (flamapy 2.6.0.dev4); install from vendor/explanation-0.1.0-*.whl — NOT a dependency (canonical not on PyPI; two-repo editable convention)`.

## Implementation Steps
1. Build the wheel from the clean `v0.1.0` checkout; capture sha256; commit under `vendor/` with `vendor/README.md` provenance.
2. `README.md`: keep dev editable line; ADD the wheel-based "Reproducing the paper environment" note; add SHA + flamapy caveat + secondary git+SHA path (repo-access only).
3. `docs/eval-pipeline.md`: add the Environment prerequisite (wheel install) — single source of truth, cross-link README.
4. `pyproject.toml`: append the reproducer-pin comment (no dependency-list change; corrected rationale).
5. State the flamapy caveat: `explanation`'s exact `2.6.0.dev4` pin is load-bearing — floating to `2.6.0` final breaks the suite.

## Success Criteria
- [ ] `vendor/explanation-0.1.0-py3-none-any.whl` committed with recorded sha256 + provenance (built from `@v0.1.0`/`9d63a63…`).
- [ ] Fresh-venv install from the wheel succeeds **without** private-repo access; `python -c "import explanation, importlib.metadata as m; print(m.version('explanation'))"` → `0.1.0`.
- [ ] README + eval-pipeline doc carry the wheel install + SHA + flamapy-`2.6.0.dev4` caveat; secondary git+SHA path noted as repo-access-only.
- [ ] `pyproject.toml` dependency list UNCHANGED (comment-only, corrected rationale).

## Risk Assessment
- Risk: wheel built from a dirty `../explanation` tree (it currently has `M .gitignore` + untracked plans/). Mitigation: build from a CLEAN checkout of the tag (fresh clone or `git worktree add … v0.1.0`), so the wheel == `9d63a63…` content exactly.
- Risk: someone converts the comment into a real dependency and breaks editable dev / CI (not on PyPI). Mitigation: explicit comment wording "NOT a dependency".
- Risk: flamapy `2.6.0.dev4` dev-releases need `--pre` on some resolvers. Mitigation: document the `--pre` fallback in the README install note.
