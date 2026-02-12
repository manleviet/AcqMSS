# AcqMSS Documentation

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
**Length**: 355 LOC

Defines what AcqMSS is, why it exists, and what success looks like:
- Executive summary
- Problem statement and motivation
- 7 core functional requirements (CONGEN, QuAcq, diagnosis, evaluation, etc.)
- 6 non-functional requirements (performance, accuracy, quality, compatibility)
- Success criteria and key metrics
- Development phases overview

**Read when**: You need to understand the "why" and "what" of the project.

### codebase-summary.md
**Purpose**: Code organization and inventory
**Length**: 298 LOC

High-level overview of what code exists where:
- Package structure (acqmss, explanation, apps, tests)
- Detailed LOC breakdown per component
- File inventory by purpose
- Data directory structure (feature models, configurations, results)
- Dependencies (runtime, development, optional)
- Key architectural patterns
- Codebase statistics (126,878 total LOC, 524 files)

**Read when**: You need to find where something is implemented, or understand the code organization.

### code-standards.md
**Purpose**: Development guidelines and conventions
**Length**: 707 LOC

Comprehensive style guide and best practices:
- Language requirements (Python 3.13+, type hints)
- Naming conventions (modules, classes, functions, variables)
- File organization and import order
- 5 design patterns with code examples
- Testing strategy (parameterization, coverage requirements)
- Documentation standards (docstring formats)
- Type hints and error handling
- Configuration management (TOML-driven)
- Performance and security considerations
- Code review checklist (12 items)

**Read when**: You're writing code or reviewing others' code. Use the checklist before submitting PRs.

### system-architecture.md
**Purpose**: Technical architecture and data flows
**Length**: 680 LOC

Deep dive into how the system works:
- Two-layer architecture overview
- Detailed package organization with API examples
- Data flow diagrams (CONGEN learning flow, QuAcq interactive flow)
- Solver architecture (incremental, non-incremental, SAT4J modes)
- Integration points between packages
- Performance characteristics (algorithm complexity, optimization)
- Testing architecture
- Design decisions and trade-offs
- Future architecture enhancements

**Read when**: You need to understand how components interact, or you're making architectural changes.

### project-roadmap.md
**Purpose**: Development timeline and progress
**Length**: 468 LOC

Project status and future planning:
- 5 development phases (4 complete, 1 in progress)
- Current metrics (code quality, performance benchmarks)
- Completed milestones and deliverables
- Future enhancements (short/medium/long-term)
- Known limitations and workarounds
- Quality assurance status
- Release strategy (v1.0, v1.1, v2.0)
- Health indicators and success criteria

**Read when**: You need to understand project status, or you're planning future work.

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
```

## Key Concepts

### Two Learning Paradigms

**CONGEN (Passive/Batch Learning)**
- Learn from sets of valid/invalid example configurations
- Process: GenerateNE → ACQMSS → REDUCE
- Good for: Offline learning from examples
- Time: 10-30 seconds (65 features), 30-60 minutes (6,467 features)

**QuAcq (Interactive Learning)**
- Learn through membership queries to an oracle
- Process: Loop of GenerateQuery → Oracle → Update KB
- Good for: Online learning with expert feedback
- Convergence: <1,000 queries (models <300 features)

### Solver Modes

**Incremental (Default, ~50x faster)**
- Persistent solver instance across calls
- Uses assumptions for hypothesis testing
- Good for: CONGEN with many consistency checks

**Non-Incremental (Baseline)**
- Fresh solver per call
- Memory-light, clear isolation
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
6. **Factory Pattern** — CONGENModel.from_bias_and_examples()

## Common Tasks

### "I want to understand the code organization"
→ Read **codebase-summary.md**
→ Follow the package inventory to source files
→ Cross-reference with **system-architecture.md** for context

### "I need to write new code"
→ Read **code-standards.md** for naming, patterns, testing
→ Use the code review checklist before submitting
→ Follow design patterns from **system-architecture.md**

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

## Documentation Statistics

| File | LOC | Size | Sections | Status |
|------|-----|------|----------|--------|
| code-standards.md | 754 | 21 KB | 16 | ✅ Complete |
| codebase-summary.md | 329 | 13 KB | 10 | ✅ Complete |
| project-overview-pdr.md | 355 | 16 KB | 12 | ✅ Complete |
| system-architecture.md | 813 | 26 KB | 15 | ✅ Complete |
| project-roadmap.md | 509 | 17 KB | 13 | ✅ Complete |
| quacq.md | 102 | 4 KB | 7 | ✅ Complete |
| **TOTAL** | **2,862** | **97 KB** | **73** | ✅ **Complete** |

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
3. [project-roadmap.md](#project-roadmap) — Current metrics, performance targets
4. Benchmark against metrics in [project-roadmap.md](#project-roadmap)

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

**Last Updated**: 2026-02-12
**Documentation Version**: 1.0
