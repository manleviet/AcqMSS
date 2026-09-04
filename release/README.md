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

## The acceptance gate

Two numbers and a scan — never "the items were applied":

1. `pytest tests/ -q` on a clean machine → **328 passed, 18 skipped, 0 failed**, reported
   as the set of red test names, not a total. A total that drops by three looks identical
   whether three tests were deleted or three broke.
2. `./reproduce_tables_sosym.sh` → five tables byte-identical with the committed ones;
   only `PROVENANCE.md` differs, on its SHA line.
3. Content scan on the artifact's committed HEAD → empty.
