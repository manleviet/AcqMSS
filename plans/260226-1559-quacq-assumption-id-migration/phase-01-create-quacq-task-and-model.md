# Phase 1: Create QuAcqTask, InteractiveModel, InteractiveTaskPreparation

## Context Links
- [Parent Plan](plan.md)
- [Brainstorm](../reports/brainstorm-260226-1541-quacq-assumption-id-migration.md)
- Pattern: `conacq/algorithms/acqmss/task_preparation.py` (ConGenTask + ConGenTaskPreparation)
- Pattern: `conacq/algorithms/acqmss/congen_model.py` (ConGenModel)
- Shared infra: `explanation/models/task_preparation.py` (prepare_kb, DescriptionProvider)

## Overview
- **Priority**: P1
- **Status**: completed
- **Description**: Create parallel assumption-based data structures for QuAcq, mirroring ConGen's ConGenTask/ConGenModel/ConGenTaskPreparation pattern.

## Key Insights
1. `prepare_kb()` (line 249 of `explanation/models/task_preparation.py`) assigns assumption IDs to constraint_map entries with negation pairs. Reusable directly.
2. `BGData` from oracle provides root BG assumption IDs and `next_available_id`.
3. QuAcq needs `constraint_clauses: Dict[int, List[List[int]]]` for violation checking (maps assumption_id -> raw clauses). ConGen doesn't need this because ACQMSS operates purely on assumption IDs.
4. QuAcq also needs `id_to_constraint_name: Dict[int, str]` for reverse lookup (or use DescriptionProvider).
5. InteractiveModel does NOT need E+/E- (unlike ConGenModel) — bias + oracle is sufficient.

## Requirements

### Functional
- QuAcqTask holds all state needed by QuAcq/FindScope/FindC with `int` assumption IDs
- InteractiveModel stores bias data, delegates preparation to InteractiveTaskPreparation
- InteractiveModel.prepare(oracle) returns QuAcqTask (like ConGenModel.prepare())
- DescriptionProvider maps assumption_id -> constraint name for display

### Non-functional
- Reuse `prepare_kb()`, `negate_cnf_tseitin()`, `BGData` — no duplication
- Keep each new file under 200 lines

## Architecture

```
InteractiveModel(bias_data)
  .prepare(oracle: FeatureModelOracle) -> QuAcqTask
    ├─ bg_data = oracle.get_bg_data()  # root BG assumption pair
    ├─ negate_cnf_tseitin() for each bias constraint
    ├─ prepare_kb() assigns assumption IDs with negation pairs
    ├─ Build constraint_clauses: Dict[int, List[List[int]]]
    ├─ Build id_to_constraint_name: Dict[int, str] (via DescriptionProvider)
    └─ Return QuAcqTask
```

Assumption ID layout (QuAcq owns Parts 5-6, no E+/E-):
- Parts 1-4: Oracle (same as ConGen)
- Part 5: Tseitin vars (negated bias)
- Part 6: Bias constraint assumptions (paired: original + negated)

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `conacq/algorithms/interactive/quacq_task.py` | QuAcqTask dataclass (~80 lines) |
| `conacq/algorithms/interactive/interactive_model.py` | InteractiveModel class (~120 lines) |
| `conacq/algorithms/interactive/interactive_task_preparation.py` | InteractiveTaskPreparation (~100 lines) |

### Files to Read (patterns)
| File | Why |
|------|-----|
| `conacq/algorithms/acqmss/task_preparation.py` | ConGenTask + ConGenTaskPreparation pattern |
| `conacq/algorithms/acqmss/congen_model.py` | ConGenModel.prepare() pattern |
| `explanation/models/task_preparation.py` | prepare_kb(), DescriptionProvider, DiagnosisTask |
| `conacq/oracle/bg_data.py` | BGData frozen dataclass |
| `conacq/algorithms/interactive/task.py` | Current InteractiveTask (fields to mirror) |

## Implementation Steps

### Step 1: Create `quacq_task.py`

```python
@dataclass
class QuAcqTask:
    """Assumption-based task for QuAcq, parallel to ConGenTask."""
    # Bias constraint assumption IDs (set for O(1) removal)
    bias: Set[int] = field(default_factory=set)
    # Learned KB assumption IDs
    learned_kb: List[int] = field(default_factory=list)
    # Full KB with assumption guards (for checker)
    set_kb: List[List[int]] = field(default_factory=list)
    # All assumption IDs
    assumptions: List[int] = field(default_factory=list)
    # Negation map: assumption_id -> negated_assumption_id
    negation_map: Dict[int, int] = field(default_factory=dict)
    # BG assumption IDs (from BGData)
    background: List[int] = field(default_factory=list)
    # Feature name -> SAT var
    feature_ids: Dict[str, int] = field(default_factory=dict)
    # SAT var -> feature name
    id_to_feature: Dict[int, str] = field(default_factory=dict)
    # assumption_id -> raw clauses (WITHOUT assumption guards, for violation checking)
    constraint_clauses: Dict[int, List[List[int]]] = field(default_factory=dict)
    # Query stats
    n_queries: int = 0
    query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)
```

Methods to include (port from InteractiveTask, change `str` -> `int`):
- `add_to_kb(assumption_id: int)` — add to learned_kb
- `remove_from_bias(ids: List[int])` — remove from bias set
- `record_query(config, answer)` — same as before
- `config_to_assumptions(config)` — same (feature_ids unchanged)
- `model_to_config(model)` — same (id_to_feature unchanged)
- `get_kb_clauses()` — get raw clauses from learned_kb via constraint_clauses
- `get_constraints_with_scope(scope: set) -> List[int]` — return assumption IDs
- `_get_constraint_vars(assumption_id: int) -> set` — uses constraint_clauses
- `partial_config_to_assumptions(config, variables)` — same
- `violates_clauses(clauses, assignment)` — static, unchanged
- `clone()` — deep copy

### Step 2: Create `interactive_task_preparation.py`

```python
class InteractiveTaskPreparation:
    """Prepare QuAcqTask from bias + oracle. No E+/E-."""

    def prepare(self, model: InteractiveModel,
                oracle: FeatureModelOracle) -> PreparationOutput:
        result = QuAcqTask()
        provider = DescriptionProvider()

        # Step 0: BG from oracle
        bg_data = oracle.get_bg_data()
        result.set_kb.extend(bg_data.set_kb)
        result.assumptions.extend(list(bg_data.assumptions))
        result.negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)
        result.background = list(bg_data.assumptions)
        id_assumption = bg_data.next_available_id

        # Step 1: Negate bias constraints (Tseitin)
        next_tseitin_var = id_assumption
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses

        # Step 2: Assign assumption IDs via prepare_kb()
        id_assumption = next_tseitin_var
        bias_start_pos = len(result.assumptions)
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)

        # Step 3: Extract bias assumption IDs (every other = stride 2)
        result.bias = set(
            result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])

        # Step 4: Build constraint_clauses mapping
        for aid in result.bias:
            name = provider.get_description(aid)
            if name in model.constraint_map:
                result.constraint_clauses[aid] = model.constraint_map[name]

        # Step 5: Populate feature_ids/id_to_feature from oracle
        fm_data = oracle.get_fm_data()
        result.feature_ids = fm_data.feature_ids
        result.id_to_feature = {v: k for k, v in fm_data.feature_ids.items()}

        return PreparationOutput(result, provider)
```

**Important**: `prepare_kb()` takes a `DiagnosisTask` as first arg. QuAcqTask must be compatible — it needs `set_kb`, `assumptions`, `negation_map` fields. Either:
- (a) Make QuAcqTask inherit from DiagnosisTask, or
- (b) Use duck typing (QuAcqTask has same fields that prepare_kb writes to)

Recommendation: (b) — QuAcqTask already has the needed fields. `prepare_kb()` only accesses `result.set_kb`, `result.assumptions`, `result.negation_map`. Verify this works. If `prepare_kb` type-checks strictly, may need a thin adapter.

### Step 3: Create `interactive_model.py`

```python
class InteractiveModel:
    """Model for interactive learning, parallel to ConGenModel."""

    def __init__(self) -> None:
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}  # feature_ids from bias
        self.next_available_id: int = 1000
        self._task: Optional[QuAcqTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

    @classmethod
    def from_bias(cls, bias_path: str) -> 'InteractiveModel':
        """Build model from bias JSON file."""
        bias = BiasIO.load_from_json(bias_path)
        model = cls()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids
        return model

    @property
    def task(self) -> Optional[QuAcqTask]:
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        if self._description_provider is None:
            raise RuntimeError("Call prepare() first")
        return self._description_provider

    def prepare(self, oracle: FeatureModelOracle) -> QuAcqTask:
        """Assign assumption IDs and build QuAcqTask."""
        preparation = InteractiveTaskPreparation()
        output = preparation.prepare(self, oracle)
        assert isinstance(output.task, QuAcqTask)
        self._task = output.task
        self._description_provider = output.description_provider
        return self._task

    def resolve_kb(self, kb_assumption_ids: List[int]) -> Tuple[List[str], List[List[int]]]:
        """Resolve assumption IDs to names and clauses."""
        provider = self.description_provider
        names = [provider.get_description(aid) for aid in kb_assumption_ids]
        clauses = []
        for aid in kb_assumption_ids:
            name = provider.get_description(aid)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return names, clauses
```

### Step 4: Update `__init__.py`
Add new exports:
```python
from .quacq_task import QuAcqTask
from .interactive_model import InteractiveModel
from .interactive_task_preparation import InteractiveTaskPreparation
```

## Todo List
- [ ] Create `conacq/algorithms/interactive/quacq_task.py` with QuAcqTask dataclass
- [ ] Create `conacq/algorithms/interactive/interactive_task_preparation.py`
- [ ] Create `conacq/algorithms/interactive/interactive_model.py`
- [ ] Verify `prepare_kb()` duck-typing works with QuAcqTask (has set_kb, assumptions, negation_map)
- [ ] Update `conacq/algorithms/interactive/__init__.py` with new exports
- [ ] Run type check / basic import test

## Success Criteria
- `InteractiveModel.from_bias(path).prepare(oracle)` returns a valid QuAcqTask
- QuAcqTask.bias contains `Set[int]` assumption IDs
- QuAcqTask.constraint_clauses maps each bias assumption_id to raw CNF clauses
- DescriptionProvider maps each assumption_id to constraint name string
- No duplicated logic from ConGenTaskPreparation

## Risk Assessment
1. **prepare_kb() type compatibility**: `prepare_kb()` first param is `DiagnosisTask`. QuAcqTask is not a DiagnosisTask subclass. If prepare_kb uses isinstance check, need adapter. Mitigation: check prepare_kb source — it only accesses `.set_kb`, `.assumptions`, `.negation_map` attributes.
2. **Tseitin var range overlap**: Must start from `bg_data.next_available_id` to avoid overlap with oracle assumption IDs. ConGenTaskPreparation does this; follow same pattern.

## Security Considerations
- No external input validation changes needed (bias file validation unchanged)

## Next Steps
- Phase 2: Update QuAcq algorithm to use QuAcqTask
- Phase 3: Update FindScope/FindC to use QuAcqTask
