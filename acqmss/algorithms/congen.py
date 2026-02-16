"""
ConGen Constraint Acquisition Algorithm.

Orchestrates AcqMSS and REDUCE to acquire a knowledge base from
positive examples and pre-computed NE constraints.

NE generation is performed by callers before invoking ConGen.
ConGen receives pre-computed NE via task.set_neg_tv.

Reference: Paper Algorithm 1 (steps 2-9, NE pre-computed)
    ConGen(E+, NE, B, BG) → KB
    2: B′ ← ∅
    3: if IsConsistent(E⁺, NE, BG) then
    4:   B′ ← AcqMSS(∅, B, NE, E⁺, BG)
    5: else
    6:   print "examples inconsistent"
    7:   return (∅)
    8: end if
    9: return (REDUCE(B′, NE, BG))

Mode-agnostic: works identically regardless of checker type.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from .acqmss import AcqMSS
from .reduce import Reduce
from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class ConGenResult:
    """Result of ConGen constraint acquisition."""
    kb_assumption_ids: List[int]  # Assumption IDs of acquired constraints
    redundant_ids: List[int]  # Assumption IDs of redundant constraints removed
    n_bias: int  # Number of bias constraints
    n_mss: int  # Size of MSS before Reduce
    n_kb: int  # Size of final KB
    bg_clauses: List[List[int]] = field(default_factory=list)  # BG clauses (e.g., [[1]])
    metadata: Dict = field(default_factory=dict)


def resolve_congen_names(result: ConGenResult, provider) -> Dict[str, List[str]]:
    """Resolve assumption IDs to human-readable names.

    Args:
        result: CONGENResult with raw assumption IDs
        provider: Object with get_description(assumption_id) method

    Returns:
        Dict with 'kb' and 'redundant' name lists
    """
    return {
        'kb': [provider.get_description(a) for a in result.kb_assumption_ids],
        'redundant': [provider.get_description(a) for a in result.redundant_ids],
    }


class ConGen:
    """
    ConGen constraint acquisition algorithm.

    Mode-agnostic: all data is assumption-based (List[int]).
    The checker implementation determines solver lifecycle.
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.result: Optional[ConGenResult] = None

    @measure_time('congen_runtime')
    @count_calls('congen_calls')
    def acquire(
            self,
            set_b: List[int],
            set_bg: List[int],
            set_tc: List[int],
            set_neg_tv: Optional[List[int]] = None,
            negation_map: Optional[Dict[int, int]] = None,
    ) -> ConGenResult:
        """Acquire knowledge base from bias constraints.

        Paper Algorithm 1 (steps 2-9, NE pre-computed):
        2. if IsConsistent(E+, NE, BG) then B' <- AcqMSS(...)
        3. return REDUCE(B', NE, BG)

        Args:
            set_b: Bias constraint assumption IDs (B)
            set_bg: Background knowledge assumption IDs (BG)
            set_tc: Positive example assumption IDs (E+)
            set_neg_tv: Negated example assumption IDs (NE)
            negation_map: Mapping assumption ID -> negated ID (for REDUCE)

        Returns:
            CONGENResult with acquired KB
        """
        set_neg_tv = set_neg_tv or []
        negation_map = negation_map or {}

        logging.debug('>>> ConGen [B=%d, NE=%d, E+=%d, BG=%d]',
                      len(set_b), len(set_neg_tv), len(set_tc), len(set_bg))

        # Step 3: if IsConsistent(E⁺, NE, BG) then
        inconsistent = self.checker.is_consistent_test_cases(
            set_neg_tv + set_bg,  # NE ∪ BG
            set_tc,           # E+
            stop_at_first_violation=True
        )
        self.profiler.increment("paper_consistency_checks")

        if len(inconsistent) > 0:
            logging.debug('<<< ConGen return Phi (E+ inconsistent with NE ∪ BG)')
            bg_clauses = [[lit] for lit in set_bg]
            self.result = ConGenResult(
                kb_assumption_ids=[],
                redundant_ids=[],
                n_bias=len(set_b),
                n_mss=0,
                n_kb=0,
                bg_clauses=bg_clauses,
                metadata={'error': 'E+ inconsistent with NE ∪ BG'}
            )
            return self.result

        # Step 4: B′ ← AcqMSS(∅, B, NE, E⁺, BG)
        acqmss = AcqMSS(self.checker, m=1, profiler_instance=self.profiler)
        b_prime = acqmss.find_mss(
            delta=[],
            set_b=set_b,
            set_neg_tv=set_neg_tv,
            set_tc=set_tc,
            set_bg=set_bg
        )
        logging.debug('AcqMSS: MSS size = %d', len(b_prime))

        # Step 9: return Reduce(B′, NE, BG)
        reduce = Reduce(self.checker, self.profiler)
        redundant, kb = reduce.reduce(
            set_b_prime=b_prime,
            set_neg_tv=set_neg_tv,
            set_bg=set_bg,
            negation_map=negation_map
        )
        logging.debug('Reduce: %d redundant, %d in final KB', len(redundant), len(kb))

        bg_clauses = [[lit] for lit in set_bg]

        self.result = ConGenResult(
            kb_assumption_ids=kb,
            redundant_ids=redundant,
            n_bias=len(set_b),
            n_mss=len(b_prime),
            n_kb=len(kb),
            bg_clauses=bg_clauses,
            metadata={
                'n_neg_tv': len(set_neg_tv),
                'n_e_pos': len(set_tc),
            }
        )

        logging.debug('<<< ConGen return KB=%d', len(kb))
        return self.result

    def save_result(self, filepath: str, description_provider=None):
        """Save result to JSON file.

        Args:
            filepath: Output file path
            description_provider: Optional provider to resolve names for output.
                If None, raw assumption IDs are serialized.
        """
        if self.result is None:
            raise ValueError("No result to save. Run acquire() first.")

        if description_provider is not None:
            names = resolve_congen_names(self.result, description_provider)
            kb_output = names['kb']
            redundant_output = names['redundant']
        else:
            kb_output = self.result.kb_assumption_ids
            redundant_output = self.result.redundant_ids

        data = {
            'kb_constraints': kb_output,
            'redundant_constraints': redundant_output,
            'statistics': {
                'n_bias': self.result.n_bias,
                'n_mss': self.result.n_mss,
                'n_kb': self.result.n_kb,
            },
            'bg_clauses': self.result.bg_clauses,
            'metadata': self.result.metadata,
        }

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
