---
name: revertible-probe-hook-repro-gap
description: Committed fairness/measurement probe scripts reference an env-gated quacq.py global whose hook is reverted — drop numbers aren't reproducible from the repo alone
metadata:
  type: project
---

The ConMin/QuAcq fairness measurement workflow uses **revertible env-gated instrumentation**: a
temporary hook in `conacq/algorithms/quacq/quacq.py` appends to a module global
`_FAIRNESS_PROBE` (band-aid drops, final KB), and a scratch probe script sets that global then
reads it. The hook is reverted after measuring (leaves tree clean), but the **probe script stays**
(e.g. shipped `scratchpad/fairness_probe.py`).

**Why:** guardrails require read-only + revertible instrumentation; the append-only hook is
control-flow-inert so it doesn't perturb results (verified: instrumented run == clean run,
342 q / |KB|=10 on REAL-FM-7).

**How to apply:** when asked to reproduce a report's band-aid **drop-classification** numbers
(N drops = X true + Y unlearnable, net-missing count), the committed repo **cannot** regenerate
them — `grep _FAIRNESS_PROBE conacq/` is empty and `hasattr(quacq,'_FAIRNESS_PROBE')` is False.
You must re-add the three append hooks (band-aid drop at the `tested_c_id` pop; empty-scope
append; `list(kb)` after reduce), run, then revert (Edit-based revert if `.git/index.lock` blocks
`git checkout` — the scout-block hook forbids referencing `.git` paths). Headline P/R/F1 numbers
DON'T need the hook (they come from `score_named_kb` on the runner result). Related:
[[golden-recorded-from-old-code]].
