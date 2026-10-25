"""Step 1: REAL-FM-7 QuAcq-active — semantic tier with bg=[] (shipped) vs bg=root."""
from pathlib import Path
from conacq.eval.conmin_cv_evaluator import _learn_quacq_active
from conacq.eval.semantic_equivalence import SemanticEquivalenceChecker
from conacq.oracle.ground_truth import GroundTruthData
from conacq.oracle import FMOracle  # noqa
from conacq.bias import BiasIO

FM, BIAS = 'data/fms/REAL-FM-7.uvl', 'data/bias/REAL-FM-7-bias.json'
gt = GroundTruthData.from_uvl(Path(FM))
inv = {v: k for k, v in gt.feature_map.items()}
fmt = lambda c: ' ∨ '.join(('¬' if l < 0 else '') + inv.get(abs(l), str(abs(l))) for l in c)

oracle = FMOracle(FM, solver_name='glucose4')
root = [list(c) for c in oracle.oracle_data.get_root_clauses()]
oracle.cleanup()
print('root clauses:', [fmt(c) for c in root])
print('CT clauses (%d), clause_set (%d):' % (len(gt.clauses), len(gt.clause_set)))
for c in gt.clauses: print('   ', fmt(c))

res = _learn_quacq_active(BIAS, FM, 'glucose4', True, 5000, 400)
print('QuAcq-active KB size', len(res.kb_constraints), res.convergence_reason, 'queries', res.n_queries)
bias = BiasIO.load_from_json(BIAS)
kb = [list(cl) for cid in res.kb_constraints if bias.has_constraint(cid) for cl in bias.get_clauses(cid)]
for cid in res.kb_constraints: print('   KB:', cid)
ct = [list(c) for c in gt.clauses]
for label, bg in (('shipped bg=[]', []), ('bg=root', root)):
    r = SemanticEquivalenceChecker(kb, ct, bg).check_equivalence()
    print(f'\n[{label}] unentailed_ct={len(r.unentailed_ct)}/{r.n_ct_checked}  unentailed_kb={len(r.unentailed_kb)}/{r.n_kb_checked}')
    for c in r.unentailed_ct: print('   CT not entailed:', fmt(c), c)
    for c in r.unentailed_kb: print('   KB not entailed:', fmt(c), c)
# exact-equiv path, for comparison
theory = kb + root
r = SemanticEquivalenceChecker(theory, [list(c) for c in gt.clause_set], root).check_equivalence()
print('\nexact-equiv path (theory=kb+root, bg=root): equivalent =', r.is_equivalent)
# precision with root added to CT side
r = SemanticEquivalenceChecker(kb, ct + root, root).check_equivalence()
print('precision vs Cτ∪root: unentailed_kb =', len(r.unentailed_kb))
