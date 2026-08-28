# Two sources: quality numbers from the re-run, runtime numbers from the sequential sweep

Date 2026-08-28. Branch `feat/sosym-r1`. Decision by Viet-Man: the runtime table takes its
numbers from the original sequential sweep; the quality tables take theirs from the re-run
under the final code state. Both sources named, rather than mixed silently.

## Why the split is needed at all

Running several jobs at once cannot change a SAT answer, so everything the tables report
about *what was learned* is unaffected: `n_kb`, `n_ne`, `kb_constraints`, the three tiers'
P/R/F1, `exact_equiv`, and the order-sensitivity survivor sets. That is not an argument —
the probe reproduced |B′| = 517 / 209 / 502 against the committed `n_mss`, and the B′
recovery gate held on 72/72 folds, while other jobs were running.

What contention does change is wall-clock. Measured: busybox `rs_1n` fold 0 took **4.10 h**
against the ledger's **3.94 h** for the same cell run alone — **+4%**. Small, but the
published runtime table (`evaluation.tex:399`, total runtime comparison) is made of exactly
that quantity, and mixing contended with uncontended cells compares cells measured under
different conditions.

## The one way contention could have corrupted a deterministic number — checked, and clear

`timeout_s` is a wall-clock guard at 6 h. A fold pushed past it by contention stops early
and records `convergence_reason='timeout'`, which is not comparable with a fold that
stopped on its budget. That is the only path from CPU load to a non-timing number.

Across 51 CV files, 153 folds:

| convergence_reason | folds |
|---|---|
| `pool_exhausted` | 84 |
| `max_queries` | 51 |
| `no_query` | 18 |
| **`timeout`** | **0** |

Every fold stopped on a deterministic rule. The margin is not thin either: the most
expensive fold measured is 4.98 h against the 6 h guard.

## The two sources are exactly separable, and the boundary is computed

The ledger stamps `started_utc` / `finished_utc` on every unit, so "ran alongside something
else" is a property of the record rather than a recollection. Over 238 completed units with
timestamps:

- **0 units overlap another ledger unit.** The window lock held for the whole sweep — no
  two sweep units ever ran at the same time. All 234 original units are mutually
  uncontended.
- **6 units ran alongside a non-ledger job**, all of them started 2026-08-28, while the
  NE-split measurements and the busybox re-runs were on the machine:

| unit | actual_h |
|---|---|
| `interactive_example_first\|REAL-FM-4_2cov\|fold0` | 4.98 |
| `interactive_example_first\|REAL-FM-4_2cov\|fold1` | 1.86 |
| `interactive_example_first\|REAL-FM-4_2cov\|fold2` | 2.25 |
| `interactive_example_first\|REAL-FM-4_rs_m\|fold0` | 3.01 |
| `interactive_example_first\|REAL-FM-4_rs_m\|fold1` | pending, will also be contended |
| `interactive_example_first\|REAL-FM-4_rs_m\|fold2` | pending, will also be contended |

Selection rule, executable rather than descriptive — a unit's timing is contended iff:

    started_utc >= '2026-08-28'

Nothing before that date shares the machine with anything, by the overlap check above.

## What each table takes

| table | source | why |
|---|---|---|
| runtime comparison | the **sequential sweep** — units with `started_utc < 2026-08-28` | timing is the reported quantity, so it must come from one condition |
| accuracy, three tiers, exact equivalence, \|KB\| | the **re-run under the final code state** | deterministic, unaffected by contention, and must come from one code state |

The two requirements pull in opposite directions and that is the whole reason for naming
both: the quality tables need the newest code, the runtime table needs the quietest
machine, and no single set of runs is both.

Cost of the decision: none. It uses runs that already exist rather than re-measuring 12 h
of busybox serially.

## Unresolved

1. The 6 REAL-FM-4 example-first units have no uncontended timing at all — they are new
   work, not a re-run, so there is no sequential measurement of them to fall back on. If
   the runtime table needs those cells, they must be re-timed alone or the cells left out
   and said so.
2. `data/results_sosym/interactive/` now holds both sources in one directory. The
   separation is recoverable from the ledger, but nothing in the filenames carries it.
