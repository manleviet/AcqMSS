# Phase 02: Create run_compare.py + describe_kb.py

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-fix-save-and-shared-config.md) (shared config, KB format)

## Overview
- Priority: P1
- Status: completed
- Effort: 1h

Create two new standalone scripts: comparison against ground truth and human-readable KB export.

## Key Insights
- Comparison logic currently embedded in run_congen_eval.py → extract to standalone
- KBComparator already exists in conacq/eval/kb_comparator.py — reuse
- describe_kb.py is pure presentation: ID→description via bias lookup

## Requirements

### run_compare.py
- Load KB file(s) + bias + oracle FM → compare using KBComparator
- Support single file and directory (batch mode)
- Both description and clause strategies
- Required: --bias, --oracle
- Output: *_eval.json with P/R/F1 metrics per strategy
- Verbose mode: print enriched constraints to console

### describe_kb.py
- Load KB file(s) + bias → resolve ID→description
- Support single file and directory
- Required: --bias
- Output formats: JSON (default), TXT (--format txt)

## Related Code Files

### Reuse
- `conacq/eval/kb_comparator.py` — KBComparator, ComparationStrategy
- `conacq/eval/result_loader.py` — ConGenResultData.from_json()
- `conacq/oracle/ground_truth.py` — GroundTruthData.from_uvl()
- `conacq/bias/bias.py` — Bias, BiasIO
- `conacq/eval/config.py` — shared config (from Phase 01)

### Create
- `apps/run_compare.py`
- `apps/describe_kb.py`

## Implementation Steps

### run_compare.py
1. CLI: `PYTHONPATH=. python apps/run_compare.py --kb <file|dir> --bias <path> --oracle <path> [-v] [--strategy all|description|clause]`
2. Load bias (BiasIO), oracle (GroundTruthData.from_uvl)
3. Build KBComparator(oracle, bias)
4. For each KB file: load via ConGenResultData.from_json() → comparator.compare()
5. Save *_eval.json per KB file
6. Verbose: print matched/missed/extra with descriptions

### describe_kb.py
1. CLI: `PYTHONPATH=. python apps/describe_kb.py --kb <file|dir> --bias <path> [--format json|txt] [-o output_dir]`
2. Load bias (BiasIO)
3. For each KB file: load JSON, for each ID in kb_constraints → bias.get_description(id)
4. Output JSON: `[{"id": "c_1", "description": "A requires B"}, ...]`
5. Output TXT: one `id: description` per line

## Todo
- [ ] Create run_compare.py with single + batch mode
- [ ] Create describe_kb.py with JSON + TXT output
- [ ] Test with existing KB files in data/results/
- [ ] Verify compare output matches current run_congen_eval.py metrics

## Success Criteria
- run_compare.py produces same P/R/F1 as current embedded comparison
- describe_kb.py correctly resolves all constraint IDs
- Both scripts work with run_congen.py and CV fold KB outputs
