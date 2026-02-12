"""
CONGEN Constraint Acquisition Algorithm.

Main algorithm that orchestrates GenerateNE, ACQMSS and REDUCE to
acquire a knowledge base from positive and negative examples.

Reference: Paper Algorithm 1
    CONGEN(E+, E-, B, BG) → KB
    1: NE ← GENERATENE(E⁻)
    2: B′ ← ∅
    3: if IsConsistent(E⁺, NE, BG) then
    4:   B′ ← ACQMSS(∅, B, NE, E⁺, BG)
    5: else
    6:   print "examples inconsistent"
    7:   return (∅)
    8: end if
    9: return (REDUCE(B′, NE, BG))

Pattern follows KBDiag from the explanation package.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field

from .acqmss import ACQMSS
from .reduce import Reduce
from .generate_ne import GenerateNE, NEResult
from .task import CONGENTask, IncrementalCONGENTask, NonIncrementalCONGENTask
from explanation.operations.algorithms.checker import (
    ConsistencyChecker,
    IncrementalPySATChecker
)
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class CONGENResult:
    """Result of CONGEN constraint acquisition."""
    kb_constraints: List[str]  # Names of acquired constraints
    kb_assumption_ids: List[int]  # Assumption IDs of acquired constraints
    redundant_constraints: List[str]  # Names of redundant constraints removed
    n_bias: int  # Number of bias constraints
    n_mss: int  # Size of MSS before REDUCE
    n_kb: int  # Size of final KB
    bg_clauses: List[List[int]] = field(default_factory=list)  # BG clauses (e.g., [[1]])
    metadata: Dict = field(default_factory=dict)


class CONGEN:
    """
    CONGEN constraint acquisition algorithm.

    Pattern follows KBDiag from explanation module.

    Algorithm (Paper Algorithm 1):
        CONGEN(E+, E-, B, BG) → KB
        1: NE ← GENERATENE(E⁻)
        2: B′ ← ∅
        3: if IsConsistent(E⁺, NE, BG) then
        4:   B′ ← ACQMSS(∅, B, NE, E⁺, BG)
        5: else
        6:   print "examples inconsistent"
        7:   return (∅)
        8: end if
        9: return (REDUCE(B′, NE, BG))

    Task fields:
    - set_c = Bias (B)
    - set_b = Background (BG)
    - set_tc = Positive examples (E+)
    - e_neg_literals = E⁻ literals for GenerateNE
    - set_neg_tv = NE (created by GenerateNE in this method)
    - neg_c_map = Negation map for REDUCE

    Args:
        checker: ConsistencyChecker instance for SAT solving
        profiler_instance: Optional profiler for metrics tracking
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.result: Optional[CONGENResult] = None
        self._is_incremental = isinstance(checker, IncrementalPySATChecker)

    @measure_time('congen_runtime')
    @count_calls('congen_calls')
    def acquire(self, task: CONGENTask) -> CONGENResult:
        """
        Acquire knowledge base from prepared task.

        Implements Paper Algorithm 1 exactly:
        1. NE ← GENERATENE(E⁻)
        2. if IsConsistent(E⁺, NE, BG) then B′ ← ACQMSS(...)
        3. return REDUCE(B′, NE, BG)

        Args:
            task: CONGENTask with:
                - set_c: Bias constraints (B)
                - set_b: Background knowledge (BG)
                - set_tc: Positive examples (E+)
                - e_neg_literals: E⁻ literals for GenerateNE

        Returns:
            CONGENResult with acquired KB
        """
        logging.debug('>>> CONGEN [B=%d, E⁻=%d, E+=%d, BG=%d]',
                      len(task.set_c), len(task.e_neg_literals),
                      len(task.set_tc), len(task.set_b))

        # Step 1: NE ← GENERATENE(E⁻)
        # Uses QuickXPlain to find minimal conflict sets
        generate_ne = GenerateNE(self.checker, self.profiler)
        ne_result = generate_ne.generate(
            set_e_neg=task.e_neg_literals,
            set_bg=task.set_b,
            start_assumption_id=task.next_assumption_id
        )

        # Get NE in appropriate format
        if self._is_incremental:
            set_ne = ne_result.assumption_ids
            # Update task mappings for result formatting
            for ne_id in ne_result.assumption_ids:
                task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"
        else:
            set_ne = ne_result.clause_lists
            # Update task mappings for non-incremental mode
            for ne_clauses in ne_result.clause_lists:
                ne_key = tuple(tuple(c) for c in ne_clauses)
                task.clauses_to_name[ne_key] = f"ne_{ne_key}"

        # Merge NE neg_map into task for REDUCE
        task.neg_c_map.update(ne_result.neg_map)

        logging.debug('GENERATENE: %d NE constraints', len(set_ne))

        # Step 3: if IsConsistent(E⁺, NE, BG) then
        # Check if each E+ is consistent with NE ∪ BG
        inconsistent = self.checker.is_consistent_test_cases(
            set_ne + task.set_b,  # NE ∪ BG
            task.set_tc,  # E+
            stop_at_first_violation=True
        )
        self.profiler.increment("paper_consistency_checks")

        if len(inconsistent) > 0:
            # Step 6-7: print "examples inconsistent", return (∅)
            logging.debug('<<< CONGEN return Φ (E+ inconsistent with NE ∪ BG)')
            # Extract BG clauses even for error path
            bg = []
            if self._is_incremental:
                bg = [[lit] for lit in task.set_b]
            else:
                for clause_list in task.set_b:
                    for clause in clause_list:
                        bg.append(clause)

            self.result = CONGENResult(
                kb_constraints=[],
                kb_assumption_ids=[],
                redundant_constraints=[],
                n_bias=len(task.set_c),
                n_mss=0,
                n_kb=0,
                bg_clauses=bg,
                metadata={'error': 'E+ inconsistent with NE ∪ BG'}
            )
            return self.result

        # Step 4: B′ ← ACQMSS(∅, B, NE, E⁺, BG)
        acqmss = ACQMSS(self.checker, m=1, profiler_instance=self.profiler)
        b_prime = acqmss.find_mss(
            delta=[],
            set_b=task.set_c,    # Bias B
            set_ne=set_ne,       # NE
            set_e_pos=task.set_tc,  # E+
            set_bg=task.set_b    # BG
        )
        logging.debug('ACQMSS: MSS size = %d', len(b_prime))

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

        # Extract BG clauses for evaluation
        bg_clauses: List[List[int]] = []
        if self._is_incremental:
            # Incremental: set_b contains assumption IDs (ints), each is a unit clause
            bg_clauses = [[lit] for lit in task.set_b]
        else:
            # Non-incremental: set_b contains clause lists (List[List[List[int]]])
            for clause_list in task.set_b:
                for clause in clause_list:
                    bg_clauses.append(clause)

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
                'n_e_neg': len(task.e_neg_literals),
            }
        )

        logging.debug('<<< CONGEN return KB=%d', len(kb))
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
