# Phase 02: Refactor apps/run_congen.py to Use ConGenRunner

## Context Links
- [Plan](plan.md) | [Phase 01](phase-01-move-runners.md)
- Branch: `refactor/dry-congen-runner`

## Overview
- **Priority**: Medium
- **Status**: pending (blocked by Phase 01)
- **Description**: Replace duplicated inline logic in `apps/run_congen.py:process_model()` with `ConGenRunner`

## Key Insights
- `process_model()` (L77-175) duplicates ConGenRunner's build→prepare→run→cleanup flow
- ConGenRunner already collects metrics (timing, memory, checks) — run_congen.py gets free metrics
- Differences to handle:
  - run_congen.py loads examples via `ExampleIO` — keep in script
  - run_congen.py saves result via `congen.save_result()` — need alternative since ConGenRunner returns `ConGenRunResult`
  - run_congen.py has verbose print statements — keep in script
  - run_congen.py uses `get_global_profiler()` — ConGenRunner creates its own Profiler

## Related Code Files

**Modify:**
- `apps/run_congen.py` — refactor `process_model()` to use ConGenRunner

**Reference (no change):**
- `acqmss/runners/congen_runner.py` — ConGenRunner API

## Implementation Steps

1. Update imports in `apps/run_congen.py`:
   - Add: `from acqmss.runners import ConGenRunner`
   - Remove: `ConGen`, `ConGenModelBuilder`, `resolve_congen_names`, `FeatureModelOracle`, `CheckerFactory`, `get_global_profiler`
   - Keep: `ExampleIO`, argparse, tomllib, Path, etc.

2. Refactor `process_model()`:
   ```python
   def process_model(model_config, output_dir, seed, verbose,
                     is_incremental=True, solver_name='glucose4'):
       try:
           model_name = Path(model_config.path).stem
           sampling_type = extract_sampling_type(model_config.examples)

           if verbose:
               # ... print config info (keep as-is)

           # Load examples
           examples = ExampleIO.load_json(model_config.examples)
           pos = [e.assignments for e in examples.positive]
           neg = [e.assignments for e in examples.negative]

           # Run ConGen via runner
           runner = ConGenRunner(model_config.bias, model_config.path,
                                 solver_name, is_incremental)
           try:
               result = runner.run(pos, neg)
           finally:
               runner.cleanup()

           if verbose:
               print(f"  MSS size: {result.n_mss}")
               print(f"  Acquired KB: {result.n_kb} constraints")
               print(f"  Runtime: {result.runtime_ms:.2f}ms")
               print(f"  Checks: {result.consistency_checks}")
               if result.kb_constraints:
                   for c in result.kb_constraints[:10]:
                       print(f"    - {c}")

           # Save result
           output_file = output_dir / f"{model_name}_{sampling_type}_kb.json"
           save_run_result(result, output_file)

           return True
       except Exception as e:
           print(f"Error processing {model_config.path}: {e}")
           traceback.print_exc()
           return False
   ```

3. Add `save_run_result()` helper (or use `ConGenRunResult.to_dict()` + json.dump):
   ```python
   def save_run_result(result: ConGenRunResult, output_file: Path):
       import json
       with open(output_file, 'w') as f:
           json.dump(result.to_dict(), f, indent=2)
   ```

4. Clean up unused imports and `main()` (remove profiler setup if no longer needed)

5. Validate:
   ```bash
   PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
   ```

## Todo List
- [ ] Update imports in `apps/run_congen.py`
- [ ] Refactor `process_model()` to use ConGenRunner
- [ ] Add save helper for ConGenRunResult
- [ ] Remove unused code (profiler setup, etc.)
- [ ] Test with actual config

## Success Criteria
- `process_model()` reduced from ~100 lines to ~40 lines
- Same output behavior (verbose prints, saved JSON)
- No duplicate ConGen execution logic

## Risk Assessment
- **Medium risk**: Output JSON format may differ slightly (`ConGenRunResult.to_dict()` vs `congen.save_result()`)
  - Mitigation: Check if downstream `evaluate_congen_results.py` expects specific JSON keys — adapt `save_run_result()` accordingly
- `ConGenRunner` creates its own `Profiler` — `run_congen.py` currently uses `get_global_profiler()`. After refactor, profiler metrics route through ConGenRunner's internal profiler. This is fine — the script wasn't using profiler stats anyway.
