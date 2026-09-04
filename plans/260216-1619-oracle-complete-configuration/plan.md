---
title: "Add complete_configuration() to Oracle, remove hidden coupling"
description: "Extend Oracle ABC with complete_configuration() and get_cnf_clauses(), move SAT solving out of ExampleGenerator"
status: complete
priority: P2
effort: 3h
branch: refactor/extract-oracle-from-congen
tags: [refactor, oracle, example-generators, type-safety]
created: 2026-02-16
---

# Oracle complete_configuration() Refactoring

## Problem

`ExampleGenerator._generate_valid_config()` and `FeatureFrequencyGenerator._generate_valid_config_for_coverage()` call `oracle.get_cnf_clauses()` -- a method only on `FeatureModelOracle`, NOT on `Oracle` ABC. This creates hidden type coupling: generators accept `Oracle` but silently require `FeatureModelOracle`.

Additionally, generators import `pysat.solvers.Solver` directly, creating SAT solver logic that belongs in the oracle layer.

## Callers of `get_cnf_clauses()`

| Caller | File | Type |
|--------|------|------|
| `ExampleGenerator._generate_valid_config()` | `example_generators/base.py:88` | Hidden coupling |
| `FeatureFrequencyGenerator._generate_valid_config_for_coverage()` | `example_generators/feature_frequency.py:208` | Hidden coupling |
| `InteractiveLearner.from_examples_and_files()` | `algorithms/interactive/learner.py:213` | Uses FeatureModelOracle directly |
| `OracleData.from_uvl()` / `from_oracle()` | `oracle/extractor.py:51,83` | Already typed as FeatureModelOracle |

## Strategy

- Add `complete_configuration()` to Oracle ABC (generators call this instead of raw SAT)
- Add `get_cnf_clauses()` to Oracle ABC (needed by extractor.py and learner.py)
- Implement both in FeatureModelOracle; raise NotImplementedError in others
- Refactor generators to use `complete_configuration()`

## Phases

| Phase | File | Status |
|-------|------|--------|
| 1 | [phase-01-extend-oracle-abc.md](phase-01-extend-oracle-abc.md) | Complete |
| 2 | [phase-02-implement-in-fm-oracle.md](phase-02-implement-in-fm-oracle.md) | Complete |
| 3 | [phase-03-refactor-generators.md](phase-03-refactor-generators.md) | Complete |
| 4 | [phase-04-verify.md](phase-04-verify.md) | Complete |

## Key Decisions

1. `complete_configuration()` returns `Optional[Dict[str, bool]]` -- None means no valid completion
2. `get_cnf_clauses()` stays abstract -- UserPromptOracle/CachedOracle raise NotImplementedError
3. CachedOracle delegates `complete_configuration()` and `get_cnf_clauses()` to base oracle
4. SAT solver import removed from generators after refactoring

## Risk

- Low: All current generator usage passes FeatureModelOracle anyway
- Breaking: UserPromptOracle now needs stub implementations (NotImplementedError is acceptable)
