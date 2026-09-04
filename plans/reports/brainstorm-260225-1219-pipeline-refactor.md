# Brainstorm: Pipeline Scripts Refactor

## Problem Statement

Current pipeline has 4 scripts with mixed responsibilities:
- `run_congen.py` — ConGen learning only (no eval, missing bg_clauses in output)
- `run_congen_eval.py` — ConGen + CV + comparison + enrichment (monolithic)
- `run_interactive_eval.py` — QuAcq + eval + CV + enrichment (monolithic)
- `extract_results.py` — Parse CV JSONs → paper tables

**Issues identified:**
1. `save_kb_result()` missing `bg_clauses` (root constraint not in run_congen.py output)
2. CV + comparison tightly coupled — can't rerun comparison without rerunning CV
3. Enrichment (descriptions) embedded in eval scripts — redundant since compare needs bias anyway
4. ConGen CV and Interactive CV duplicate fold/accuracy logic
5. KB files inconsistent: CV path has bg_clauses, run_congen.py path doesn't

## Agreed Design Principles

- **KB files store IDs only** — no descriptions (bias is single source of truth)
- **Compare script always requires bias** — resolves ID→description and ID→clauses
- **Enrichment only at presentation layer** — verbose console output, paper tables
- **bg_clauses (root constraint) in all KB outputs** — consistent data format

## Target Architecture

```
apps/
├── run_congen.py          ← ConGen learning → KB files (keep, fix bg_clauses)
├── run_interactive.py     ← QuAcq learning → KB files (extract from eval)
├── run_cv.py              ← N-fold CV for BOTH algorithms (new, unified)
├── run_compare.py         ← KB vs GroundTruth comparison (new)
├── describe_kb.py         ← Enrich KB IDs → human-readable file (new)
└── extract_results.py     ← Parse results → paper tables (refactor)
```

### Data Flow

```
Step 1: Learn KB
  run_congen.py / run_interactive.py
  Input: TOML config (FM, bias, examples)
  Output: *_kb.json (IDs + bg_clauses + statistics)

Step 2: Cross-Validate
  run_cv.py --algorithm congen|interactive
  Input: TOML config
  Output: *_cv_{mode}.json (fold results, accuracy, intersected KB)

Step 3: Compare KB vs Ground Truth
  run_compare.py
  Input: KB files + bias + oracle FM
  Output: *_eval.json (P/R/F1 per strategy)

Step 3b: Describe KB (human-readable)
  describe_kb.py
  Input: KB file(s) + bias
  Output: *_described.json or *_described.txt (IDs + descriptions)

Step 4: Generate Tables
  extract_results.py
  Input: *_cv_*.json + *_eval.json
  Output: MD + LaTeX tables
```

## Changes Per Script

### 1. `run_congen.py` — Fix bg_clauses

**Current:** calls `save_kb_result()` which lacks bg_clauses
**Change:**
- Add `bg_clauses` param to `save_kb_result()`
- Pass `result.bg_clauses` from `ConGenRunResult`
- Output format now consistent with CV fold KB files

### 2. `run_interactive.py` — Extract from run_interactive_eval.py

**Current:** `run_interactive_eval.py` does learning + eval + CV + enrichment
**Change:**
- Extract pure learning logic into `run_interactive.py`
- Remove evaluation, CV, and enrichment code
- Output: `{name}_interactive_kb.json` with IDs + bg_clauses

### 3. `run_cv.py` — Unified Cross-Validation (NEW)

**Current:** CV logic split between `run_congen_eval.py` and `run_interactive_eval.py`
**Change:**
- Single script with `algorithm` config field (`congen` | `interactive`)
- Reuse existing `n_fold_cross_validation()` and `n_fold_cross_validation_interactive()`
- Remove comparison/enrichment logic (delegated to run_compare.py)
- Output: `*_cv_{mode}.json` (fold results, accuracy, intersected KB — IDs only)
- Save fold KB files + intersected KB

### 4. `run_compare.py` — KB Comparison (NEW)

**Current:** comparison embedded in `run_congen_eval.py` → `compare_cv_with_strategy()`
**Change:**
- Standalone script: load KB file + bias + oracle → compare
- Supports both description and clause strategies
- Input: single KB file OR CV result (compare intersected KB + per-fold KBs)
- Required inputs: `--bias` (always), `--oracle` (always)
- Output: `*_eval.json` with metrics per strategy
- Enrichment only in verbose console output (not persisted)

### 5. `describe_kb.py` — Human-Readable KB Export (NEW)

**Motivation:** KB files store IDs only (design principle). Humans need descriptions to understand learned constraints.
**Change:**
- Load KB file(s) + bias → resolve ID→description via `bias.get_description(cid)`
- Input: single KB file OR directory (batch mode)
- Required: `--bias` path
- Output formats:
  - JSON: `[{"id": "c_1", "description": "A requires B"}, ...]`
  - TXT (optional `--format txt`): one constraint per line for quick inspection
- Works with any KB output: run_congen, run_interactive, run_cv fold/intersected KBs
- Pure presentation utility — no modification to source KB files

### 6. `extract_results.py` — Adapt to New File Format

**Current:** parses `*_cv_*.json` containing embedded `intersected_evaluation`
**Change:**
- Also load `*_eval.json` files from run_compare.py
- Merge CV data (accuracy, runtime) with comparison data (P/R/F1)
- Adapt filename parsing if naming convention changes
- Generate same paper tables (Tables 7,9,10,11)

## KB Output Format (Unified)

```json
{
  "kb_constraints": ["c_1", "c_2", "c_5"],
  "bg_clauses": [[1]],
  "redundant_constraints": ["c_3", "c_4"],
  "statistics": {
    "n_bias": 20,
    "n_mss": 15,
    "n_kb": 3
  }
}
```

All KB outputs (run_congen, run_interactive, run_cv fold KBs) use this format.

## Shared Module Extraction

Functions currently duplicated across scripts → extract to `conacq/eval/`:
- `load_config()` — TOML loading (duplicated 3x)
- `parse_models()` — model config parsing (duplicated 3x, slightly different)
- `ModelConfig` dataclass — duplicated 3x with different fields

Consider unified `conacq/eval/config.py`:
```python
@dataclass
class ModelConfig:
    name: str
    oracle: str
    bias: str
    examples: str = None
    folds_path: str = None

def load_pipeline_config(config_path: str) -> Dict[str, Any]: ...
def parse_models(config: Dict) -> List[ModelConfig]: ...
```

## Risk Assessment

| Risk | Impact | Mitigation |
|:---|:---|:---|
| extract_results.py breaks | Paper table generation fails | Test with existing data/results before removing old scripts |
| CV results format changes | Old results incompatible | Keep backward-compat in result_loader.py |
| Filename convention changes | extract_results.py parser breaks | Define convention upfront, update parser |
| Interactive CV config differs | run_cv.py gets complex | Use algorithm-specific config sections in TOML |

## Implementation Order

1. Fix `save_kb_result()` — add bg_clauses (quick fix, unblocks everything)
2. Extract shared config module (`conacq/eval/config.py`)
3. Create `run_compare.py` (new, independent)
4. Create `describe_kb.py` (new, independent — simple utility)
5. Create `run_cv.py` (unified CV, replaces CV parts of eval scripts)
6. Simplify `run_congen.py` and create `run_interactive.py`
7. Refactor `extract_results.py` to work with new file layout
8. Remove old `run_congen_eval.py` and `run_interactive_eval.py`
9. Test full pipeline end-to-end

## Unresolved Questions

1. Should `run_compare.py` accept a directory (batch compare all KB files) or single file? -> support both: single file for quick compare, directory for batch mode (e.g. all CV fold KBs + intersected KB)
2. TOML config: one unified config file for whole pipeline, or separate per script? -> separate per script with shared sections (e.g. [models]) seems cleaner and more modular
3. `run_interactive.py`: keep profiler (BENCHMARK) or move profiling to run_cv.py? -> keep in run_interactive.py for now, can refactor later if needed
