import logging
from typing import List, Tuple

from .checker import ConsistencyChecker
from .profiler import get_global_profiler, measure_time, count_calls, AbstractProfiler
from .utils import split, diff

class KBDiag:
    """
    Implementation of KBDiag algorithm.
    The algorithm determines a maximal satisfiable subset MSS (Γ) of C U B U -TV U TC.
    """

    def __init__(self, checker: ConsistencyChecker, m: int = 1, profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.m = m
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

    @measure_time('kbdiag_runtime')
    @count_calls('kbdiag_calls')
    def find_diagnosis(self, set_c: List, set_b: List,
                       set_tv: List, set_tc: List) -> Tuple[List, List]:
        """
        Activate KBDiag algorithm if there exists at least one positive test case,
        which induces an inconsistency in C U B. Otherwise, it returns an empty set.

        // Func KBDiag(C, B, Tν, Tπ, λ) : ∆
        // negTν ← /\ tv ∈ Tν {¬tν}
        // T′π ← TESTC(negTν, Tπ)
        // if T′π = ∅ then
        //     T′π ← TESTC(C ∪ B ∪ negTν, Tπ)
        //     if (T′π  != ∅) then
        //          return(C − MSSDIRECT(∅, C, B ∪ negTν, T′π, λ))
        //     else
        //          return Φ
        // else
        //     return Φ
        :param set_c: a consideration set of constraints
        :param set_b: a background knowledge
        :param set_tc: a set of positive test cases
        :param set_tv: a set of negative test cases
        :return: a diagnosis or an empty set
        """
        logging.debug('kbDiag [C=%s, B=%s, TV=%s, TC=%s]', set_c, set_b, set_tv, set_tc)
        # print(f'fastDiag [C={C}, B={B}]')

        # negTν ← /\ tv ∈ Tν {¬tν}

        # T′π ← TESTC(negTν, Tπ)
        set_tcp = []
        if len(set_tcp) != 0:
            logging.debug('inconsistent test cases - return Φ')
            # print('return Φ')
            return [], []

        # T′π ← TESTC(C ∪ B ∪ negTν, Tπ)
        # TODO - fix
        set_tcp = self.checker.is_consistent_test_cases(set_b + set_c, set_tc, False)
        if len(set_c) == 0 or len(set_tcp) == 0:
            logging.debug('all test cases satisfied - return Φ')
            # print('return Φ')
            return [], []

        # return C \ mssDirect(Φ, C, B, T'π)
        # return(C \ mssDirect(∅, C, B ∪ negTν, T′π, λ))
        # TODO - fix
        mss = self._mssDirect([], set_c, set_b, set_tcp)
        diag = diff(set_c, mss)

        logging.debug('return %s', diag)
        # print(f'return {diag}')
        return set_tcp, diag

    @count_calls('mssDirect_calls')
    @measure_time('mssDirect_runtime')
    def _mssDirect(self, delta: List, set_c: List, set_b: List, set_tc: List) -> List:
        """
        The implementation of KBDiag algorithm.
        The algorithm determines a maximal satisfiable subset MSS (Γ) of C U B U TC.
        Tv is the set of negative test cases - ignored from this evaluation

        // Func MSSDirect(δ, C, B, Tv, Tπ) : Γ
        // T'π <- Tπ
        // if Δ != Φ then
        //    T'π <- TestC(B U C, Tπ)
        //    if T'π = Φ then return C;
        // if |C| <= m return Φ;
        // k = n/2;
        // C1 = {c1..ck}; C2 = {ck+1..cn};
        // Γ2 = MSSDirect(δ=C1, C1, B, T'π);
        // Γ1 = MSSDirect(δ=C1-Γ2, C2, B U Γ2, T'π);
        // return Γ1 ∪ Γ2;
        :param delta: check to skip redundant consistency checks
        :param set_c: a consideration set of constraints
        :param set_b: a background knowledge
        :param set_tc: a set of test cases
        :return: a maximal satisfiable subset MSS of C U B U TC
        """
        logging.debug('>>> MSSDirect [δ=%s, C=%s, B=%s, TC=%s]', delta, set_c, set_b, set_tc)

        # T'π <- Tπ
        set_tcp = set_tc.copy()

        # if δ != Φ and TestC(B U C, Tπ) return C;
        if len(delta) != 0:
            set_tcp = self.checker.is_consistent_test_cases(set_b + set_c, set_tc, False)

            if len(set_tcp) == 0:
                logging.debug('<<< return %s', set_c)
                return set_c

        # if singleton(C) return Φ;
        if len(set_c) <= self.m:
            logging.debug('<<< return Φ')
            return []

        # C1 = {c1..ck}; C2 = {ck+1..cn};
        set_c1, set_c2 = split(set_c)

        # Γ1 = MSSDirect(δ=C1, C1, B, T'π);
        delta1 = self._mssDirect(set_c1, set_c1, set_b, set_tcp)
        # Γ2 = MSSDirect(δ=C1-Γ1, C2, B U Γ1, T'π);
        c1_without_delta1 = diff(set_c1, delta1)
        delta2 = self._mssDirect(c1_without_delta1, set_c2, set_b + delta1, set_tcp)

        logging.debug('<<< return [Γ1=%s ∪ Γ2=%s]', delta1, delta2)

        # return Γ1 ∪ Γ2
        return delta1 + delta2