# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Generic rules — Role & Responsibilities, Workflows, Hook Response Protocol, Python-Scripts venv, and Modularization — live in `~/.claude/CLAUDE.md` (auto-loaded for every project) and are intentionally **not** duplicated here. This file holds only AcqMSS-specific context.

## Project Overview

AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets) — Python system for constraint acquisition from feature models. In-repo source packages: `conacq/` (acquisition algorithms) + `apps/` (CLI applications). SAT solver infrastructure (`explanation/` + `profiling/`) is consumed from the canonical `../explanation` package (installed editable). Note: `acqmss` is the distribution name in `pyproject.toml`, not a directory.

### External Dependencies

**Canonical `../explanation` package**: AcqMSS requires the flamapy-plugin `explanation/` package (SAT solver infrastructure + profiling) checked out beside the repo and installed editable:
```bash
# From AcqMSS root:
pip install -e ../explanation
```
It is intentionally **NOT** pinned in `pyproject.toml` (canonical is not on PyPI yet) — a local two-repo dev convention. See `../explanation/README.md` for setup details.

**Key references** (read on-demand, not duplicated here):
- `README.md` — Quick start, code examples, project structure
- `docs/system-architecture.md` — Architecture, data flow, solver modes, performance
- `docs/codebase-summary.md` — Package structure, file inventory, dependencies
- `docs/code-standards.md` — Naming, patterns, testing conventions
- `docs/project-roadmap.md` — Development phases and status
- `docs/quacq.md` — QuAcq algorithm documentation (IJCAI 2013)
- `docs/congen.md` — ConGen algorithm documentation (MSS-based constraint acquisition)
- `docs/eval-pipeline.md` — Evaluation/benchmark pipeline

## Quick Commands

```bash
# Tests (PYTHONPATH=. required)
PYTHONPATH=. pytest tests/ -v                        # All tests
PYTHONPATH=. pytest tests/test_congen.py -v          # Specific file
PYTHONPATH=. pytest tests/ -k "test_name" -v         # Pattern match

# Key apps pattern: python -m apps.<module> <toml-config> -v
# See README.md for full workflow commands

# Paper tables — one gated command, end to end (see data/results_conmin/RUN.md TL;DR)
./reproduce_tables.sh            # from the committed CSVs (~1 min)
./reproduce_tables.sh --full     # re-run the whole sweep first (~12+ h)
```

> **Table pipeline**: `apps/make_tables/` is the current generator (11 `.tex`/`.md` +
> `exact-equiv.md` + `PROVENANCE.md` → `data/results_conmin/tables/`). ⚠️
> `docs/eval-pipeline.md` still documents an **older** path (`extract_results.py` →
> `paper/tables/`) that did **not** produce the AAAI tables — that doc needs updating.

## Gotchas & Conventions

- **Test runner**: `PYTHONPATH=. pytest tests/ -v` (matches README), or `uv run --no-sync pytest tests/ -v` via the uv lockfile. Project is editable-installed (`pyproject.toml` + `uv.lock`); `PYTHONPATH=.` still set for direct invocation.
- **`neg_c_map` renamed to `negation_map`** across all modules (commit f15200b)
- **Feature ID source of truth**: flamapy's tree traversal order (NOT alphabetical) — see `docs/system-architecture.md` § "Feature ID Consistency"
- **GenerateNE**: Called internally by `ConGenModel.prepare_task()`, not by callers
- **Checker building**: Checker is built from a Task via `build_checker(task, backend=...)` (imported from `explanation.api`); models are pure KB containers with no checker protocol
- **Test control**: `ENABLED_TESTS` and `ENABLED_PARAMS` dicts at top of test files toggle specific tests
- **Known pytest warnings**: `TestSuiteReader` triggers PytestCollectionWarning (has `__init__`). The `slow` marker is registered in `pyproject.toml` `[tool.pytest.ini_options]`; shared fixtures/paths live in `tests/conftest.py` + `tests/resource_paths.py`.
- **Suite baseline — `610 passed, 1 skipped`** (611 collected), measured at commit
  `0540010` on 2026-08-22. `../explanation` is `275 passed, 0 skipped`.

  **Record the commit and the environment whenever you move this number.** The
  previous baseline (`507 passed + 1 skipped`) died precisely because neither was
  written down: it was measured at `4b47c9b` on 2026-07-19, before `make_tables`
  entered the repo at `2536385` (2026-07-26), so by August it described a tree
  that no longer existed and could not tell an environment failure apart from a
  real one. Both conditions matter:

  1. canonical `../explanation` installed editable (`pip install -e ../explanation`)
  2. `flamapy-fm` / `-fw` / `-sat` at `2.6.0.dev4` — the versions `pyproject.toml`
     pins. `pip check` stays red on `flamapy-bdd 2.0.1`; that is the normal
     working state, not a problem.

  A total is the wrong gate anyway. Before changing anything, measure the set of
  **red test names** under the environment you will use, then require the set
  after your change to be exactly the tests your change should touch. Any other
  red test means stop.
- **The one skipped test**: `test_extraction_tables_are_byte_identical`
  (`tests/test_t9_metrics_safety_net.py:37`). Owned by **C2**, not by whoever
  trips over it — it compares stale against stale, so enabling it now proves
  nothing. It is released when C2 regenerates `data/results/congen` and
  re-baselines the t9 golden (B3 REDUCE regen; see ADR-0017).

## Effort plans (`plans/`) — what gets committed

`plans/<timestamped-effort>/` is the implementation layer: one folder per effort,
holding its plan, phase specs, progress log and any measurement reports. Most of
it is scratch and stays local. Two kinds are **not** scratch, and both must be
committed on the working branch:

1. **Anything another machine has to read.** The moment an effort crosses
   machines — a second Claude Code, a laptop running an overnight sweep — the
   branch is the only channel. A spec left uncommitted means the other side is
   working from a chat summary instead of the document, which defeats the point
   of writing it down.
2. **Anything a plan or hub cites as evidence.** If `Cowork/AcqMSS/plan.md` or a
   paper hub points at `plans/reports/<x>.md` as the provenance for a decision,
   that file is part of the record and belongs in history. A citation to a path
   that exists on one laptop is not a citation.

Rule of thumb: *scratch is local, evidence is committed.* When unsure, commit —
`plans/` is text and the whole tree is a few megabytes.

Commit effort logs **separately from data or code**, so the record survives
regardless of how the run turns out.

Adopted 2026-08-21, after both failure modes hit on the same day: the SoSyM hub
cited two `plans/reports/measurement-*.md` files that existed on exactly one
machine, and a Claude Code on a second machine wrote a C11 spec the first machine
could not read. Before that, 13 of 439 files under `plans/` were tracked, with no
rule behind which 13.

## Documentation Management

Project docs live in `./docs` (keep updated). Tree differs from the generic global list:

```
./docs
├── README.md
├── code-standards.md
├── codebase-summary.md
├── project-overview-pdr.md
├── project-roadmap.md
├── congen.md
├── quacq.md
├── eval-pipeline.md
└── system-architecture.md
```
