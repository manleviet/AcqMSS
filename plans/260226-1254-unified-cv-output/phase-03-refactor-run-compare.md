# Phase 3: Refactor run_compare.py to Read/Write Unified JSON

## Context Links
- `apps/run_compare.py` — Current comparison script (220 lines)
- `conacq/eval/kb_comparator.py` — `KBComparator`, `ComparationResult`
- `conacq/eval/result_loader.py` — `ConGenResultData`
- `conacq/eval/config.py` — `find_kb_files()`, `ModelConfig`
- Phase 1 deliverables: `ConGenResultData.from_dict()`, `ComparationResult.to_enriched_dict()`

## Overview
- Priority: P1
- Status: completed
- Rewrite `run_compare.py` to read unified CV JSONs, compare each fold + intersected KB, write evaluation back into the same file, and compute summary metrics

## Key Insights

### Current flow
1. `find_kb_files()` globs for `*_kb.json` and `*_intersected_kb.json`
2. For each KB file: `ConGenResultData.from_json(path)` -> `comparator.compare()` -> save `*_eval.json`
3. Produces separate eval files that `extract_results.py` later discovers and merges

### New flow
1. Find `*_cv_*.json` files in kb_dir (unified files)
2. For each unified file:
   a. Load JSON
   b. For each fold: construct `ConGenResultData.from_dict(fold)`, run `comparator.compare()`, write `evaluation` back
   c. For intersected_kb: same — construct `ConGenResultData` from intersected data, compare, write evaluation
   d. Compute summary metrics (mean/std of P, R, F1 across folds)
   e. Write enriched file back to same path
3. Idempotent: re-running overwrites evaluation fields

## Requirements

### Functional
1. Read unified CV JSON files (not separate KB files)
2. For each fold: create `ConGenResultData`, run `comparator.compare()` per strategy, write evaluation into fold's `evaluation` field
3. For intersected_kb: same — compare and write evaluation
4. Compute summary: mean/std of precision, recall, f1_score across folds per strategy
5. Write summary into top-level `summary` field
6. Evaluation items (TP, FP, FN) include both constraint ID and description
7. Save enriched file back to same path (idempotent)
8. Keep CLI mode (`--kb` flag) working for single-file comparison (backward compat)

### Non-functional
- `run_compare.py` stays under 200 lines
- Reuse existing `KBComparator` and `ComparationStrategy` unchanged

## Architecture

### Config mode flow (new)

```
for each model in config:
    load bias, oracle, create comparator
    find *_cv_*.json files in kb_dir
    for each cv_file:
        data = json.load(cv_file)
        for each fold in data['folds']:
            result_data = ConGenResultData.from_dict(fold)
            eval_dict = {}
            for strategy in strategies:
                com_result = comparator.compare(result_data, strategy)
                eval_dict[strategy.value] = com_result.to_enriched_dict(bias)
            fold['evaluation'] = eval_dict

        # Intersected KB
        ik = data['intersected_kb']
        ik_result = ConGenResultData.from_dict(ik)
        ik_eval = {}
        for strategy in strategies:
            com_result = comparator.compare(ik_result, strategy)
            ik_eval[strategy.value] = com_result.to_enriched_dict(bias)
        ik['evaluation'] = ik_eval

        # Summary
        data['summary'] = compute_summary(data, strategies)

        json.dump(data, cv_file)
```

### Summary computation

```python
def compute_summary(data: dict, strategies: List[ComparationStrategy]) -> dict:
    """Compute mean/std of P, R, F1 across folds per strategy."""
    summary = {}
    for strategy in strategies:
        key = strategy.value
        precisions, recalls, f1s = [], [], []
        for fold in data['folds']:
            if fold.get('evaluation') and key in fold['evaluation']:
                m = fold['evaluation'][key]['metrics']
                precisions.append(m['precision'])
                recalls.append(m['recall'])
                f1s.append(m['f1_score'])

        summary[key] = {
            'precision': _mean_std(precisions),
            'recall': _mean_std(recalls),
            'f1_score': _mean_std(f1s),
        }
    return summary

def _mean_std(values: list) -> dict:
    if not values:
        return {'mean': 0.0, 'std': 0.0}
    m = statistics.mean(values)
    s = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {'mean': m, 'std': s}
```

### Finding unified CV files

Add to `conacq/eval/config.py`:

```python
def find_cv_files(cv_path: Path) -> List[Path]:
    """Find unified CV JSON files from path."""
    if cv_path.is_file() and cv_path.name.endswith('.json'):
        return [cv_path]
    if cv_path.is_dir():
        return sorted(cv_path.glob('*_cv_*.json'))
    return []
```

## Related Code Files

### Modify
- `apps/run_compare.py` — Major rewrite of config mode; keep CLI mode for legacy
- `conacq/eval/config.py` — Add `find_cv_files()`
- `conacq/eval/__init__.py` — Export `find_cv_files`

## Implementation Steps

### Step 1: Add `find_cv_files()` to `config.py`

Simple glob for `*_cv_*.json` pattern. Keep existing `find_kb_files()` for backward compat.

### Step 2: Rewrite `compare_kb()` -> `compare_fold()`

New function that takes fold dict + comparator + bias + strategies, returns enriched eval dict:

```python
def compare_entry(entry: dict, comparator: KBComparator,
                  bias: Bias, strategies: List[ComparationStrategy],
                  verbose: bool, label: str = "") -> dict:
    """Compare a fold or intersected KB entry. Returns evaluation dict."""
    result_data = ConGenResultData.from_dict(entry)
    eval_dict = {}
    for strategy in strategies:
        com_result = comparator.compare(result_data, strategy)
        eval_dict[strategy.value] = com_result.to_enriched_dict(bias)
        if verbose:
            m = com_result.metrics
            print(f"    {label}{strategy.value}: P={m.precision:.4f}, R={m.recall:.4f}, F1={m.f1_score:.4f}")
    return eval_dict
```

### Step 3: Rewrite `compare_model()` for config mode

```python
def compare_model_unified(model, strategies, verbose):
    """Compare all unified CV files for a model."""
    kb_path = Path(model.kb_dir)
    cv_files = find_cv_files(kb_path)
    if not cv_files:
        print(f"  Warning: No CV files found in {model.kb_dir}")
        return 0

    bias = BiasIO.load_from_json(model.bias)
    oracle = GroundTruthData.from_uvl(Path(model.oracle))
    comparator = KBComparator(oracle, bias)

    count = 0
    for cv_file in cv_files:
        print(f"  {cv_file.name}")
        with open(cv_file) as f:
            data = json.load(f)

        # Compare each fold
        for fold in data.get('folds', []):
            label = f"Fold {fold['fold_index']}: "
            fold['evaluation'] = compare_entry(
                fold, comparator, bias, strategies, verbose, label)

        # Compare intersected KB
        ik = data.get('intersected_kb', {})
        if ik and ik.get('kb_constraints'):
            ik['evaluation'] = compare_entry(
                ik, comparator, bias, strategies, verbose, "Intersected: ")

        # Compute summary
        data['summary'] = compute_summary(data, strategies)
        if verbose:
            for key, vals in data['summary'].items():
                p = vals['precision']
                r = vals['recall']
                f1 = vals['f1_score']
                print(f"    Summary({key}): P={p['mean']:.4f}+/-{p['std']:.4f}, "
                      f"R={r['mean']:.4f}+/-{r['std']:.4f}, "
                      f"F1={f1['mean']:.4f}+/-{f1['std']:.4f}")

        # Write back
        with open(cv_file, 'w') as f:
            json.dump(data, f, indent=2)
        count += 1

    return count
```

### Step 4: Update `run_config_mode()`

Replace `compare_model()` call with `compare_model_unified()`.

### Step 5: Keep CLI mode working

CLI mode (`--kb` flag) stays as-is for single-file legacy comparison. It still uses `find_kb_files()` and produces `*_eval.json`. This provides backward compat for any non-CV use cases.

### Step 6: Update `run_compare_config.toml`

The config needs `kb_dir` to point to the directory with unified CV files. Current config already does this: `kb_dir = "data/results/congen"`. No change needed.

## Todo List
- [ ] Add `find_cv_files()` to `config.py`
- [ ] Add `compare_entry()` helper function
- [ ] Add `compute_summary()` function
- [ ] Rewrite `compare_model()` -> `compare_model_unified()` for config mode
- [ ] Update `run_config_mode()` to use unified flow
- [ ] Keep CLI mode (`--kb`) working for backward compat
- [ ] Export `find_cv_files` from `__init__.py`
- [ ] Test with: `python -m apps.run_compare apps/conf/run_compare_config.toml -v`

## Success Criteria
- `run_compare.py` reads unified CV files and writes evaluation back into same file
- Each fold's `evaluation` field populated with strategy results containing id+description
- `intersected_kb.evaluation` populated
- `summary` field populated with mean/std of P, R, F1 across folds
- Re-running is idempotent (overwrites evaluation fields)
- CLI mode still works for single-file comparison
- File stays under 200 lines

## Risk Assessment
- **Risk**: Unified CV file may not have `statistics` in fold data (needed by `ConGenResultData.from_dict()`)
  - **Mitigation**: Fold `to_dict()` already includes `statistics` key with `n_bias`, `n_mss`, `n_kb`
- **Risk**: `intersected_kb` has no `statistics` section
  - **Mitigation**: `ConGenResultData.from_dict()` falls back to `n_kb=len(kb_constraints)` when stats missing
