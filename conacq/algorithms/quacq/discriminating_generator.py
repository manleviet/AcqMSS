"""
DiscriminatingGenerator: Paper Algorithm 3 line 5.

Generates discriminating examples from C_L[Y] (learned KB restricted to scope)
+ BG clauses, NOT from FM clauses (ground truth).

Uses ConsistencyChecker via DI pattern (like FindScope/FindC).
"""

from typing import Dict, List, Optional, Set

from explanation.operations.algorithms.checker import ConsistencyChecker


class DiscriminatingGenerator:
    """Generate discriminating examples from learned KB restricted to scope.

    Paper Algorithm 3 line 5: choose e' in sol(C_L[Y]) s.t. e' |= c_i, e' |/= c_j.
    SAT formula: BG + C_L[Y] + c_i + neg(c_j).

    Args:
        checker: ConsistencyChecker with full KB loaded
        model: QuAcqModel for constraint variable lookup and config conversion
        root_assumption: Root BG assumption ID
    """

    def __init__(self, checker: ConsistencyChecker, model, root_assumption: int) -> None:
        self.checker = checker
        self.model = model
        self.root_assumption = root_assumption

    def generate(self, c_i: int, c_j: int,
                 learned_kb: List[int], scope: Set[str]) -> Optional[Dict[str, bool]]:
        """Find e' s.t. e' in sol(BG + C_L[Y]) and e' |= c_i and e' |/= c_j.

        Args:
            c_i: Constraint ID that e' must satisfy
            c_j: Constraint ID that e' must violate
            learned_kb: Currently learned constraint IDs
            scope: Variable scope Y (feature names)

        Returns:
            Config dict if SAT, None if UNSAT
        """
        # C_L[Y]: learned constraints in scope
        cl_y = [c_id for c_id in learned_kb
                if self.model.get_constraint_vars(c_id).issubset(scope)]

        # Get negated assumption for c_j
        negation_map = self.model.get_negation_map()
        neg_j = negation_map.get(c_j)
        if neg_j is None:
            return None

        # SAT: BG + C_L[Y] + c_i + neg(c_j)
        set_c = [self.root_assumption] + cl_y + [c_i, neg_j]

        if self.checker.is_consistent(set_c):
            return self.model.model_to_config(self.checker.get_model())
        return None
