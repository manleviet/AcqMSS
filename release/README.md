# release/ — the decisions, not the instructions

How to run it is in `./release/carve.sh --help` and in the script's own comments.
Documentation that repeats code drifts from it. What follows are the choices that were
expensive to reach, and would be expensive to reach again.

## 1. The derivation runs AcqMSS → artifact. Never the reverse.

A fix belongs **here** when it is wrong in both places — ConGen code should not use
another paper's coined terms anywhere. It belongs in **`<target>/patches/`** when it is
correct here and meaningless there — this repository keeps ConMin, and it works.

This is first because all three of us got the direction wrong at least once. An
independent verifier proposed removing ConMin from *this* repository three times; the
instruction was relayed once; it was caught only because a decision from an earlier day
was remembered. Making the carve a script converts that judgement into a lookup: in
`release/` means artifact-side, absent means here.

## 2. Allowlist, never blocklist

A blocklist fails silently on the file nobody thought of. Two that no path filter anyone
wrote had matched:

- `apps/conf/run_conmin_config.toml` — the name pattern was `apps/conf_conmin/`
- `tests/test_make_tables.py` — the name pattern was `tests/test_conmin*`, and this file
  was **live in the working tree**, not merely in history

An allowlist fails loudly instead: the forgotten file is absent, and
`reproduce_tables_sosym.sh` stops.

Corollary, now enforced by `carve.sh` rather than remembered: a keep-list line ending in
`/` needs a comment saying why the whole directory is safe. Four separate near-misses
came from directory prefixes — the two above, plus `docs/adr/` re-admitting ADR-0018 and
`conacq/eval/` re-admitting two ConMin evaluators.

## 3. Byte-identity is not a reason to drop a file. "Who reads it" is.

Twenty-nine files are byte-identical with the canonical `explanation` checkout, so every
content comparison said drop them. Four had readers:

| file | reader |
|---|---|
| `tests/__init__.py` | 23 files here do `from tests.…`, 16 of them in the artifact — its role is *existence*, not content |
| `tests/resources/incomplete_catalog.cnf` | `test_transformations_characterization.py` |
| `tests/resources/prod_1_1.cnf` | `resource_paths.py` |
| `tests/resources/smartwatch_inconsistent.fide` | `resource_paths.py` |

The package marker is the sharpest case: identical to another repository's copy, and
load-bearing precisely because nothing reads its contents. The importer reads it.

## 4. This repository keeps ConMin; the artifact does not

That difference is scope, not debt. `conacq/runners/conmin_runner.py` exists here and
works. Every removal that a file-level allowlist cannot express — a function inside a
kept file, a metric spec, a dispatch branch — is a **named patch** under
`<target>/patches/`. Without named patches the hand-editing would simply move inside the
script.

## 5. `release/` is never shipped

A keep-list enumerates what was excluded, which is a map of what was removed. `carve.sh`
asserts that no keep-list pattern begins with `release/` rather than leaving it implicit.

The same reasoning removed `scripts/check-release-hygiene.sh` from the artifact: a
checker that names the terms it forbids is, inside a public repository, the disclosure
it exists to prevent — and inside the tree it scanned it had to exempt itself, so it
reported green while being the violation. It runs from here, against the carve.

## 6. `conmin` is deliberately not one of the checker's terms

The reason is in `scripts/check-release-hygiene.sh` beside the term list; it is repeated
here because this file is read first. Case-insensitively, `conmin` matches fifteen
comments in ConGen's own algorithm files that say a sibling algorithm exists and how a
shared code path is shaped for it. None names the venue, the title, or the review.

A gate that is red on day one gets relaxed until it checks nothing. Two such relaxations
have already been removed from that script.

## Method rules

Learned the expensive way, each from a check that reported success while unable to
observe the failure it existed to prevent:

- **Every selective check runs in both directions — missing and extra.** A
  one-directional check is a systematic way to overlook things, not a weaker one. This
  file's own output gate compared only one way and was blind to a tracked file the
  shipped `.gitignore` silently dropped from the commit. The same shape appeared four
  times before that: a `.get()` default standing in for a missing key, filtering by
  filename instead of by role, `git grep` over paths instead of contents, and an
  `exists()` guard turning an absent input into a pass.
- **Byte-identity is not a reason to drop a file; "who reads it" is.** See §3.
- **A gate that is red on day one gets relaxed until it checks nothing.** See §6.
- **A pass is a positive count, never the absence of a negative.** A suite reported an
  empty set of failures because pytest was not installed; a targeted run reported success
  against a test file that did not exist. Both exited 0. Naming this did not stop it
  recurring an hour later, so it is now a gate in two places: `check_paper_numbers.py`
  refuses a run of fewer than 90 checks, and `reproduce_tables_sosym.sh` refuses a tree
  whose tests cannot be collected.
- **A gate must stand on a measured number, not a chosen one.** If you find yourself
  picking a threshold, first look for the real signal being thrown away. A proposed
  minimum collection count would have differed per repository (681 here, 343 in the
  artifact), needed a per-target patch to maintain, and given a reader no baseline to
  compare against — a gate creating maintenance without creating information. Meanwhile
  `pytest` was already reporting exit 2 on a broken `conftest.py`, and `2>/dev/null` was
  discarding it. The same error produced the case-insensitive `conmin` proposal in §6.
- **An assertion must be shown to be capable of failing.** If it has never been red,
  make it red once before trusting it. Three boundary rules in this repository passed for
  months while scanning directories that did not exist — green lights wired to nothing.
  An empty assertion is worse than an absent one: it reads as coverage in every report
  and promises a protection that is not there. The same shape produced a `.get()` default
  standing in for a missing key, a suite that "passed" with pytest uninstalled, and a
  targeted run that succeeded against a test file that did not exist. Every gate added
  during this release was deliberately made to fail once before being believed.
- **A named exception inside a check will grow; a named patch fails loudly when it is
  wrong.** When a gate fires on a case you believe legitimate, put the exception
  *outside* the gate. Offered a carve-out for one file under `data/`, the right answer
  was a patch: the guard stays absolute with zero exemptions, and the single case fails
  visibly if it drifts. Two exemptions had already been removed from the hygiene script
  for exactly this reason.
- **Line-based search is blind to a phrase that wraps.** `grep` and line-wise
  substitution both miss `"byte-comparable with ConMin's\n  ``size``"`. This bit three
  separate times in one day — a substitution rule that silently skipped a file, a
  reviewer's grep that under-counted, and a check that reported clean. Where the answer
  matters, search the joined text, not the lines.
- **Report `git show --stat` of the commit, never the diff you intended.** Two commits
  in this effort were described by what they were meant to contain: a staged revert had
  already been picked up, so a message announcing a seven-line fix shipped twenty-three
  files. Read back what git recorded, not what you asked for.
- **Measure the radius before trusting a force.** `git add -A -f` is safe here because
  exactly one tracked file is also matched by `.gitignore` — measured with
  `git ls-files | git check-ignore --no-index --stdin`, not assumed. At forty files it
  would not have been safe.

## The acceptance gate

Two numbers and a scan — never "the items were applied":

1. `pytest tests/ -q` on a clean machine → **328 passed, 18 skipped, 0 failed**, reported
   as the set of red test names, not a total. A total that drops by three looks identical
   whether three tests were deleted or three broke.
2. `./reproduce_tables_sosym.sh` → five tables byte-identical with the committed ones;
   only `PROVENANCE.md` differs, on its SHA line.
3. Content scan on the artifact's committed HEAD → empty.
