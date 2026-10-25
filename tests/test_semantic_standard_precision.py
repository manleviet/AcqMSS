"""Semantic tier: the standard precision P_std = TP_kb / (TP_kb + FP_kb) is reported beside
the historical precision TP_ct / (TP_ct + FP_kb), which stays unchanged."""
import unittest

from conacq.eval.kb_comparator import (ComparationStrategy, KBComparator,
                                       SemanticStandardPrecision)
from conacq.eval.result_loader import ConGenResultData
from tests.resource_paths import BIAS_PATH, FM_PATH

# QuAcq-active (oracle mode, glucose4) on REAL-FM-7: logically equivalent to the target
# once the root axiom `jplug` (variable 1) is a premise.
QUACQ_ACTIVE_FM7 = ['c23', 'c4', 'c162', 'c16', 'c291', 'c100', 'c161', 'c103', 'c288',
                    'c242', 'c287', 'c165']


class TestSemanticStandardPrecisionArithmetic(unittest.TestCase):
    def test_precision_counts_learned_clauses(self):
        s = SemanticStandardPrecision(n_kb_checked=4, n_kb_entailed=3,
                                      n_ct_checked=10, n_ct_entailed=5)
        self.assertAlmostEqual(s.precision, 0.75)
        self.assertAlmostEqual(s.recall, 0.5)
        self.assertAlmostEqual(s.f1, 2 * 0.75 * 0.5 / 1.25)

    def test_empty_kb_precision_undefined_f1_zero(self):
        s = SemanticStandardPrecision(0, 0, 10, 3)       # bg alone entails 3 Cτ clauses
        self.assertIsNone(s.precision)
        self.assertEqual(s.f1, 0.0)
        self.assertAlmostEqual(s.recall, 0.3)


class TestSemanticStandardPrecisionComparator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)

    def _compare(self, names, bg):
        data = ConGenResultData(kb_constraints=names, n_bias=295, n_kb=len(names),
                                bg_clauses=bg)
        return self.comparator.compare(data, ComparationStrategy.SEMANTIC)

    def test_same_call_counts_and_historical_precision_unchanged(self):
        res = self._compare(QUACQ_ACTIVE_FM7, [])
        std, m = res.standard_precision, res.metrics
        self.assertEqual(std.n_kb_checked - std.n_kb_entailed, m.false_positives)
        self.assertEqual(std.n_ct_entailed, m.true_positives)
        self.assertAlmostEqual(std.recall, m.recall)
        self.assertAlmostEqual(m.recall, 16 / 22)      # submitted contract: root missing
        self.assertAlmostEqual(m.precision, 1.0)
        self.assertAlmostEqual(std.precision, 1.0)

    def test_root_as_background_gives_equivalence(self):
        res = self._compare(QUACQ_ACTIVE_FM7, [[1]])
        self.assertAlmostEqual(res.metrics.recall, 1.0)
        self.assertAlmostEqual(res.standard_precision.precision, 1.0)

    def test_formulas_differ_on_empty_kb(self):
        res = self._compare([], [[1]])
        self.assertEqual(res.metrics.precision, 1.0)      # TP_ct = 1 (root), FP_kb = 0
        self.assertIsNone(res.standard_precision.precision)
        self.assertEqual(res.standard_precision.f1, 0.0)
        self.assertGreater(res.standard_precision.recall, 0.0)   # root unit + child → root

    def test_other_tiers_carry_no_standard_precision(self):
        data = ConGenResultData(kb_constraints=QUACQ_ACTIVE_FM7, n_bias=295, n_kb=12,
                                bg_clauses=[])
        for strategy in (ComparationStrategy.DESCRIPTION, ComparationStrategy.CLAUSE):
            res = self.comparator.compare(data, strategy)
            self.assertIsNone(res.standard_precision)
            self.assertNotIn('standard_precision', res.to_dict())


if __name__ == '__main__':
    unittest.main()
