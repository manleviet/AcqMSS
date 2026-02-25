# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets) — Python system for constraint acquisition from feature models. Two packages: `acqmss/` (acquisition algorithms) + `explanation/` (SAT solver infrastructure).

**Key references** (read on-demand, not duplicated here):
- `README.md` — Quick start, code examples, project structure
- `docs/system-architecture.md` — Architecture, data flow, solver modes, performance
- `docs/codebase-summary.md` — Package structure, file inventory, dependencies
- `docs/code-standards.md` — Naming, patterns, testing conventions
- `docs/project-roadmap.md` — Development phases and status
- `docs/quacq.md` — QuAcq algorithm documentation (IJCAI 2013)
- `docs/congen.md` — ConGen algorithm documentation (MSS-based constraint acquisition)

## Role & Responsibilities

Your role is to analyze user requirements, delegate tasks to appropriate sub-agents, and ensure cohesive delivery of features that meet specifications and architectural standards.

## Workflows

- Primary workflow: `$HOME/.claude/rules/primary-workflow.md`
- Development rules: `$HOME/.claude/rules/development-rules.md`
- Orchestration protocols: `$HOME/.claude/rules/orchestration-protocol.md`
- Documentation management: `$HOME/.claude/rules/documentation-management.md`
- And other workflows: `$HOME/.claude/rules/*`

**IMPORTANT:** Analyze the skills catalog and activate the skills that are needed for the task during the process.
**IMPORTANT:** You must follow strictly the development rules in `$HOME/.claude/rules/development-rules.md` file.
**IMPORTANT:** Before you plan or proceed any implementation, always read the `./README.md` file first to get context.
**IMPORTANT:** Sacrifice grammar for the sake of concision when writing reports.
**IMPORTANT:** In reports, list any unresolved questions at the end, if any.

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

- **PYTHONPATH=.** required for all commands (no `pyproject.toml` with package install)
- **`neg_c_map` renamed to `negation_map`** across all modules (commit f15200b)
- **Feature ID source of truth**: flamapy's tree traversal order (NOT alphabetical) — see `docs/system-architecture.md` § "Feature ID Consistency"
- **GenerateNE**: Called internally by `ConGenModel.prepare()`, not by callers
- **CheckerModel protocol**: Both `ConGenModel` and `FMOracleModel` implement `get_kb()`, `get_assumptions()`, `use_incremental`
- **Test control**: `ENABLED_TESTS` and `ENABLED_PARAMS` dicts at top of test files toggle specific tests
- **Known pytest warnings**: `TestSuiteReader` triggers PytestCollectionWarning (has `__init__`); `pytest.mark.slow` is unregistered

## Hook Response Protocol

### Privacy Block Hook (`@@PRIVACY_PROMPT@@`)

When a tool call is blocked by the privacy-block hook, the output contains a JSON marker between `@@PRIVACY_PROMPT_START@@` and `@@PRIVACY_PROMPT_END@@`. **You MUST use the `AskUserQuestion` tool** to get proper user approval.

**Required Flow:**

1. Parse the JSON from the hook output
2. Use `AskUserQuestion` with the question data from the JSON
3. Based on user's selection:
    - **"Yes, approve access"** → Use `bash cat "filepath"` to read the file (bash is auto-approved)
    - **"No, skip this file"** → Continue without accessing the file

**Example AskUserQuestion call:**
```json
{
  "questions": [{
    "question": "I need to read \".env\" which may contain sensitive data. Do you approve?",
    "header": "File Access",
    "options": [
      { "label": "Yes, approve access", "description": "Allow reading .env this time" },
      { "label": "No, skip this file", "description": "Continue without accessing this file" }
    ],
    "multiSelect": false
  }]
}
```

**IMPORTANT:** Always ask the user via `AskUserQuestion` first. Never try to work around the privacy block without explicit user approval.

## Python Scripts (Skills)

When running Python scripts from `$HOME/.claude/skills/`, use the venv Python interpreter:
- **Linux/macOS:** `$HOME/.claude/skills/.venv/bin/python3 scripts/xxx.py`
- **Windows:** `.claude\skills\.venv\Scripts\python.exe scripts\xxx.py`

This ensures packages installed by `install.sh` (google-genai, pypdf, etc.) are available.

**IMPORTANT:** When scripts of skills failed, don't stop, try to fix them directly.

## [IMPORTANT] Consider Modularization
- If a code file exceeds the language threshold, consider modularizing it:
    - JS/TS/Python: ~200 lines
    - Java/Kotlin: ~300 lines (accounts for language verbosity)
- Check existing modules before creating new
- Analyze logical separation boundaries (functions, classes, concerns)
- Follow language conventions for file naming: kebab-case for JS/TS, snake_case for Python/Go/Rust, PascalCase for Java/C#/Kotlin (see `$HOME/.claude/rules/lang/*.md`)
- Write descriptive code comments
- After modularization, continue with main task
- When not to modularize: Markdown files, plain text files, bash scripts, configuration files, environment variables files, etc.

## Documentation Management

We keep all important docs in `./docs` folder and keep updating them:

```
./docs
├── README.md
├── code-standards.md
├── codebase-summary.md
├── project-overview-pdr.md
├── project-roadmap.md
├── congen.md
├── quacq.md
└── system-architecture.md
```

**IMPORTANT:** *MUST READ* and *MUST COMPLY* all *INSTRUCTIONS* in project `./CLAUDE.md`, especially *WORKFLOWS* section is *CRITICALLY IMPORTANT*, this rule is *MANDATORY. NON-NEGOTIABLE. NO EXCEPTIONS. MUST REMEMBER AT ALL TIMES!!!*
