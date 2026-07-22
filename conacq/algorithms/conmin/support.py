"""support⁺ for ConMin (prep layer, solver-free) — design brief §4 (unified, 6 ops).

Definition: ``support(c) = min over c's minimal violations, of [ min over the literals
that violation forces PRESENT, of #{e⁺ selects that literal} ]``. Only present
(selected) triggers count; a trigger never observed ⇒ support 0 ⇒ vacuous ⇒ dropped
(unless the cover forces it in).

On the constraint's CNF this is exactly:

    support(c) = min over clauses cl of ( min over {|lit| : lit<0 in cl} of present[|lit|] )

because a clause is violated when all its literals are false, and a *negative* literal
``¬v`` being false means feature ``v`` is PRESENT — the "must-present" trigger of that
minimal violation. Each clause is one minimal-violation family, so "min over violations"
= "min over clauses". Reproduces the paper table:
requires ``A→B``→``#A``, excludes ``¬(A∧B)``→``min(#A,#B)``,
mandatory/or/alternative ``P⟺…``→``min(#P, minᵢ #Cᵢ)`` (alternative == or).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Mapping, Sequence

if TYPE_CHECKING:
    from explanation.api import DescriptionProvider, TestSuite


def support(clauses: Sequence[Sequence[int]], present: Mapping[int, int]) -> int:
    """support⁺ of a CNF constraint given per-variable positive-selection counts."""
    best = None
    for clause in clauses:
        trigger_vars = [abs(lit) for lit in clause if lit < 0]
        if not trigger_vars:
            continue  # all-positive clause: no must-present trigger (not in FM bias)
        clause_support = min(present.get(v, 0) for v in trigger_vars)
        best = clause_support if best is None else min(best, clause_support)
    return best if best is not None else 0


def build_present_counts(
        name_to_id: Mapping[str, int],
        positive_testsuite: "TestSuite",
) -> Dict[int, int]:
    """``present[var]`` = #{e⁺ that select the feature with that var (value True)}."""
    present: Dict[int, int] = {}
    for testcase in positive_testsuite.testcases:
        selected = {name_to_id[a.feature] for a in testcase.assignments
                    if a.value and a.feature in name_to_id}
        for var in selected:
            present[var] = present.get(var, 0) + 1
    return present


def build_support_count(
        constraint_aids: Sequence[int],
        describe: "DescriptionProvider",
        constraint_map: Mapping[str, List[List[int]]],
        name_to_id: Mapping[str, int],
        positive_testsuite: "TestSuite",
) -> Dict[int, int]:
    """support⁺ per bias-constraint assumption id, over the whole positive set.

    Structural + solver-free. Fails loud if an aid does not resolve to a bias
    constraint (never a silent support-0 that would drop a constraint from S).
    """
    present = build_present_counts(name_to_id, positive_testsuite)
    support_count: Dict[int, int] = {}
    for aid in constraint_aids:
        name = describe.get_description(aid)
        if name not in constraint_map:
            raise KeyError(
                f"support: assumption {aid} -> '{name}' is not a bias constraint")
        support_count[aid] = support(constraint_map[name], present)
    return support_count
