"""Per KB: does the bias mention the root var? |CT|, R+ = CT clauses containing +root,
is the root unit in CT (precision side), and are any R+ antecedent features dead in CT."""
from pathlib import Path
from pysat.solvers import Solver
from conacq.oracle import FMOracle
from conacq.oracle.ground_truth import GroundTruthData
from conacq.bias import BiasIO

KBS = ["REAL-FM-7", "fqa", "arcade-game", "REAL-FM-4", "busybox-1.18.0"]
for kb in KBS:
    fm, bias_p = f'data/fms/{kb}.uvl', f'data/bias/{kb}-bias.json'
    gt = GroundTruthData.from_uvl(Path(fm))
    o = FMOracle(fm, solver_name='glucose4'); root = [list(c) for c in o.oracle_data.get_root_clauses()]; o.cleanup()
    assert len(root) == 1 and len(root[0]) == 1, root
    r = root[0][0]
    bias = BiasIO.load_from_json(bias_p)
    bias_cl = bias.get_all_clause_tuples()
    n_bias_root = sum(1 for c in bias_cl if r in c or -r in c)
    ct = gt.clause_set
    rplus = [c for c in ct if r in c]
    rminus = [c for c in ct if -r in c]
    # dead antecedents in CT: for R+ clause (-x..., r), is CT ∧ x's SAT?
    dead = 0
    with Solver(name='glucose4', bootstrap_with=[list(c) for c in ct]) as s:
        for c in rplus:
            if len(c) > 1 and not s.solve(assumptions=[-l for l in c if l != r]): dead += 1
    print(f'{kb:15s} root_var={r:4d} |CT|={len(ct):4d} root_unit_in_CT={(r,) in ct} '
          f'|R+|={len(rplus):3d} |R-|={len(rminus):3d} bias_clauses_mentioning_root={n_bias_root} '
          f'dead_R+_antecedents_in_CT={dead}')
