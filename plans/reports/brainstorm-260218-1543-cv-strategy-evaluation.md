# Brainstorm: CV Strategy Evaluation

## Problem
`run_congen_eval.py` only computes accuracy via `AccuracyCalculator` (SAT-based). Need to also evaluate each fold KB + intersected KB against oracle FM groundtruth using `Evaluator` with description/clause strategies.

## Requirements
- **Timing**: After all folds complete
- **Output**: In `_cv_*.json` (per-fold) + separate `*_eval_strategy.json` for intersected KB
- **Tables**: Add strategy eval metrics to `extract_results.py`
- **Config**: User selects strategies via TOML `[evaluation].strategy` field

## Agreed Approach
1. Restore strategy config parsing in `run_congen_eval.py`
2. After CV loop, create `Evaluator.from_files()` once
3. Evaluate each fold KB + intersected KB with selected strategies
4. Append `strategy_evaluation` to each fold in CV JSON
5. Save intersected KB eval to separate file
6. Extend `CVResult` in `extract_results.py` with strategy eval fields
7. Add table generators for strategy eval metrics

## JSON Structure
```json
"folds": [{
  "strategy_evaluation": {
    "description": { "accuracy", "precision", "recall", "f1_score", "tp", "fp", "fn" },
    "clause": { "accuracy", "precision", "recall", "f1_score", "tp", "fp", "fn", "tn" }
  }
}],
"intersected_evaluation": {
  "description": { ... },
  "clause": { ... }
}
```

## Risk
- Evaluator FM loading adds one-time cost per model. Acceptable since shared across folds.
- Large models may take longer. Mitigation: strategy is optional config.
