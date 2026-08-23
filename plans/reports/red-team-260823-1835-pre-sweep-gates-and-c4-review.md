# Red team — the 17 commits of 2026-08-23

- Scope: `012ce31` … `e9bc10b` on `feat/sosym-r1` (17 commits; `85d2178` was pre-staged, excluded).
- Method: attack specific hypotheses against the diffs, then try to make each one fail
  in the running system. Not a re-read of the commit messages.
- Suite at review time: 665 passed, 1 skipped. `data/results*` clean.

## Findings

| # | severity | commit | finding |
|---|---|---|---|
| 1 | **medium** | `ff4566b` (C6) | an NE that Reduce drops disappears from every output list |
| 2 | low (claim) | `012ce31` (C7) | the "generic" root/domain split is a no-op filter; the comment overclaims |
| 3 | low (env) | `b8cced3` (C4) | installed metadata does not list the new extras (stale editable install) |

---

### 1. NE dropped by Reduce vanishes entirely — `congen_model.py:113`

```python
_, redundant_names, _ = self._resolve_ids(describe, result.redundant_ids)
```

`_resolve_ids` now returns `(clauses, fm_names, non_fm_names)`. For `redundant_ids` the
third element — the NE names — is **discarded**. Before C6, `redundant_names` was a single
list and contained them.

So when Reduce drops an NE as entailed, that NE is:

- not in `kb_constraints` (correct — it is not in the KB)
- not in `ne_constraints` (that list is built from `kb_assumption_ids` only)
- not in `redundant_constraints` (discarded here)

**Confirmed in the running system**, not inferred. Taking a real REAL-FM-7 rs_1n result
and moving the NE id from `kb_assumption_ids` to `redundant_ids` — exactly what Reduce
does when it finds the NE entailed:

```
NE id: 746 | description: NOT(mdi = true & sdi = true)
  in kb_constraints?        False
  in ne_constraints?        False
  in redundant_constraints? False
  => VANISHES ENTIRELY
```

**Why it is invisible today**: Reduce drops 0 NE on every available fixture (measured
during C6 — prepared NE = 1 and `n_ne` = 1 on all six REAL-FM-7 example sets). The
runner golden shows `redundant_constraints` HELD across C6, which is consistent with
"no NE was ever in it", not with "nothing was lost".

This is the same defect class the NE-clause fix addressed — a population silently
dropped on the way out — reintroduced one commit earlier, in the reporting path rather
than the theory path. It is strictly an accounting loss: the delivered theory is
unaffected, since a redundant NE is by definition entailed by what remains.

**Proposed fix** (not applied — this was a review):

```python
_, redundant_names, redundant_ne_names = self._resolve_ids(describe, result.redundant_ids)
```

and surface `redundant_ne_names` beside `redundant_constraints`, so |KB| accounting
stays closed: `prepared NE = n_ne + redundant NE`. That identity is also the
discriminating test the C6 work could not write, because no fixture drops an NE —
with the field present, a synthetic result (as used above) can assert it.

### 2. The C7 "generic" derivation is a no-op — `task_preparation.py:176-179`

```python
root_id = bg_data.assumptions[0]
bg_ids = [assumptions[0]]
set_b = [a for a in bg_ids if a != root_id]
root_axiom = tuple(a for a in bg_ids if a == root_id)
```

`assumptions[0]` **is** `bg_data.assumptions[0]` — Step 0 extends `assumptions` with
`bg_data.assumptions` and `prepare_kb` only appends after it. So `bg_ids` is a
one-element list holding exactly the root, `set_b` is **always** `[]` and `root_axiom`
**always** `(root,)`. The filter cannot do anything.

The comment claims "Generic: derive by dropping the root id, never hardcode ∅, so a
non-boolean FM's domain axioms survive." That is not what the code achieves: no domain
axiom can enter `bg_ids` in the first place. Genericity would require the BG
construction to admit domain axioms, which it does not.

In fairness the ConMin original I ported had the same shape (`task.set_b` was likewise
root-only), so the illusion predates today — but the commit message and comment assert
genericity, which makes it a claim rather than an inherited quirk.

**Behaviourally correct, wrongly justified.** Either construct `bg_ids` from a real BG
source, or say plainly that BG is root-only today and the filter documents intent for
when it is not.

### 3. Installed metadata does not list the new extras

`pyproject.toml` correctly declares `dev`, `baselines`, `baselines-cn2`, and uv resolves
`.[baselines-cn2]` from source (it warns on a bogus extra name, so parsing is fine). But
`importlib.metadata.metadata('acqmss')` reports `Provides-Extra: dev` only — the editable
install's metadata predates the edit and was never regenerated.

Harmless to the tests, which import directly. Matters for anyone verifying "are the
extras declared?" against the installed distribution, and for the environment freeze,
which is intended as reviewer-facing evidence. Fix: reinstall editable.

---

## Probed and clean

Each of these was a specific hypothesis, checked rather than assumed:

- **C10 delta counting is not double-counting.** `is_consistent_calls` advances only
  inside the wrapped `is_consistent_test_cases` call; nothing else runs in that window,
  and the batch counters were verified byte-identical for both algorithms.
- **`reduce.py:91` remains commented** — `git diff` against `c377567` is empty.
- **ConGen registers the combined NE in `negation_map`** (`task_preparation.py:249`), so
  the NE-clause resolver can never hit its "no negation entry" refusal on the ConGen path.
- **ConMin still inherits the moved resolver.** `_resolve_fallback_clause` is a
  staticmethod on `KBModel`; ConMin's call site is unchanged and its 51 tests pass.
- **Shuffling does not corrupt the NE resolution.** The runner passes `task.set_kb`
  after `replace(task, set_c=shuffled)`, and `replace` leaves `set_kb` untouched.
- **`ne_clauses` and `ne_names` correspond by index** — both iterate
  `kb_assumption_ids` in order under the same predicate.
- **The added `n_ne` key breaks no consumer.** `result_loader.py` and
  `extract_results.py` read `statistics` with `.get(...)`, so an extra key is inert.
- **The C4 threshold matches the declared rule.** `min(n_valid, n_invalid) < 10` is
  exactly "not both classes ≥ 10", applied to the TRAIN split.
- **The C4 baseline theory matches the acquisition side**: `cnf + bg_clauses` for
  accuracy, `bg` passed separately for semantic entailment — the same shape
  `cross_validation` now uses.

## Unresolved

1. Finding 1 needs a decision: surface `redundant_ne_names`, or accept the loss and say
   so in the accounting note. Not applied — this was a review, and it changes an output
   schema.
2. Finding 2 is a wording-vs-code choice: make the derivation genuinely generic, or drop
   the claim. Both are cheap; they differ in what future readers are told.
3. No fixture in the repo makes Reduce drop an NE, so finding 1 cannot be regression-tested
   from real data — only from a synthetic result like the one used above. That is a fifth
   entry for the non-discriminating register if the fix lands.
