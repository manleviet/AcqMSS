"""
Bias I/O utilities for saving and loading bias files.

This module provides functionality to save and load constraint biases
in different formats: JSON (structured) and DIMACS CNF (standard SAT format).
"""

import json
from pathlib import Path
from typing import Dict
from .data_structures import Feature, Constraint, Bias, OperatorType


class BiasIO:
    """Save and load bias to/from files"""

    @staticmethod
    def save_to_cnf(bias: Bias, filepath: str):
        """
        Save bias to DIMACS CNF format with metadata in comments.

        Format:
            c <metadata in comments>
            c Constraint c1: survey --mandatory--> payment
            c Constraint c2: payment --optional--> license
            p cnf <num_vars> <num_clauses>
            <clauses>

        Args:
            bias: Bias object to save
            filepath: Output file path

        Example output:
            c Constraint Bias B
            c Generated for constraint acquisition
            c Number of features: 9
            c Number of constraints: 92
            c
            c Feature mapping:
            c   1: survey
            c   2: payment
            c
            c Constraint descriptions:
            c   c1: survey --mandatory--> payment
            c   c2: survey --optional--> payment
            c
            p cnf 9 184
            -1 2 0
            -2 1 0
            -2 1 0
            ...
        """
        with open(filepath, 'w') as f:
            # Header comments
            f.write("c Constraint Bias B\n")
            f.write("c Generated for constraint acquisition\n")
            f.write(f"c Number of features: {len(bias.features)}\n")
            f.write(f"c Number of constraints: {len(bias.constraints)}\n")
            f.write("c\n")

            # Feature mapping
            f.write("c Feature mapping:\n")
            for feature in sorted(bias.features, key=lambda f: f.id):
                f.write(f"c   {feature.id}: {feature.name}\n")
            f.write("c\n")

            # Constraint descriptions
            f.write("c Constraint descriptions:\n")
            for constraint in bias.constraints:
                f.write(f"c   {constraint.id}: {constraint.description}\n")
            f.write("c\n")

            # CNF header
            all_clauses = bias.to_cnf()
            num_vars = max(f.id for f in bias.features)
            num_clauses = len(all_clauses)
            f.write(f"p cnf {num_vars} {num_clauses}\n")

            # Clauses (one per line, terminated with 0)
            for clause in all_clauses:
                f.write(' '.join(map(str, clause)) + ' 0\n')

    @staticmethod
    def save_to_json(bias: Bias, filepath: str):
        """
        Save bias to JSON format (more structured, easier to load).

        Args:
            bias: Bias object to save
            filepath: Output file path

        Example output:
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
        """
        data = {
            'features': [
                {'name': f.name, 'id': f.id}
                for f in sorted(bias.features, key=lambda f: f.id)
            ],
            'constraints': [
                {
                    'id': c.id,
                    'operator': c.operator.value if c.operator else None,
                    'parent': c.parent.name if c.parent else None,
                    'children': [ch.name for ch in c.children],
                    'clauses': c.clauses,
                    'description': c.description
                }
                for c in bias.constraints
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_from_json(filepath: str) -> Bias:
        """
        Load bias from JSON file.

        Args:
            filepath: Input JSON file path

        Returns:
            Bias object

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON parsing fails
        """
        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"Bias file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct features
        features = [
            Feature(name=f['name'], id=f['id'])
            for f in data['features']
        ]
        feature_map = {f.name: f for f in features}

        # Reconstruct constraints
        constraints = []
        for c_data in data['constraints']:
            parent = feature_map.get(c_data['parent']) if c_data['parent'] else None
            children = [feature_map[name] for name in c_data['children']]

            constraint = Constraint(
                id=c_data['id'],
                operator=OperatorType(c_data['operator']) if c_data['operator'] else None,
                parent=parent,
                children=children,
                clauses=c_data['clauses'],
                description=c_data['description']
            )
            constraints.append(constraint)

        return Bias(constraints=constraints, features=features)

    @staticmethod
    def save_statistics(bias: Bias, filepath: str):
        """
        Save bias statistics to a text file.

        Args:
            bias: Bias object
            filepath: Output file path

        Output format:
            ===  Bias Statistics ===
            Total features: 9
            Total constraints: 92
            Total clauses: 184

            Constraints by operator:
              mandatory: 4
              optional: 4
              alternative: 2
              or: 2
              requires: 72
              excludes: 36
        """
        from collections import Counter

        with open(filepath, 'w') as f:
            f.write("=== Bias Statistics ===\n")
            f.write(f"Total features: {len(bias.features)}\n")
            f.write(f"Total constraints: {len(bias.constraints)}\n")
            f.write(f"Total clauses: {len(bias.to_cnf())}\n")
            f.write("\n")

            # Count by operator
            op_counts = Counter(c.operator.value if c.operator else 'unknown'
                                for c in bias.constraints)
            f.write("Constraints by operator:\n")
            for op, count in sorted(op_counts.items()):
                f.write(f"  {op}: {count}\n")

            f.write("\n")

            # Feature list
            f.write("Features:\n")
            for feature in sorted(bias.features, key=lambda f: f.id):
                f.write(f"  {feature.id}: {feature.name}\n")
