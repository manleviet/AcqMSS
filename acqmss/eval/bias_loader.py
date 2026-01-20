"""
Bias file loader for evaluation.

Loads bias JSON files that contain constraint definitions with clauses
and descriptions for comparison with learned KB.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
from pathlib import Path
import json


@dataclass
class BiasConstraint:
    """Single bias constraint."""
    id: str
    operator: str
    clauses: List[List[int]]
    description: str
    parent: str = ""
    children: List[str] = field(default_factory=list)


@dataclass
class BiasData:
    """
    Loaded bias data.

    Attributes:
        constraints: Mapping {constraint_id: BiasConstraint}
        features: Mapping {feature_name: variable_id}
        constraint_ids: List of all constraint IDs in order
    """
    constraints: Dict[str, BiasConstraint] = field(default_factory=dict)
    features: Dict[str, int] = field(default_factory=dict)
    constraint_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, json_path: Path) -> 'BiasData':
        """
        Load bias from JSON file.

        Args:
            json_path: Path to bias JSON file

        Returns:
            BiasData instance
        """
        json_path = Path(json_path)
        with open(json_path, 'r') as f:
            data = json.load(f)

        features = {f['name']: f['id'] for f in data.get('features', [])}
        constraints = {}
        constraint_ids = []

        for c in data.get('constraints', []):
            constraint_id = c['id']
            constraint_ids.append(constraint_id)
            constraints[constraint_id] = BiasConstraint(
                id=constraint_id,
                operator=c.get('operator', ''),
                clauses=c.get('clauses', []),
                description=c.get('description', ''),
                parent=c.get('parent', ''),
                children=c.get('children', [])
            )

        return cls(
            constraints=constraints,
            features=features,
            constraint_ids=constraint_ids
        )

    def get_clauses(self, constraint_id: str) -> List[List[int]]:
        """Get CNF clauses for a constraint."""
        if constraint_id in self.constraints:
            return self.constraints[constraint_id].clauses
        return []

    def get_description(self, constraint_id: str) -> str:
        """Get description for a constraint."""
        if constraint_id in self.constraints:
            return self.constraints[constraint_id].description
        return ""

    def get_all_clauses(self) -> Set[Tuple[int, ...]]:
        """Get all clauses as normalized tuples."""
        result = set()
        for c in self.constraints.values():
            for clause in c.clauses:
                result.add(tuple(sorted(clause)))
        return result

    def get_all_descriptions(self) -> Set[str]:
        """Get all constraint descriptions."""
        return {c.description for c in self.constraints.values()}

    def get_constraint_ids_by_description(self, description: str) -> List[str]:
        """Find constraint IDs matching a description."""
        return [
            cid for cid, c in self.constraints.items()
            if c.description == description
        ]

    def __len__(self) -> int:
        """Number of constraints."""
        return len(self.constraints)

    def __repr__(self) -> str:
        return f"BiasData(constraints={len(self.constraints)}, features={len(self.features)})"
