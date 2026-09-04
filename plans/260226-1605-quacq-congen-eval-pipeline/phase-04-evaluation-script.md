# Phase 4: Evaluation Script + Config

## Context

- Parent plan: [plan.md](plan.md)
- Dependencies: Phase 1, Phase 2, Phase 3 (all must be complete)
- Blocks: None (final phase)

## Overview

- **Date**: 2026-02-26
- **Priority**: P1
- **Status**: pending
- **Effort**: 1.5h

App script orchestrating the full QuAcq->ConGen evaluation pipeline. Follows existing app patterns: TOML config, `python -m apps.run_evaluation`, argparse CLI, verbose output, JSON results.

## Key Insights

- Existing app scripts (`run_interactive.py`, `run_congen.py`, `run_cv.py`) share a pattern: argparse + `load_pipeline_config()` + `parse_models()` + per-model processing + summary table.
- `InteractiveRunner` handles QuAcq automated mode. After Phase 1, its result includes `query_history`.
- `ConGenRunner` handles ConGen runs. Reused across checkpoints by `ProgressiveEvaluator`.
- `KBComparator.from_files()` creates comparator from FM + bias paths.
- `GroundTruthData.from_uvl()` loads ground truth without solver.
- Output JSON should contain: metadata, QuAcq summary, progressive checkpoints, QuAcq final comparison.

## Requirements

### Functional
1. TOML config specifying FM paths, bias, checkpoints, output dir
2. CLI: `python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v`
3. Per-model pipeline: QuAcq -> progressive ConGen -> comparisons -> JSON output
4. Batch support: iterate `[[models]]` sections
5. Summary table printed to stdout
6. JSON output per model with full results

### Non-functional
- Follow existing app script patterns (argparse, verbose flags, error handling)
- PYTHONPATH=. required (consistent with project)
- Graceful error handling per model (continue batch on failure)
- Log timing for each phase of the pipeline

## Architecture

```
run_evaluation.py
    |
    +--- main()
    |       parse args + load TOML config
    |       parse_models(config) -> List[ModelConfig]
    |       for each model:
    |           process_model(model, config) -> EvaluationOutput
    |       print summary table
    |
    +--- process_model(model_config, eval_config)
            |
            +--- InteractiveRunner(bias, fm).run(mode='automated')
            |       -> InteractiveRunResult (with query_history)
            |
            +--- ConGenRunner(bias, fm)
            |       (passed to ProgressiveEvaluator)
            |
            +--- KBComparator.from_files(fm, bias)
            |
            +--- GroundTruthData.from_uvl(fm)
            |
            +--- ProgressiveEvaluator(congen_runner, comparator, gt, checkpoints)
            |       .evaluate(query_history, quacq_result)
            |       -> ProgressiveResult
            |
            +--- Save JSON output
            +--- Return summary dict
```

## Related Code Files

### Create
| File | Description |
|------|-------------|
| `apps/run_evaluation.py` | Main evaluation script (~150 lines) |
| `apps/conf/run_evaluation_config.toml` | Example TOML config (~30 lines) |
| `tests/test_evaluation_pipeline.py` | Integration test on small FM |

### No modifications to existing files
All integration happens via imports of classes built in Phases 1-3.

## Implementation Steps

### Step 1: Create TOML config

`apps/conf/run_evaluation_config.toml`:

```toml
# QuAcq -> ConGen Evaluation Pipeline Configuration
# Run with: python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v

[general]
output_dir = "data/results/evaluation"
verbose = true

[evaluation]
# Query budget checkpoints (percentages of total QuAcq queries)
checkpoints = [10, 25, 50, 75, 100]

# Comparison strategies to run at each checkpoint
strategies = ["description", "clause", "semantic"]

[quacq]
# Mode: "automated" uses FM oracle (reproducible)
mode = "automated"
max_queries = 1000
shuffle_seed = 42
solver_name = "glucose4"

[congen]
solver_name = "glucose4"
use_incremental = true

# Models to evaluate
[[models]]
name = "REAL-FM-7"
oracle = "data/fms/REAL-FM-7.uvl"
bias = "data/bias/REAL-FM-7-bias.json"
```

### Step 2: Create `run_evaluation.py` — argparse + main

```python
#!/usr/bin/env python
"""
Run QuAcq -> ConGen evaluation pipeline.

Runs QuAcq (automated) to generate queries, then feeds progressive
subsets to ConGen and compares both KBs against ground truth.

Usage:
    python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from conacq.runners import InteractiveRunner, ConGenRunner
from conacq.eval.config import load_pipeline_config, parse_models
from conacq.eval.kb_comparator import KBComparator
from conacq.eval.progressive_evaluation import ProgressiveEvaluator
from conacq.oracle.ground_truth import GroundTruthData
```

Argparse flags:
- `config` (positional): TOML config path
- `-v / --verbose`: verbose output
- `-o / --output-dir`: override output dir
- `--max-queries`: override max queries
- `--solver`: SAT solver name
- `--debug`: enable debug logging

### Step 3: Implement `process_model()`

```python
def process_model(model_config, eval_config, output_dir, verbose):
    """Run full evaluation pipeline for a single model.

    Returns:
        dict with summary metrics, or None on error
    """
```

Logic:
1. Extract config values (checkpoints, strategies, quacq settings, congen settings)
2. Create `InteractiveRunner` and run QuAcq automated mode
3. Print QuAcq summary (queries, KB size, convergence)
4. Create `ConGenRunner`, `KBComparator`, `GroundTruthData`
5. Create `ProgressiveEvaluator` with checkpoints from config
6. Call `evaluator.evaluate(query_history, quacq_run_result)`
7. Build output dict with metadata + progressive results
8. Save JSON to `output_dir / f"{model_name}_evaluation.json"`
9. Print checkpoint summary table
10. Return summary dict for batch summary
11. Cleanup runners

### Step 4: Implement `main()`

```python
def main():
    # Parse args
    # Load config
    # Parse models
    # Create output dir
    # Print header
    # For each model: process_model()
    # Print batch summary table
```

Summary table columns:
```
Model          Queries  QuAcq-KB  ConGen-KB@100%  Semantic-Eq  Runtime
REAL-FM-7       142       18          22             Yes        3.2s
```

### Step 5: Output JSON structure

```json
{
  "metadata": {
    "model": "REAL-FM-7",
    "fm_path": "data/fms/REAL-FM-7.uvl",
    "bias_path": "data/bias/REAL-FM-7-bias.json",
    "timestamp": "2026-02-26T16:05:00",
    "checkpoints_pct": [10, 25, 50, 75, 100]
  },
  "quacq": {
    "n_queries": 142,
    "n_kb": 18,
    "convergence_reason": "empty_bias",
    "runtime_ms": 1234.56,
    "comparison": {
      "description": { "...ComparationResult.to_dict()..." },
      "clause": { "..." },
      "semantic": { "...SemanticResult.to_dict()..." }
    }
  },
  "progressive": [
    {
      "checkpoint_pct": 10,
      "n_queries": 14,
      "n_positive": 8,
      "n_negative": 6,
      "congen_n_kb": 12,
      "congen_runtime_ms": 456.78,
      "comparison": {
        "description": { "..." },
        "clause": { "..." },
        "semantic": { "..." }
      }
    }
  ]
}
```

### Step 6: Integration test

`tests/test_evaluation_pipeline.py`:

Requires a small FM fixture (e.g., REAL-FM-7 if available in test data, or a synthetic 5-feature FM).

Test cases:
1. **Config loading**: verify TOML parses correctly
2. **End-to-end on small FM**: run full pipeline, verify output JSON structure
3. **Progressive checkpoints**: verify correct number of checkpoints in output
4. **Output file created**: verify JSON file exists and is valid

Mark integration tests with `@pytest.mark.slow` (project convention).

## Todo List

- [ ] Create `apps/conf/run_evaluation_config.toml`
- [ ] Create `apps/run_evaluation.py` with argparse skeleton
- [ ] Implement `process_model()` function
- [ ] Implement `main()` with batch loop + summary table
- [ ] Implement JSON output serialization
- [ ] Create `tests/test_evaluation_pipeline.py`
- [ ] Test with: `PYTHONPATH=. python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v`
- [ ] Run `PYTHONPATH=. pytest tests/test_evaluation_pipeline.py -v`
- [ ] Run full test suite

## Success Criteria

1. `python -m apps.run_evaluation config.toml -v` runs end-to-end on a real FM
2. JSON output contains all checkpoint results + QuAcq final comparison
3. Summary table prints to stdout with key metrics
4. Batch mode processes multiple models, continues on per-model failure
5. All existing tests pass

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| QuAcq takes long on large FM | High | `max_queries` config cap; progress logging; `--max-queries` CLI override |
| ConGen fails at low-query checkpoints | Medium | `ProgressiveEvaluator` already skips checkpoints with insufficient examples (Phase 3) |
| Output JSON too large | Low | Only store summary metrics per checkpoint, not full clause lists. Limit `unentailed_ct/kb` to 20 items. |
| Missing FM/bias files | Low | Validate paths before processing; graceful error message |

## Security Considerations

- No external network calls
- File paths from TOML config only (local filesystem)
- No credentials or secrets involved

## Next Steps

After completion:
- Run on real FMs to generate evaluation data
- Analyze results for paper: learning curves, convergence rates, semantic equivalence
- Consider visualization script (matplotlib/plotly) for learning curve plots — future enhancement
