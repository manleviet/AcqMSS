"""Score one ConMin passive-strategy slice (A / C / C∪S) or a QuAcq KB.

§9a: the three passive strategies are slices of ONE ConMin run; each is resolved to
its FM/bias names + clauses and scored INDEPENDENTLY. §9d metrics, reusing the existing
eval primitives (no new metric code):

- P/R/F1 in all three comparison strategies (description / clause / semantic) — these
  range over the FM/bias-constraint VOCABULARY (names), so ¬e⁻ and root are excluded
  (they are not bias constraints, so ``resolve_slice`` drops them).
- exact-equivalence + predictive accuracy — these range over the DELIVERED THEORY
  (slice clauses ∪ ¬e⁻ fallbacks ∪ root), the Cowork B1 decision.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .kb_comparator import ComparationStrategy, KBComparator
from .accuracy import AccuracyCalculator
from .semantic_equivalence import SemanticEquivalenceChecker
from .result_loader import ConGenResultData

_STRATEGIES = (
    (ComparationStrategy.DESCRIPTION, 'desc'),
    (ComparationStrategy.CLAUSE, 'clause'),
    (ComparationStrategy.SEMANTIC, 'sem'),
)


def score_named_kb(
        names: Sequence[str],
        clauses: Sequence[Sequence[int]],
        *,
        comparator: KBComparator,
        ground_truth,
        variables: Dict[str, int],
        test_pos: List[Dict[str, bool]],
        test_neg: List[Dict[str, bool]],
        bg_clauses: Sequence[Sequence[int]],
        n_bias: int,
        solver_name: str = 'glucose4',
        fallback_clauses: Sequence[Sequence[int]] = (),
) -> Dict[str, float]:
    """Score one KB (a ConMin slice or a QuAcq result) already resolved to
    ``names`` + ``clauses``.

    ``names`` drive the vocabulary-space P/R/F1 (KBComparator resolves clauses from the
    names via the bias). ``clauses`` + ``fallback_clauses`` + ``bg_clauses`` form the
    delivered theory scored for exact-equivalence + accuracy (B1). Returns a flat dict
    of metric columns for the long/tidy CSV.
    """
    out: Dict[str, float] = {'size': len(names)}

    # Vocabulary-space P/R/F1 in all three strategies (names only; ¬e⁻/root excluded).
    # CRITICAL: bg_clauses MUST be [] here — the CLAUSE/SEMANTIC strategies union
    # result.bg_clauses into the compared KB, so passing root would count it as a
    # learned constraint and inflate clause/semantic F1 (the contract forbids it). Root
    # belongs only in the delivered theory below (exact-equiv + accuracy).
    result_data = ConGenResultData(
        kb_constraints=list(names), n_bias=n_bias, n_kb=len(names), bg_clauses=[])
    for strategy, prefix in _STRATEGIES:
        m = comparator.compare(result_data, strategy).metrics
        out[f'{prefix}_p'] = m.precision
        out[f'{prefix}_r'] = m.recall
        out[f'{prefix}_f1'] = m.f1_score

    # Delivered theory (B1): slice ∪ ¬e⁻ fallbacks ∪ root.
    theory = [list(c) for c in clauses] + [list(c) for c in fallback_clauses] \
        + [list(c) for c in bg_clauses]
    ct_clauses = [list(c) for c in ground_truth.clause_set]

    out['exact_equiv'] = int(SemanticEquivalenceChecker(
        theory, ct_clauses, bg_clauses, solver_name).check_equivalence().is_equivalent)

    with AccuracyCalculator(theory, variables, solver_name) as acc:
        am = acc.calculate(test_pos, test_neg).metrics
    out['accuracy'] = am.accuracy
    out['tp'], out['tn'] = am.true_positives, am.true_negatives
    out['fp'], out['fn'] = am.false_positives, am.false_negatives
    # Specificity = TN/(TN+FP): the negatives-side signal accuracy hides when the test
    # fold is positive-heavy (threat-to-validity flag, R1-Q1). None when no negatives.
    denom = am.true_negatives + am.false_positives
    out['specificity'] = (am.true_negatives / denom) if denom > 0 else None
    return out
