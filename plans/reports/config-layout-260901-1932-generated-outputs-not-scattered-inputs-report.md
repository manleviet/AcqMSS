# The configs under `data/results_sosym/` are not scattered — they are co-located

Investigated 2026-09-01 after a proposal to gather them into `apps/conf_sosym_r1/`,
by analogy with `apps/conf/` and `apps/conf_conmin/`. **The proposal was withdrawn on
the evidence below. `apps/conf_sosym_r1/` was deliberately not created.**

Written down because the next person to notice "104 TOML files loose under `data/`"
will re-propose the same move. The analogy is what fails: `conf/` and `conf_conmin/`
hold **hand-maintained inputs that drive runs**; these are **generated outputs
co-located with the results they produced**. Same extension, opposite role.

## The reference test

**0 of 104** config TOMLs is named by a full literal path anywhere in `apps/`,
`tools/`, `conacq/`, `docs/`, or the shell scripts. Every path is *constructed*,
which is what decides movability — not whether a grep finds the filename.

> A first pass reported 16 "referenced". False positives: the basename `config.toml`
> matches as a substring of `run_evaluation_config.toml`. The same imprecision earlier
> matched `sweep_queue.py` out of a *comment* and would have promoted it into `apps/`.
> A mechanical test is only as good as its precision.

| group | n | how the path is built | verdict |
|---|---|---|---|
| `configs/` | 84 | `sweep_queue.py:270` → `REPO / ledger['output_root'] / 'configs'` | stays |
| `cap_probe_*/…/config.toml` | 16 | `probe_query_budget.py:77-83` writes into `cell_dir`, then runs `run_cv … -o cell_dir` | stays |
| `compare_configs*/` | 4 | `make_score_configs.py --out <dir>`, CLI-supplied | movable, but pointless |

## Why each stays

**The 16 cap-probe configs are one artifact with their results.** `probe_query_budget.py`
writes `config.toml` into the cell directory and passes that same directory as `-o` in
the next statement. One call produces both. Moving the config splits something the tool
creates as a unit, and would make the prober write to two places.

**The 84 sweep configs are coupled to the results tree.** Their directory derives from
the ledger's `output_root`, which is also what places the results. Relocating them means
changing `output_root`, which moves `data/results_sosym/` — the tree that must not move,
because it is the OLD half of the old-vs-new pairing the N item rests on. The proposal
contradicted that constraint, and nothing surfaced it until the paths were traced. They
are also write-then-immediately-consume (`sweep_queue.py:324` → `:335`), never read back:
a record of what ran, not an input anyone edits.

**The 4 scoring configs are movable and not worth moving.** They are generated to a
CLI-supplied path and document a scoring pass that has already happened. A directory
holding four generated files has no reader.

## The defect this investigation found

`data/results_sosym_r1/compare_configs/score_interactive.toml` carried **56 absolute
paths hardcoding one developer's checkout**; all four pre-existing configs were relative.

Cause: `rglob` over a *relative* `--cv-dir` yields relative paths, `relative_to(REPO)`
against an absolute REPO raises, and the fallback `resolve()` bakes in the checkout.

The absolute paths were seen when the file was generated and judged harmless **because
the run worked**. That is the wrong test: it answers whether the path resolves on this
machine, not whether the package resolves on any other. A config in a reproducibility
package that only one machine can use is the same shape as every other defect in this
effort — a check that could not fail for the reason it was meant to catch.

Fixed at `0e5e138` (`resolve()` before `relative_to`). Now guarded by rule rather than
by luck: `check_paper_numbers.py` §11 fails if any tracked `.toml` names an absolute or
home-relative path, on any platform. Verified to fire by planting one — it names the
file and exits 1. 120 tracked TOMLs are clean today.

## Unresolved

None. Item closed; `apps/conf_sosym_r1/` is not created, and this report is why.
