"""
ConGen Constraint Acquisition Algorithm.

Orchestrates AcqMSS and REDUCE to acquire a knowledge base from
positive examples and pre-computed NE constraints.

NE generation is performed by callers before invoking ConGen.
ConGen receives pre-computed NE via task.set_ne.

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
from .task_preparation import ConGenTask
from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class CONGENResult:
    """Result of ConGen constraint acquisition."""
    kb_constraints: List[str]  # Names of acquired constraints
    kb_assumption_ids: List[int]  # Assumption IDs of acquired constraints
    redundant_constraints: List[str]  # Names of redundant constraints removed
    n_bias: int  # Number of bias constraints
    n_mss: int  # Size of MSS before REDUCE
    n_kb: int  # Size of final KB
    bg_clauses: List[List[int]] = field(default_factory=list)  # BG clauses (e.g., [[1]])
    metadata: Dict = field(default_factory=dict)


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
        self.result: Optional[CONGENResult] = None

    @measure_time('congen_runtime')
    @count_calls('congen_calls')
    def acquire(self, task: ConGenTask) -> CONGENResult:
        """
        Acquire knowledge base from prepared task.

        NE must be pre-computed by caller and stored in task.set_ne.
        Implements Paper Algorithm 1 steps 2-9:
        2. if IsConsistent(E⁺, NE, BG) then B′ ← AcqMSS(...)
        3. return REDUCE(B′, NE, BG)

        Args:
            task: ConGenTask with set_c, set_b, set_tc, set_ne populated

        Returns:
            CONGENResult with acquired KB
        """
        # NE is pre-computed by caller and stored in task.set_ne
        set_ne = task.set_ne
        logging.debug('>>> ConGen [B=%d, NE=%d, E+=%d, BG=%d]',
                      len(task.set_c), len(set_ne),
                      len(task.set_tc), len(task.set_b))

        # Step 3: if IsConsistent(E⁺, NE, BG) then
        inconsistent = self.checker.is_consistent_test_cases(
            set_ne + task.set_b,  # NE ∪ BG
            task.set_tc,  # E+
            stop_at_first_violation=True
        )
        self.profiler.increment("paper_consistency_checks")

        if len(inconsistent) > 0:
            logging.debug('<<< ConGen return Φ (E+ inconsistent with NE ∪ BG)')
            bg_clauses = [[lit] for lit in task.set_b]

            self.result = CONGENResult(
                kb_constraints=[],
                kb_assumption_ids=[],
                redundant_constraints=[],
                n_bias=len(task.set_c),
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
            set_b=task.set_c,
            set_ne=set_ne,
            set_e_pos=task.set_tc,
            set_bg=task.set_b
        )
        logging.debug('AcqMSS: MSS size = %d', len(b_prime))

        # Step 9: return (REDUCE(B′, NE, BG))
        reduce = Reduce(self.checker, self.profiler)
        redundant, kb = reduce.reduce(
            set_b_prime=b_prime,
            set_ne=set_ne,
            set_bg=task.set_b,
            neg_map=task.neg_c_map
        )
        logging.debug('REDUCE: %d redundant, %d in final KB', len(redundant), len(kb))

        # Map back to constraint names
        kb_names = [task.get_constraint_name(a) for a in kb]
        redundant_names = [task.get_constraint_name(a) for a in redundant]

        # Extract BG clauses (unified: set_b contains assumption IDs)
        bg_clauses = [[lit] for lit in task.set_b]

        self.result = CONGENResult(
            kb_constraints=kb_names,
            kb_assumption_ids=kb,
            redundant_constraints=redundant_names,
            n_bias=len(task.set_c),
            n_mss=len(b_prime),
            n_kb=len(kb),
            bg_clauses=bg_clauses,
            metadata={
                'n_ne': len(set_ne),
                'n_e_pos': len(task.set_tc),
            }
        )

        logging.debug('<<< ConGen return KB=%d', len(kb))
        return self.result

    def save_result(self, filepath: str):
        """Save result to JSON file."""
        if self.result is None:
            raise ValueError("No result to save. Run acquire() first.")

        data = {
            'kb_constraints': self.result.kb_constraints,
            'redundant_constraints': self.result.redundant_constraints,
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
