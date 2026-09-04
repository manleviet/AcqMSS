# Brainstorm: TOML Config for run_compare.py & describe_kb.py

## Problem
`run_compare.py` and `describe_kb.py` only accept CLI args. User needs to compare/describe all models (6+) in batch, requiring repeated commands with different bias/oracle paths.

## User Requirements
- Compare all models in one run (6+ models)
- Separate config files (not reusing run_cv/run_congen configs)
- Add `kb_dir` to shared `ModelConfig` dataclass
- KB files can be in multiple dirs (congen/, interactive/) → multiple `[[models]]` entries per FM

## Agreed Design

### Config files

**`apps/conf/run_compare_config.toml`**
```toml
[general]
output_dir = "data/results/congen"
verbose = true

[compare]
strategy = "all"

[[models]]
name = "REAL-FM-7_congen"
oracle = "data/fms/REAL-FM-7.uvl"
bias = "data/bias/REAL-FM-7-bias.json"
kb_dir = "data/results/congen"
```

**`apps/conf/describe_kb_config.toml`**
```toml
[general]
output_dir = "data/results/congen"
verbose = true

[describe]
format = "json"

[[models]]
name = "REAL-FM-7"
bias = "data/bias/REAL-FM-7-bias.json"
kb_dir = "data/results/congen"
```

### CLI dual-mode
```bash
# Config mode (batch)
PYTHONPATH=. python apps/run_compare.py apps/conf/run_compare_config.toml -v

# CLI mode (single, backward compat)
PYTHONPATH=. python apps/run_compare.py --kb path --bias path --oracle path
```

Detection: positional arg is .toml → config mode; --kb present → CLI mode.

### ModelConfig change
```python
@dataclass
class ModelConfig:
    name: str
    oracle: str
    bias: str
    examples: Optional[str] = None
    folds_path: Optional[str] = None
    kb_dir: Optional[str] = None  # NEW
```

### Implementation steps
1. Add `kb_dir` to ModelConfig + parse_models()
2. Update run_compare.py: add config mode, keep CLI fallback
3. Update describe_kb.py: add config mode, keep CLI fallback
4. Create TOML config files
5. Test both modes

### Effort: ~45 min
