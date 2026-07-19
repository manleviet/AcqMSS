# AcqMSS Pipeline — Scripts Explanation

## Pipeline Overview

```
Feature Model (.uvl)
       │
       ├─[1] generate_bias_config.py  → YAML config
       ├─[2] generate_bias_files.py   → bias JSON + CNF
       ├─[3] generate_examples.py     → examples E+/E- (6 strategies)
       ├─[4] generate_cv_folds.py     → fold assignments
       │
       ├─[5] run_cv.py                → CV results + KB files    ← PAPER EVALUATION
       ├─[6] run_compare.py           → eval JSON (P/R/F1)       ← OPTIONAL
       │
       └─[7] extract_results.py       → .md + .tex TABLES        ← FINAL OUTPUT
```

### Auxiliary Scripts (not for paper evaluation)

```
run_congen.py       → single ConGen run (debug/demo), 1 KB file per model
run_quacq.py  → single QuAcq run (debug/demo), 1 KB file per model
```

### CLI output convention (stdout vs stderr)

Every app writes its **result to files** (KB JSON, CV JSON, `.md`/`.tex` tables) and
routes **diagnostics** — banners, progress, warnings, errors — through Python
`logging`, which goes to **stderr**. The only thing on **stdout** is an app's
*product*: currently just `run_cv`'s printed CV report. So `run_cv … > report.txt`
captures the clean report with no banner noise.

Verbosity is a **log level**, unified from the `-v` flag **or** a config
`[general] verbose = true` (whichever is set, applied after the config loads):
default shows INFO progress; `-v`/config-verbose adds DEBUG detail. (Before, some
progress went to stdout and a config `verbose` could be silently ignored — both
fixed.)

---

## Phase 1: Data Preparation (run once)

### [1] generate_bias_config.py

Generates YAML configuration describing bias structure from a feature model.

```bash
python -m apps.generate_bias_config data/fms/REAL-FM-7.uvl -v
```

| | |
|---|---|
| **Input** | Feature model `.uvl` file |
| **Output** | `data/bias-config/{model}.yaml` |
| **Run per** | Each feature model |

### [2] generate_bias_files.py

Converts YAML bias config into constraint files (JSON for algorithms, CNF for SAT solvers).

```bash
python -m apps.generate_bias_files data/bias-config/REAL-FM-7.yaml
```

| | |
|---|---|
| **Input** | YAML config from step 1 |
| **Output** | `data/bias/{model}-bias.json` + `.cnf` + `-stats.txt` |
| **Contains** | Bias B = set of candidate constraints |

### [3] generate_examples.py

Generates positive (E+) and negative (E-) example configurations using 6 sampling strategies.

```bash
python -m apps.generate_examples apps/conf/generate_examples_config.toml -v
```

| | |
|---|---|
| **Input** | TOML config with models list + strategies |
| **Output** | `data/examples/{model}_{strategy}.json` (1 file per model × strategy) |
| **Config** | `apps/conf/generate_examples_config.toml` |

**6 Sampling Strategies:**

| Strategy | Description |
|---|---|
| RS(1n) | Random Sampling, n examples (n = #features) |
| RS(2n) | Random Sampling, 2n examples |
| RS(3n) | Random Sampling, 3n examples |
| RS(m) | Random Sampling, m examples (m = smallest for 2-wise coverage) |
| 2-COV | Pairwise coverage — each pair of features covered |
| FF | Feature Frequency — each feature appears as True/False |

### [4] generate_cv_folds.py

Pre-generates fold assignments for reproducible cross-validation.

```bash
python -m apps.generate_cv_folds apps/conf/generate_cv_folds_config.toml
```

| | |
|---|---|
| **Input** | TOML config + example files |
| **Output** | `data/folds/{model}_{strategy}_folds.json` |
| **Config** | `apps/conf/generate_cv_folds_config.toml` |
| **Default** | 3-fold cross-validation |

---

## Phase 2: Experiments & Evaluation

### [5] run_cv.py — Main Evaluation Script

Runs n-fold cross-validation. Supports both ConGen and QuAcq (example-based mode).

```bash
python -m apps.run_cv apps/conf/run_cv_config.toml -v
```

| | |
|---|---|
| **Input** | TOML config with models (oracle, bias, examples, folds) |
| **Config** | `apps/conf/run_cv_config.toml` |

**Key config options:**

```toml
[general]
output_dir = "data/results"     # algorithm name auto-appended → data/results/congen/
seed = 82

[evaluation]
algorithm = "congen"            # "congen" or "interactive"
n_folds = 3
solver_mode = "non-incremental" # "all", "incremental", or "non-incremental"
shuffle_bias = true
```

**Output directory**: `output_dir / {algorithm}` — the algorithm name (`congen` or `interactive`) is automatically appended as a subdirectory.

**Two algorithm modes in run_cv.py:**

| Config | Algorithm | Internal call | Input |
|---|---|---|---|
| `algorithm = "congen"` | ConGen (passive) | `ConGenRunner(bias_path, fm_path, ...).run()` | Examples E+/E- |
| `algorithm = "interactive"` | QuAcq (example-based) | `QuAcqRunner(bias_path, fm_path, ...).run(pos_examples, neg_examples, mode='example_only')` | Same examples — fair comparison |

**Output files per model (example: REAL-FM-7_rs_1n, 3-fold, non-incremental):**

Output directory is `{output_dir}/{algorithm}/` — the algorithm name is auto-appended.

```
data/results/congen/          ← algorithm = "congen"
├── REAL-FM-7_rs_1n_non-incremental_fold1_kb.json        # KB learned from fold 1
├── REAL-FM-7_rs_1n_non-incremental_fold2_kb.json        # KB learned from fold 2
├── REAL-FM-7_rs_1n_non-incremental_fold3_kb.json        # KB learned from fold 3
├── REAL-FM-7_rs_1n_non-incremental_intersected_kb.json  # Intersection of fold KBs
└── REAL-FM-7_rs_1n_cv_non-incremental.json              # CV summary (accuracy, metrics)

data/results/interactive/     ← algorithm = "interactive"
├── REAL-FM-7_rs_1n_non-incremental_fold1_kb.json        # KB learned from fold 1
├── REAL-FM-7_rs_1n_non-incremental_fold2_kb.json        # KB learned from fold 2
├── REAL-FM-7_rs_1n_non-incremental_fold3_kb.json        # KB learned from fold 3
├── REAL-FM-7_rs_1n_non-incremental_intersected_kb.json  # Intersection of fold KBs
└── REAL-FM-7_rs_1n_cv_non-incremental_example_only.json # CV summary (with query_mode suffix)
```

**Performance-block schema (post-T9 — read this before diffing old vs new result files).**
The CV summary's aggregated `"performance"` block is `{group: {stat: value}}`. As of
the runners+metrics refactor (ADR-0006), each algorithm declares its own disjoint
metric table (`conacq/runners/metrics.py`):

- **New ConGen** CV files carry **13 groups** (runtime, consistency_checks, memory,
  kb_size, congen_runtime, acqmss_runtime, acqmss_calls, reduce_runtime, solver_time,
  is_consistent_calls, is_consistent_test_cases_calls, redundancy_consistency_checks —
  plus `n_runs`). QuAcq gets its own disjoint table.
- **Legacy** ConGen files (recorded before T9) carry **29 groups** — the extra 16 are
  zeroed QuAcq groups the old single union-container emitted into every file. Those
  files are **not** regenerated and stay byte-for-byte as recorded.
- `apps.extract_results` reads **both** shapes: it consumes only the four ConGen-owned
  groups (`runtime`/`consistency_checks`/`memory`/`kb_size`), so the paper tables are
  identical from either. A diff of an old vs a new file will show the dropped zeroed
  QuAcq groups — that is expected, not a regression.

### [6] run_compare.py — Optional KB Evaluation

Compares learned KB(s) against ground truth feature model. Adds precision/recall/F1 using description and clause matching strategies.

**TOML config mode (recommended):**

```bash
python -m apps.run_compare apps/conf/run_compare_config.toml -v
```

**CLI mode (single model):**

```bash
python -m apps.run_compare \
  --kb data/results/congen/ \
  --bias data/bias/REAL-FM-7-bias.json \
  --oracle data/fms/REAL-FM-7.uvl -v
```

| | |
|---|---|
| **Input** | KB file(s) + bias JSON + oracle FM (.uvl) |
| **Output** | `*_eval.json` per KB file |
| **Config** | `apps/conf/run_compare_config.toml` |
| **Strategies** | `description` (semantic match) and `clause` (CNF clause match) |

`extract_results.py` automatically merges these eval files into the final tables.

### [7] extract_results.py — Generate Paper Tables

Reads all CV results and eval files, generates Markdown and LaTeX tables.

**TOML config mode (recommended):**

```bash
python -m apps.extract_results apps/conf/extract_results_config.toml
```

**CLI mode:**

```bash
python -m apps.extract_results \
  --results-dir data/results/congen \
  --output-dir paper/tables \
  --mode both
```

| | |
|---|---|
| **Input** | `*_cv_*.json` + `*_eval.json` files in results dir |
| **Output** | `paper/tables/results_tables.md` + `results_tables.tex` |
| **Config** | `apps/conf/extract_results_config.toml` |

**Tables generated:**

| Table | Content |
|---|---|
| Table 7 | #consistency checks + runtime per strategy × KB |
| Table 9 | Accuracy for Random Sampling strategies |
| Table 10 | Accuracy for 2-COV |
| Table 11 | Accuracy for FF |
| Fold Metrics | Precision / Recall / F1 per fold |
| Performance | Runtime, checks, memory, bias/mss/kb sizes |
| KB Summary | Bias size, KB size, intersected, reduction % |
| Strategy Eval | Description vs clause comparison (P/R/F1) |
| Inc vs Non-Inc | Incremental vs non-incremental solver comparison |

---

## Auxiliary Scripts (not part of paper evaluation pipeline)

### run_congen.py — Single ConGen Run

Runs ConGen once on full examples. No CV, no folds, no evaluation. For debugging and quick testing.

```bash
python -m apps.run_congen apps/conf/run_congen_config.toml -v
```

| | |
|---|---|
| **Output per model** | 1 file: `{model}_{strategy}_kb.json` |
| **Use case** | Debug, inspect learned KB, input for run_compare.py |

### run_quacq.py — Single QuAcq Run (Oracle Mode)

Runs QuAcq with QueryProvider (SAT-based mode) + Oracle. No examples needed — self-generates queries via SAT solving: `SAT(KB ∪ BG ∪ ¬c)`.

```bash
python -m apps.run_quacq apps/conf/run_quacq_config.toml -v
```

| | |
|---|---|
| **Output per model** | 1 file: `{model}_interactive_kb.json` |
| **Modes** | `automated` (FM oracle answers) or `--interactive` (human answers) |
| **Use case** | Demo interactive learning, test QuAcq algorithm (generates queries from SAT) |

---

## QuAcq: Two Operating Modes

| Mode | Method | Used by | Input | Query/Example source |
|---|---|---|---|---|
| **Oracle** | `QuAcq.learn()` with mode='oracle' | `run_quacq.py` | Oracle FM only | `QueryProvider.generate_from_sat()` (SAT-based query generation) |
| **Example-based** | `QuAcq.learn()` with mode='example_only'/'example_first' | `run_cv.py` (algorithm=interactive) | Examples E+/E- | `QueryProvider.generate_from_pool()` or fallback to `generate_from_sat()` |

Example-based mode exists for **fair comparison** with ConGen — both algorithms receive the same input examples.

---

## KB File Format (shared across all scripts)

All scripts use `save_kb_result()` producing identical JSON format:

```json
{
  "kb_constraints": ["c_1", "c_2", "..."],
  "redundant_constraints": ["c_5", "..."],
  "bg_clauses": [[1]],
  "statistics": {
    "n_bias": 100,
    "n_mss": 30,
    "n_kb": 20
  },
  "metadata": {}
}
```

Compatible with `run_compare.py` regardless of source script.

---

## Data Directory Structure

```
data/
├── fms/              # Feature models (.uvl)               ← INPUT
├── bias-config/      # Bias YAML configs                   ← Step 1 output
├── bias/             # Bias JSON + CNF                     ← Step 2 output
├── examples/         # E+/E- examples per model×strategy   ← Step 3 output
├── folds/            # CV fold assignments                  ← Step 4 output
└── results/
    ├── congen/       # ConGen CV results                   ← Step 5 output
    └── interactive/  # Interactive results                  ← Step 5 output
```

## KB Name Mapping (Paper)

| Paper Name | Feature Model | Features | Cross-tree Constraints |
|---|---|---|---|
| KB1 | REAL-FM-7 | 14 | 2 |
| KB2 | fqa | 179 | 9 |
| KB3 | arcade-game | 65 | 34 |
| KB4 | REAL-FM-4 | 291 | 21 |

---

## Config Files Summary

| Script | Config File | Purpose |
|---|---|---|
| generate_examples.py | `apps/conf/generate_examples_config.toml` | Models + sampling strategies |
| generate_cv_folds.py | `apps/conf/generate_cv_folds_config.toml` | Models + fold count |
| run_congen.py | `apps/conf/run_congen_config.toml` | Single ConGen run (debug) |
| run_quacq.py | `apps/conf/run_quacq_config.toml` | Single QuAcq run (debug) |
| run_cv.py | `apps/conf/run_cv_config.toml` | CV evaluation (main) |
| run_compare.py | `apps/conf/run_compare_config.toml` | KB comparison (optional) |
| extract_results.py | `apps/conf/extract_results_config.toml` | Table generation |

## Typical Run Sequence

```bash
# Phase 1: Data Preparation (run once)
python -m apps.generate_bias_config data/fms/REAL-FM-7.uvl -v
python -m apps.generate_bias_files data/bias-config/REAL-FM-7.yaml
python -m apps.generate_examples apps/conf/generate_examples_config.toml -v
python -m apps.generate_cv_folds apps/conf/generate_cv_folds_config.toml

# Phase 2: Run experiments (main — takes the longest)
python -m apps.run_cv apps/conf/run_cv_config.toml -v
# → output auto-saved to data/results/{algorithm}/

# Phase 2b: Optional — compare KB with ground truth for extra metrics
python -m apps.run_compare apps/conf/run_compare_config.toml -v

# Phase 3: Extract tables for paper
python -m apps.extract_results apps/conf/extract_results_config.toml
```
