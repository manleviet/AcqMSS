"""Cover structure (AAAI-27 rebuttal analysis, 2026-10-26).

For every persisted fold (data/results_conmin_r1/kbs/<kb>/*fold*.json, condition "C") list
each cover element with its operator, the hierarchy depth of its parent feature (from the
target UVL), and whether the same relation exists in the target. Read-only; derived data.
Run from the repo root:  python3 apps/conmin_r1/cover_structure.py > data/results_conmin_r1/cover_structure.txt
Known limit: `in_target` is None for cross-tree constraints (requires/excludes) — not checked.
"""
import json,glob,collections,re,sys
def parse_uvl(path):
    lines=open(path).read().split('\n')
    i=0
    while not lines[i].strip().startswith('features'): i+=1
    i+=1
    depth={}; parent={}; stack=[]  # stack of (indent, name)
    groups={}  # feature -> current group type being read
    rel=set()  # (op, parent, child)
    cross=[]
    while i<len(lines) and not lines[i].strip().startswith('constraints'):
        ln=lines[i]; i+=1
        if not ln.strip(): continue
        ind=len(ln)-len(ln.lstrip('\t '))
        tok=ln.strip()
        while stack and stack[-1][0]>=ind: stack.pop()
        if tok in ('mandatory','optional','alternative','or'):
            stack.append((ind,'@'+tok)); continue
        name=tok.split()[0].strip('"')
        # find nearest feature ancestor and group
        grp=None; par=None
        for d,n in reversed(stack):
            if n.startswith('@') and grp is None: grp=n[1:]
            elif not n.startswith('@'): par=n; break
        if par is None: depth[name]=0
        else:
            depth[name]=depth[par]+1; parent[name]=par; rel.add((grp,par,name))
        stack.append((ind,name))
    while i<len(lines):
        t=lines[i].strip(); i+=1
        if t: cross.append(t)
    return depth,parent,rel,cross
def in_target(c,rel,cross):
    op=c['operator']
    if op in ('mandatory','optional'):
        return all((op,c['parent'],ch) in rel for ch in c['children'])
    if op in ('alternative','or'):
        kids={ch for (g,p,ch) in rel if g==op and p==c['parent']}
        return set(c['children'])==kids and len(kids)>0
    # cross-tree: requires/excludes
    d=c['description']
    return None
for kb in ['REAL-FM-7','fqa','arcade-game','REAL-FM-4']:
    depth,parent,rel,cross=parse_uvl(f'data/fms/{kb}.uvl')
    bias={c['id']:c for c in json.load(open(f'data/bias/{kb}-bias.json'))['constraints']}
    maxd=max(depth.values())
    rows=[]
    for f in sorted(glob.glob(f'data/results_conmin_r1/kbs/{kb}/*fold*.json')):
        for e in json.load(open(f)):
            if e['condition']=='C':
                for n in e['names']:
                    c=bias[n]
                    par=c.get('parent') or (c.get('children') or [None])[0]
                    rows.append((e['example_set'],e['fold'],n,c['operator'],depth.get(c.get('parent'),'?'),in_target(c,rel,cross),c['description'][:70]))
    print(f'\n== {kb}: max depth {maxd}, root={[k for k,v in depth.items() if v==0]}')
    alld=collections.Counter(depth.get(c.get('parent'),'x') for c in bias.values() if c['operator'] in ('mandatory','optional','alternative','or'))
    print(' bias hierarchy constraints by parent depth:', dict(sorted(alld.items(), key=lambda x:str(x[0]))))
    print(' cover constraints (set, fold, id, op, parent-depth, in-target, desc):')
    for r in rows: print('  ',r)
    cd=collections.Counter(r[4] for r in rows); print(' cover by parent depth:', dict(cd), ' in-target:', collections.Counter(r[5] for r in rows))
