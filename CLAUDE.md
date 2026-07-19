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
```

## Gotchas & Conventions

- **Test runner**: `PYTHONPATH=. pytest tests/ -v` (matches README), or `uv run --no-sync pytest tests/ -v` via the uv lockfile. Project is editable-installed (`pyproject.toml` + `uv.lock`); `PYTHONPATH=.` still set for direct invocation.
- **`neg_c_map` renamed to `negation_map`** across all modules (commit f15200b)
- **Feature ID source of truth**: flamapy's tree traversal order (NOT alphabetical) — see `docs/system-architecture.md` § "Feature ID Consistency"
- **GenerateNE**: Called internally by `ConGenModel.prepare_task()`, not by callers
- **Checker building**: Checker is built from a Task via `build_checker(task, backend=...)` (imported from `explanation.api`); models are pure KB containers with no checker protocol
- **Test control**: `ENABLED_TESTS` and `ENABLED_PARAMS` dicts at top of test files toggle specific tests
- **Known pytest warnings**: `TestSuiteReader` triggers PytestCollectionWarning (has `__init__`). The `slow` marker is registered in `pyproject.toml` `[tool.pytest.ini_options]`; shared fixtures/paths live in `tests/conftest.py` + `tests/resource_paths.py`.

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
