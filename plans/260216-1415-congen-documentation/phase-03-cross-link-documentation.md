# Phase 3: Cross-Link Documentation

## Priority
P2

## Status
complete

## Overview
Update CLAUDE.md, README.md, and docs/README.md to reference the new docs/congen.md file. Ensure all navigation paths, indexes, and cross-references include ConGen documentation.

## Context Links
- Phase 2 output: `docs/congen.md`
- Parent plan: `plans/260216-1415-congen-documentation/plan.md`

## Key Insights
- CLAUDE.md has a "Key references" list and a docs tree listing — both need congen.md
- README.md has a Documentation table — needs congen.md row
- docs/README.md is the main doc index — needs updates in 6+ locations

## Related Code Files

### Files to Modify
- `CLAUDE.md` — 2 edits (key references + docs tree)
- `README.md` — 1 edit (documentation table)
- `docs/README.md` — 6 edits (section, stats, flow diagram, topics, roles, version)

## Implementation Steps

### 1. CLAUDE.md — Key References (Line ~15)
Add after quacq.md line:
```markdown
- `docs/congen.md` — ConGen algorithm documentation (MSS-based constraint acquisition)
```

### 2. CLAUDE.md — Docs Tree (Lines 113-122)
Add `congen.md` to the tree listing:
```
├── congen.md
```

### 3. README.md — Documentation Table (Line ~143)
Add row after quacq.md:
```markdown
| [docs/congen.md](docs/congen.md) | ConGen algorithm documentation (MSS-based acquisition) |
```

### 4. docs/README.md — New Section (After quacq.md section, ~Line 129)
Add congen.md section following same format as quacq.md section:
```markdown
### congen.md
**Purpose**: ConGen algorithm documentation (MSS-based constraint acquisition)
**Length**: TBD LOC

Paper-based implementation guide:
- Overview of ConGen algorithm (passive/batch learning via MSS)
- Three sub-algorithms: GenerateNE, AcqMSS, REDUCE
- Complexity analysis and correctness theorems
- Working example walkthrough
- Relation to codebase (file locations, LOC)
- Shared infrastructure with QuAcq

**Read when**: You need to understand the ConGen/ACQMSS algorithm or modify passive learning.
```

### 5. docs/README.md — Flow Diagram (~Line 154)
Add after quacq.md line:
```
congen.md (ALGORITHM DETAILS)
    ↓
    Deep dive on ConGen/ACQMSS implementation
```

### 6. docs/README.md — Statistics Table (~Line 253)
Add row for congen.md and update TOTAL.

### 7. docs/README.md — Algorithms & Techniques (~Line 285)
Add:
```markdown
- [congen.md](#congen) → ConGen algorithm details
```

### 8. docs/README.md — Algorithm Researcher Role (~Line 303)
Add:
```markdown
3. [congen.md](#congen) — ConGen/ACQMSS implementation details
```

### 9. docs/README.md — Version History (~Line 334)
Add version entry:
```markdown
- v1.3 (2026-02-16): Added congen.md, cross-linked all docs
```

## Todo

- [x] Update CLAUDE.md key references
- [x] Update CLAUDE.md docs tree
- [x] Update README.md documentation table
- [x] Add congen.md section to docs/README.md
- [x] Update flow diagram in docs/README.md
- [x] Update statistics table in docs/README.md
- [x] Update topic/role sections in docs/README.md
- [x] Update version history in docs/README.md

## Success Criteria
- [x] All 3 files updated (CLAUDE.md, README.md, docs/README.md)
- [x] congen.md appears in every navigation path and index
- [x] No broken links
- [x] Statistics table reflects actual congen.md LOC

## Risk Assessment
- **LOC unknown until Phase 2 completes**: Use TBD placeholder, update after writing
  - Mitigation: Phase 3 runs after Phase 2, so actual LOC will be known
