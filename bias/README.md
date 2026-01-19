# Bias Module

Module sinh constraint bias cho Feature Model Constraint Acquisition.

## Tổng quan

Module này cung cấp các công cụ để:
1. Đọc cấu hình feature model từ file YAML đơn giản
2. Sinh tự động các constraint candidates (bias B)
3. Lưu/đọc bias ở nhiều định dạng (JSON, DIMACS CNF)

## Kiến trúc

```
bias/
├── __init__.py              # Package exports
├── data_structures.py       # Feature, Constraint, Bias classes
├── clause_generator.py      # CNF clause generators
├── config_loader.py         # YAML config loader
├── bias_generator.py        # Main bias generator
├── bias_io.py              # Save/load utilities
└── README.md               # This file
```

## Sử dụng nhanh

### 1. Tạo file cấu hình YAML

```yaml
name: Survey

features:
  - survey
  - payment
  - license
  - nolicense

hierarchical_candidates:
  - parent: survey
    children: [payment]
    relationship_type: binary  # Sẽ sinh mandatory + optional

  - parent: payment
    children: [license, nolicense]
    relationship_type: group   # Sẽ sinh alternative + or

cross_tree_candidates:
  auto_generate: true  # Sinh tất cả requires + excludes
```

### 2. Sinh bias

```python
from bias import ConfigLoader, BiasGenerator, BiasIO

# Load config
config = ConfigLoader.load('configs/survey.yaml')

# Generate bias
generator = BiasGenerator(config)
bias = generator.generate_bias()

# Save
BiasIO.save_to_json(bias, 'data/bias.json')
BiasIO.save_to_cnf(bias, 'data/bias.cnf')
```

### 3. Sử dụng trong CONGEN

```python
from bias import BiasIO

# Load bias
B = BiasIO.load_from_json('data/bias.json')

# Use in ACQMSS
B_prime = acqmss(set(), B.constraints, NE, E_plus, BG)
```

## Các loại operators

### Hierarchical Relationships

**Binary (mandatory/optional):**
- `mandatory`: child ↔ parent (bidirectional)
  - CNF: `[[-parent, child], [-child, parent]]`
- `optional`: child → parent
  - CNF: `[[-child, parent]]`

**Group (alternative/or):**
- `alternative`: exactly one child if parent
  - At least one: `[[-parent, child1, child2, ...]]`
  - At most one: `[[-childi, -childj]]` for all pairs
  - Child implies parent: `[[-child, parent]]`

- `or`: at least one child if parent
  - At least one: `[[-parent, child1, child2, ...]]`
  - Child implies parent: `[[-child, parent]]`

### Cross-tree Constraints

- `requires`: a → b
  - CNF: `[[-a, b]]`

- `excludes`: ¬(a ∧ b)
  - CNF: `[[-a, -b]]`

## Định dạng file

### Input: YAML Config

```yaml
name: <feature_model_name>

features:
  - <feature1>
  - <feature2>
  ...

hierarchical_candidates:
  - parent: <parent_name>
    children: [<child1>, <child2>, ...]
    relationship_type: binary|group

cross_tree_candidates:
  auto_generate: true|false
  specific_pairs:  # Optional, if not auto_generate
    - [<feature1>, <feature2>]
```

### Output: JSON Bias

```json
{
  "features": [
    {"name": "survey", "id": 1},
    {"name": "payment", "id": 2}
  ],
  "constraints": [
    {
      "id": "c1",
      "operator": "mandatory",
      "parent": "survey",
      "children": ["payment"],
      "clauses": [[-1, 2], [-2, 1]],
      "description": "survey --mandatory--> payment"
    }
  ]
}
```

### Output: DIMACS CNF

```
c Constraint Bias B
c Generated for constraint acquisition
c
c Feature mapping:
c   1: survey
c   2: payment
c
p cnf 9 134
-1 2 0
-2 1 0
...
```

## Ví dụ

Xem file `test_bias_module.py` để biết cách sử dụng chi tiết.

Chạy test:
```bash
python3 test_bias_module.py
```

## Kích thước Bias

Với n features:

**Hierarchical:**
- Binary relationships: 2 constraints × số children (mandatory + optional)
- Group relationships: 2 constraints × số groups (alternative + or)

**Cross-tree (auto_generate=true):**
- Requires: n × (n-1) = n(n-1) constraints (cả 2 chiều)
- Excludes: n × (n-1) / 2 constraints (đối xứng)
- Total: 3n(n-1)/2

**Ví dụ:** Survey model (9 features)
- Hierarchical: 12 constraints
- Cross-tree: 108 constraints (72 requires + 36 excludes)
- **Total: 120 constraints**

## Tham khảo

- Plan: `paper/plan_bias.md`
- Paper: `paper/AcqMSS.pdf`
