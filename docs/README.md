# AcqMSS Documentation

**Last Updated**: 2026-02-18

Welcome to the comprehensive documentation for AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets). This directory contains technical documentation for developers, researchers, and contributors.

## Quick Navigation

### Starting Points

**New to AcqMSS?**
1. Read the main [README.md](../README.md) in project root for quick start
2. Read [project-overview-pdr.md](#project-overview--pdr) to understand the vision

**Already familiar, need details?**
- [codebase-summary.md](#codebase-summary) — Package structure and organization
- [system-architecture.md](#system-architecture) — How components interact
- [code-standards.md](#code-standards) — Development standards and patterns

**Planning development?**
- [project-roadmap.md](#project-roadmap) — Phases, timeline, and future work
- [code-standards.md](#code-standards) — Code review checklist

## Documentation Files

### project-overview-pdr.md
**Purpose**: Product definition and requirements
**Length**: 353 LOC

Defines what AcqMSS is, why it exists, and what success looks like:
- Executive summary
- Problem statement and motivation
- 7 core functional requirements (CONGEN, QuAcq, diagnosis, evaluation, etc.)
- 6 non-functional requirements (performance, accuracy, quality, compatibility)
- Success criteria and key metrics
- Development phases overview
- Phase 5 (QuAcq Enhancement) completion with FindScope/FindC

**Read when**: You need to understand the "why" and "what" of the project.

### codebase-summary.md
**Purpose**: Code organization and inventory
**Length**: 439 LOC

High-level overview of what code exists where:
- Package structure (conacq, explanation, apps, tests)
- Detailed LOC breakdown per component
- **conacq/oracle/**: Oracle ABC, FeatureModelOracle, FMData (9 files, ~929 LOC)
- **conacq/runners/**: ConGenRunner, QuAcqRunner (3 files, ~446 LOC, moved from eval/)
- File inventory by purpose
- Data directory structure (feature models, configurations, results)
- Dependencies (runtime, development, optional)
- Key architectural patterns
- Codebase statistics (~19,532 LOC across ~97 files)

**Read when**: You need to find where something is implemented, or understand the code organization.

### code-standards.md
**Purpose**: Development guidelines and conventions
**Length**: 694 LOC (trimmed to <800 LOC limit)

Comprehensive style guide and best practices:
- Language requirements (Python 3.13+, type hints)
- Module file size guidelines (~200 lines Python, max ~300)
- Naming conventions (modules, classes, functions, variables)
- File organization and import order
- 7 design patterns (Builder, Strategy, Template, DI, Facade, Shared Utils, Interactive)
- Oracle module conventions (Oracle ABC, FMData, FeatureModelOracle)
- Testing strategy (parameterization, coverage requirements)
- Documentation standards (docstring formats)
- Type hints and error handling
- Configuration management (TOML-driven)
- Performance and security considerations
- Code review checklist (12 items)

**Read when**: You're writing code or reviewing others' code. Use the checklist before submitting PRs.

### system-architecture.md
**Purpose**: Technical architecture and data flows
**Length**: 595 LOC

Deep dive into how the system works:
- Two-layer architecture overview
- **NEW**: acqmss/oracle/ package architecture and feature ID consistency (CRITICAL)
- **NEW**: Unified checker interface (assumption-based data representation)
- Detailed package organization with API examples
- Data flow diagrams (CONGEN learning flow, QuAcq interactive flow)
- Solver architecture (incremental, non-incremental, SAT4J modes)
- **UPDATED**: GenerateNE caller-invoked design with merge_ne_into_task()
- Integration points between packages
- Performance characteristics (algorithm complexity, optimization)
- Testing architecture
- Design decisions and trade-offs

**Read when**: You need to understand how components interact, or you're making architectural changes.

### project-roadmap.md
**Purpose**: Development timeline and progress
**Length**: 347 LOC

Project status and future planning:
- **Updated**: 5 development phases (Phases 1-5 complete, Phase 6 in progress)
- **NEW**: Phase 5 (QuAcq Enhancement) completion details
- Current metrics (code quality, performance benchmarks)
- Completed milestones and deliverables
- Future enhancements (short/medium/long-term)
- Known limitations and workarounds
- Quality assurance status
- Release strategy (v1.0, v1.1, v2.0)
- Health indicators and success criteria

**Read when**: You need to understand project status, or you're planning future work.

### quacq.md
**Purpose**: QuAcq algorithm documentation (IJCAI 2013)
**Length**: 193 LOC

Paper-based implementation guide:
- Overview of QuAcq algorithm (partial queries for active learning)
- **UPDATED**: Two implementation modes (oracle-based + example-based)
- **UPDATED**: FindScope (Algorithm 2) and FindC (Algorithm 3) details
- **UPDATED**: Oracle and oracle module references (conacq/oracle/)
- Complexity analysis for both modes
- Optimality discussion
- Experimental results (from paper)
- Key advantages
- Query generation heuristics
- Relation to codebase (file locations, implementation patterns)
- Shared infrastructure with CONGEN

**Read when**: You need to understand the QuAcq algorithm or integrate new oracle types.

### congen.md
**Purpose**: ConGen algorithm documentation (MSS-based constraint acquisition)
**Length**: 383 LOC

Paper-based implementation guide:
- Overview of ConGen algorithm (passive/batch learning via MSS)
- Three sub-algorithms: GenerateNE, AcqMSS, REDUCE with pseudocode
- Formal definitions and working example walkthrough
- Complexity analysis and correctness theorems
- Relation to codebase (file locations, LOC)
- Shared infrastructure with QuAcq

**Read when**: You need to understand the ConGen/ACQMSS algorithm or modify passive learning.

## How These Documents Work Together

```
project-overview-pdr.md (WHAT & WHY)
    ↓
    Defines goals, requirements, vision
    ↓
codebase-summary.md (WHERE & WHAT EXISTS)
    ↓
    Maps requirements to code locations
    ↓
system-architecture.md (HOW & WHY ORGANIZED THIS WAY)
    ↓
    Explains design decisions and data flows
    ↓
code-standards.md (HOW TO WRITE CODE THAT FITS)
    ↓
    Guides implementation following established patterns
    ↓
project-roadmap.md (WHAT'S DONE & WHAT'S NEXT)
    ↓
    Tracks progress and future directions

quacq.md (ALGORITHM DETAILS)
    ↓
    Deep dive on QuAcq implementation

congen.md (ALGORITHM DETAILS)
    ↓
    Deep dive on ConGen/ACQMSS implementation
```

## Key Concepts

### Two Learning Paradigms

**CONGEN (Passive/Batch Learning)**
- Learn from sets of valid/invalid example configurations
- Process: `ConGenModel.prepare()` (internally runs GenerateNE) → ACQMSS → REDUCE
- Good for: Offline learning from examples
- Time: 10-30 seconds (65 features), 30-60 minutes (6,467 features)

**QuAcq (Interactive Learning)**
- **Oracle mode** (original): Learn through membership queries with an oracle
- **Example mode** (new): Learn from E+/E- examples using FindScope/FindC (no oracle needed)
- Process: GenerateQuery → Oracle → Update KB (or FindScope/FindC for examples)
- Good for: Online learning with expert feedback or batch example learning
- Convergence: <1,000 queries (models <300 features)

### Oracle Module (NEW)

**Purpose**: Ground truth oracle for validating configurations and generating examples

**Key Classes** (acqmss/oracle/):
- `Oracle` — Abstract base class
- `FeatureModelOracle` — FM-based configuration validator
- `AutomatedOracle` — Automated oracle (FM-based or constraint-based)
- `UserPromptOracle` — Interactive user oracle
- `CachedOracle` — Caching wrapper
- `ExampleProvider` — Batch example interface

**Critical**: Feature ID consistency uses flamapy's variable mapping (tree traversal order) as authoritative source. Alphabetical sorting would cause critical mismatch.

### Solver Modes

**Incremental (Default, ~50x faster)**
- Persistent solver instance across calls
- Uses assumptions for hypothesis testing
- Checkers immutable after construction
- Good for: CONGEN with many consistency checks

**Non-Incremental (Baseline)**
- Fresh solver per call
- Memory-light, clear isolation
- Same assumption-based data representation as incremental
- Good for: Verification and comparison

**SAT4J (Optional, Java-based)**
- External solver via subprocess
- Good for: Cross-validation and solver comparison

### Design Patterns Used

1. **Dependency Injection** — Algorithms accept pluggable ConsistencyChecker
2. **Strategy Pattern** — Multiple solver implementations
3. **Builder Pattern** — DiagnosisModelBuilder for configuration
4. **Facade Pattern** — High-level interfaces (InteractiveLearner, CONGENRunner)
5. **Template Method** — PySATAbstractExplanation algorithm base
6. **Shared Utility Methods** — InteractiveTask.violates_clauses() used across modules

## Common Tasks

### "I want to understand the code organization"
→ Read **codebase-summary.md**
→ Follow the package inventory to source files
→ Cross-reference with **system-architecture.md** for context

### "I need to write new code"
→ Read **code-standards.md** for naming, patterns, testing
→ Use the code review checklist before submitting
→ Follow design patterns from **system-architecture.md**

### "I want to add a new oracle type"
→ Read **quacq.md** → "Relation to Codebase" section
→ Read **system-architecture.md** → acqmss/oracle/ section
→ Extend Oracle ABC from acqmss/oracle/oracle.py
→ Check feature ID consistency requirements

### "I want to add a new algorithm"
→ Read **system-architecture.md** → "Integration points between packages"
→ Follow solver abstraction pattern from **code-standards.md**
→ Implement as ConsistencyChecker subclass or diagnosis algorithm wrapper

### "I need to evaluate my changes"
→ Read **project-overview-pdr.md** → "Success Criteria"
→ Check metrics in **project-roadmap.md** → "Current Metrics"
→ Run tests: `PYTHONPATH=. pytest tests/ -v`

### "I want to know what comes next"
→ Read **project-roadmap.md** → "Future Enhancements"
→ Check "Known Limitations" for workarounds
→ Phase 6 (Documentation & Polish) in progress, Phase 7 planning

## Documentation Statistics

| File | LOC | Size | Status |
|------|-----|------|--------|
| code-standards.md | 694 | 24 KB | ✅ Updated 2026-02-17 (trimmed to <800) |
| codebase-summary.md | 439 | 22 KB | ✅ Updated 2026-02-17 |
| system-architecture.md | 595 | 22 KB | ✅ Updated 2026-02-17 |
| congen.md | 383 | 17 KB | ✅ Updated 2026-02-17 |
| README.md | 364 | 10 KB | ✅ Updated 2026-02-17 |
| project-overview-pdr.md | 352 | 17 KB | ✅ Updated 2026-02-17 |
| project-roadmap.md | 347 | 14 KB | ✅ Updated 2026-02-17 |
| quacq.md | 193 | 7 KB | ✅ Updated 2026-02-17 |
| **TOTAL** | **3,404** | **135 KB** | ✅ **All under 800 LOC** |

All files are within size constraints (≤800 LOC per file) and follow documentation standards.

## Finding Information

### By Topic

**Architecture & Design**
- [system-architecture.md](#system-architecture) — Components, data flows, patterns
- [code-standards.md](#code-standards) → Design Patterns section

**Implementation & Code Quality**
- [code-standards.md](#code-standards) — Comprehensive style guide
- [codebase-summary.md](#codebase-summary) — Where things are
- [system-architecture.md](#system-architecture) → Integration points

**Requirements & Planning**
- [project-overview-pdr.md](#project-overview--pdr) — Goals and requirements
- [project-roadmap.md](#project-roadmap) — Timeline and phases

**Algorithms & Techniques**
- [system-architecture.md](#system-architecture) → Diagnosis algorithms, data flows
- [project-overview-pdr.md](#project-overview--pdr) → Functional requirements
- [quacq.md](#quacq) → QuAcq algorithm details
- [congen.md](#congen) → ConGen algorithm details

**Performance & Optimization**
- [system-architecture.md](#system-architecture) → Performance characteristics, solver modes
- [project-roadmap.md](#project-roadmap) → Current metrics, benchmarks

### By Development Role

**Backend Developer**
1. [code-standards.md](#code-standards) — Style guide and patterns
2. [codebase-summary.md](#codebase-summary) — Code organization
3. [system-architecture.md](#system-architecture) — How components work together
4. Review checklist in [code-standards.md](#code-standards) before each PR

**Algorithm Researcher**
1. [project-overview-pdr.md](#project-overview--pdr) — Algorithm requirements
2. [system-architecture.md](#system-architecture) — Solver abstraction, diagnosis algorithms
3. [quacq.md](#quacq) — QuAcq implementation details
4. [congen.md](#congen) — ConGen/ACQMSS implementation details
5. [project-roadmap.md](#project-roadmap) — Current metrics, performance targets

**DevOps/Maintainer**
1. [project-roadmap.md](#project-roadmap) — Release strategy, milestones
2. [project-overview-pdr.md](#project-overview--pdr) → Dependencies section
3. [codebase-summary.md](#codebase-summary) → Codebase statistics

**New Contributor**
1. Start with main [README.md](../README.md)
2. Read [project-overview-pdr.md](#project-overview--pdr) — Understand what we do
3. Read [codebase-summary.md](#codebase-summary) — Find the code
4. Read [code-standards.md](#code-standards) — Learn how we code
5. Follow design patterns from [system-architecture.md](#system-architecture)

## Additional Resources

- **README.md** (project root) — Quick start and basic workflow
- **CLAUDE.md** (project root) — Development context, workflows, commands
- **requirements.txt** — Python dependencies
- **tests/** — Example usage patterns from test code
- **apps/conf/** — Configuration examples for all applications

## Keeping Documentation Current

Documentation is updated when:
- **Code changes significantly** — Update architecture and standards
- **Requirements change** — Update overview and roadmap
- **Performance changes** — Update metrics and benchmarks
- **Release happens** — Update roadmap and version history
- **New features added** — Document architecture and usage

**Version History:**
- v1.5 (2026-02-18): ConGenModelBuilder auto-prepare pattern, BGData class, runner details, cross-validation refactoring documentation
- v1.4 (2026-02-17): Updated for oracle refactoring (ABC slimmed, FMData introduced, FeatureModelOracle extended), runners/ package move, CheckerFactory import path correction
- v1.3 (2026-02-16): Added congen.md, cross-linked all docs
- v1.2 (2026-02-16): Update for variable naming refactor (neg_c_map → negation_map), CheckerFactory API update
- v1.1 (2026-02-13): Comprehensive update with oracle/ package, Phase 5 completion, file size trim
- v1.0 (2026-02-12): Initial comprehensive documentation

---

**Documentation Status**: Phase 6 (Documentation & Polish) — In Progress
**All files updated**: 2026-02-17
