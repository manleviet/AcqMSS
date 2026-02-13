# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets) is a Python-based system for constraint acquisition from feature models. It implements:
- **Diagnosis algorithms**: FastDiag, QuickXPlain, KBDiag, WipeOutR with HSDAG tree search
- **CONGEN**: Passive/batch constraint acquisition using ACQMSS, REDUCE, and GenerateNE
- **QuAcq**: Interactive constraint acquisition via membership queries
- **Evaluation framework**: Cross-validation, accuracy metrics, performance benchmarking

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

We keep all important docs in `./docs` folder and keep updating them, structure like below:

```
./docs
├── project-overview-pdr.md
├── code-standards.md
├── codebase-summary.md
├── design-guidelines.md
├── deployment-guide.md
├── system-architecture.md
└── project-roadmap.md
```

**IMPORTANT:** *MUST READ* and *MUST COMPLY* all *INSTRUCTIONS* in project `./CLAUDE.md`, especially *WORKFLOWS* section is *CRITICALLY IMPORTANT*, this rule is *MANDATORY. NON-NEGOTIABLE. NO EXCEPTIONS. MUST REMEMBER AT ALL TIMES!!!*

## Main Applications

```bash
# Generate bias files from feature model
PYTHONPATH=. python apps/generate_bias_config.py data/fms/model.uvl -v
PYTHONPATH=. python apps/generate_bias_files.py data/bias-config/model.yaml

# Generate test examples
PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml

# Run CONGEN (passive learning)
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml --non-incremental

# Run QuAcq (interactive learning)
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml --interactive

# Evaluate results
PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml -v
```

## Architecture

### Two Learning Paradigms

**CONGEN (Passive/Batch Learning)**:
```
CONGEN(E+, E-, B, BG) → KB
1: NE ← GENERATENE(E⁻)      # Create negated examples
2: B′ ← ACQMSS(∅, B, NE, E⁺, BG)  # Find MSS of bias
3: return REDUCE(B′, NE, BG)  # Remove redundant constraints
```

**QuAcq (Interactive Learning)**:
```
QuAcq(B, BG, Oracle) → KB
while B is not empty:
  1. q ← GenerateQuery(KB, B, BG)
  2. answer ← Oracle.is_valid(q)
  3. if answer: prune constraints rejecting q
     else: find conflict, add to KB
return REDUCE(KB, BG)
```

### Solver Modes

- **Incremental**: Persistent solver with assumptions (default, efficient for repeated SAT checks)
- **Non-incremental**: Fresh solver instance per check
- **SAT4J**: External Java solver via subprocess

### Evaluation Metrics (from Paper Formula 1)

- **Accuracy** = (TP + TN) / (TP + TN + FP + FN) — primary metric
- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **F1** = 2 * P * R / (P + R)

Evaluation strategies: `description` (compare constraint descriptions) or `clause` (compare CNF clauses)

## Test Configuration

Tests use `@parameterized.expand` with combinations of incremental/non-incremental modes and with/without profiling. Toggle specific tests via `ENABLED_TESTS` and `ENABLED_PARAMS` dictionaries at the top of test files.

## Key API Patterns

**CONGEN usage**:
```python
from acqmss.algorithms import CONGEN, CONGENModel, CONGENTaskPreparation
from explanation.operations.algorithms.checker import IncrementalPySATChecker

model = CONGENModel.from_bias_and_examples(bias_constraints, pos_examples, neg_examples, feature_ids)
preparation = CONGENTaskPreparation()  # mode_name defaults to "congen"
task = preparation.prepare(model).task
checker = IncrementalPySATChecker(task.set_kb, task.assumptions, 'glucose4', profiler)
congen = CONGEN(checker, profiler)
result = congen.acquire(task)
```

**QuAcq usage**:
```python
from acqmss.algorithms.interactive import InteractiveLearner

learner = InteractiveLearner.from_files(fm_path='model.uvl', bias_path='bias.json')
result = learner.learn(mode='automated', max_queries=1000)
evaluation = learner.evaluate(result)
```

**Diagnosis operations**:
```python
from explanation.operations import PySATDiagnosisBuilder, PySATTestcaseBuilder

# FastDiag
operation = PySATDiagnosisBuilder.for_diagnosis().with_max_diagnoses(5).build()

# QuickXPlain
operation = PySATDiagnosisBuilder.for_conflict().with_max_conflicts(3).build()

# KBDiag
operation = PySATTestcaseBuilder.for_debugging().with_max_diagnoses(1).build()
```