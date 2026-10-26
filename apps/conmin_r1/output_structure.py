"""Output structure (AAAI-27 rebuttal analysis, 2026-10-26).

Classifies every constraint of the persisted ConMin k=1 theories (data/results_conmin_r1/kbs/,
condition "C∪S", k=1, 2-COV excluded) against the target UVL: TARGET (same relation), operator
neighbour (same parent/children, stronger or weaker operator), or cross-tree. Cross-tree
constraints are split into target / spurious by a second pass (see cover_structure.md §4).
Description-level only: a "spurious" cross-tree constraint may still be entailed by the target
(sibling excludes, child-requires-parent); the semantic tier decides that. Read-only; derived data.
Run from the repo root:  python3 apps/conmin_r1/output_structure.py > data/results_conmin_r1/output_structure.txt
"""
import json,glob,collections,sys
sys.path.insert(0,'apps/conmin_r1')
exec(open('apps/conmin_r1/cover_structure.py').read().split('for kb in')[0])  # reuse parse_uvl, in_target (read-only)
def classify(c,rel,cross,depth):
    op=c['operator']; par=c.get('parent'); kids=set(c.get('children') or [])
    if op in ('requires','excludes'):
        return 'cross-tree (not in target)'
    if in_target(c,rel,cross): return 'TARGET'
    # relations with same parent
    same_par=[(g,p,ch) for (g,p,ch) in rel if p==par]
    kids_rel={ch for (g,p,ch) in same_par}
    if op in ('mandatory','optional'):
        ch=next(iter(kids))
        tops=[g for (g,p,c2) in same_par if c2==ch]
        if tops: return f'operator-neighbour ({op} vs target {tops[0]})'
        return 'wrong parent/child link'
    if op in ('alternative','or'):
        tgt_groups={g for (g,p,ch) in same_par if g in ('alternative','or') and ch in kids}
        tgt_kids={ch for (g,p,ch) in same_par if g in ('alternative','or')}
        if kids==tgt_kids and tgt_groups: return f'operator-neighbour ({op} vs target {next(iter(tgt_groups))})'
        if kids<=tgt_kids and tgt_groups: return f'group over subset of target group ({op})'
        if kids & kids_rel: return f'group over mixed children ({op})'
        return 'wrong parent/children'
    return 'other'
for kb in ['REAL-FM-7','fqa','arcade-game','REAL-FM-4']:
    depth,parent,rel,cross=parse_uvl(f'data/fms/{kb}.uvl')
    bias={c['id']:c for c in json.load(open(f'data/bias/{kb}-bias.json'))['constraints']}
    cnt=collections.Counter(); nfold=0; ntot=0
    for f in sorted(glob.glob(f'data/results_conmin_r1/kbs/{kb}/*fold*.json')):
        if '2cov' in f: continue
        for e in json.load(open(f)):
            if e['condition']=='C∪S' and e['k']==1:
                nfold+=1
                for n in e['names']:
                    cnt[classify(bias[n],rel,cross,depth)]+=1; ntot+=1
    print(f'\n== {kb}: ConMin k=1, {nfold} folds (excl. 2-COV), {ntot} constraints, {ntot/nfold:.1f} per fold')
    for k,v in cnt.most_common(): print(f'  {v:5d}  {v/ntot:5.1%}  {k}')
