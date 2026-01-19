"""
Bias generator for feature model constraint acquisition.

This module implements the bias generator that creates
constraint biases from YAML configurations.
"""

from itertools import combinations
from typing import List, Dict
from .data_structures import (
    Feature,
    Constraint,
    Bias,
    OperatorType,
    RelationshipType,
    BiasConfig,
    CrossTreeMode,
)
from .clause_generator import ConstraintClauseGenerator


class BiasGenerator:
    """
    Generate constraint bias from configuration.

    The generator automatically determines allowed operators based on
    relationship types and generates all candidate constraints.
    """

    def __init__(self, config: BiasConfig):
        """
        Initialize bias generator.

        Args:
            config: BiasConfig object loaded from YAML
        """
        self.config = config
        self.feature_ids = config.get_feature_ids()
        self.constraint_counter = 0
        self.clause_gen = ConstraintClauseGenerator()

    def _next_constraint_id(self) -> str:
        """Generate next constraint ID (c1, c2, ...)"""
        self.constraint_counter += 1
        return f"c{self.constraint_counter}"

    def _get_feature_obj(self, name: str) -> Feature:
        """
        Convert feature name to Feature object.

        Args:
            name: Feature name

        Returns:
            Feature object with assigned ID
        """
        return Feature(name=name, id=self.feature_ids[name])

    def generate_hierarchical_constraints(self) -> List[Constraint]:
        """
        Generate all hierarchical constraint candidates.

        For each hierarchical candidate:
        - If relationship_type is BINARY: generate constraints with mandatory and optional
        - If relationship_type is GROUP: generate constraints with alternative and or

        Returns:
            List of Constraint objects
        """
        constraints = []

        for candidate in self.config.hierarchical_candidates:
            parent = self._get_feature_obj(candidate.parent)
            children = [self._get_feature_obj(c) for c in candidate.children]

            # Get allowed operators based on relationship type
            allowed_ops = candidate.get_allowed_operators()

            if candidate.relationship_type == RelationshipType.BINARY:
                # Binary: generate one constraint per (operator, child) pair
                for child in children:
                    for op_name in allowed_ops:
                        op_type = OperatorType(op_name)

                        if op_type == OperatorType.MANDATORY:
                            clauses = self.clause_gen.mandatory(parent, child)
                        else:  # OPTIONAL
                            clauses = self.clause_gen.optional(parent, child)

                        constraint = Constraint(
                            id=self._next_constraint_id(),
                            operator=op_type,
                            parent=parent,
                            children=[child],
                            clauses=clauses,
                            description=f"{parent.name} --{op_name}--> {child.name}"
                        )
                        constraints.append(constraint)

            else:  # GROUP
                # Group: generate one constraint per operator
                for op_name in allowed_ops:
                    op_type = OperatorType(op_name)

                    if op_type == OperatorType.ALTERNATIVE:
                        clauses = self.clause_gen.alternative(parent, children)
                    else:  # OR
                        clauses = self.clause_gen.or_relation(parent, children)

                    child_names = [c.name for c in children]
                    constraint = Constraint(
                        id=self._next_constraint_id(),
                        operator=op_type,
                        parent=parent,
                        children=children,
                        clauses=clauses,
                        description=f"{parent.name} --{op_name}--> {child_names}"
                    )
                    constraints.append(constraint)

        return constraints

    def generate_cross_tree_constraints(self) -> List[Constraint]:
        """
        Generate all cross-tree constraint candidates.

        Based on cross_tree_mode:
        - 'all': Generate constraints between all features
        - 'leaf': Generate constraints only between leaf features

        For each pair, generate both directions of requires (a→b and b→a)
        and excludes (symmetric, only one direction).

        Returns:
            List of Constraint objects
        """
        constraints = []
        allowed_ops = self.config.cross_tree_config.get_allowed_operators()
        cross_tree_mode = self.config.cross_tree_config.cross_tree_mode

        # Use specific pairs if provided
        if self.config.cross_tree_config.specific_pairs:
            for pair in self.config.cross_tree_config.specific_pairs:
                feature_a = self._get_feature_obj(pair[0])
                feature_b = self._get_feature_obj(pair[1])

                for op_name in allowed_ops:
                    op_type = OperatorType(op_name)

                    if op_type == OperatorType.REQUIRES:
                        clauses = self.clause_gen.requires(feature_a, feature_b)
                    else:  # EXCLUDES
                        clauses = self.clause_gen.excludes(feature_a, feature_b)

                    constraints.append(Constraint(
                        id=self._next_constraint_id(),
                        operator=op_type,
                        parent=feature_a,
                        children=[feature_b],
                        clauses=clauses,
                        description=f"{feature_a.name} {op_type.value} {feature_b.name}"
                    ))
        else:
            # Generate pairs based on cross_tree_mode
            cross_tree_feature_names = self.config.get_cross_tree_features()
            cross_tree_features = [self._get_feature_obj(name) for name in cross_tree_feature_names]

            for feature_a, feature_b in combinations(cross_tree_features, 2):
                for op_name in allowed_ops:
                    op_type = OperatorType(op_name)

                    if op_type == OperatorType.REQUIRES:
                        # Generate BOTH directions for requires
                        # a → b
                        clauses_ab = self.clause_gen.requires(feature_a, feature_b)
                        constraints.append(Constraint(
                            id=self._next_constraint_id(),
                            operator=op_type,
                            parent=feature_a,
                            children=[feature_b],
                            clauses=clauses_ab,
                            description=f"{feature_a.name} requires {feature_b.name}"
                        ))

                        # b → a
                        clauses_ba = self.clause_gen.requires(feature_b, feature_a)
                        constraints.append(Constraint(
                            id=self._next_constraint_id(),
                            operator=op_type,
                            parent=feature_b,
                            children=[feature_a],
                            clauses=clauses_ba,
                            description=f"{feature_b.name} requires {feature_a.name}"
                        ))

                    elif op_type == OperatorType.EXCLUDES:
                        # Excludes is symmetric, only one direction
                        clauses = self.clause_gen.excludes(feature_a, feature_b)
                        constraints.append(Constraint(
                            id=self._next_constraint_id(),
                            operator=op_type,
                            parent=feature_a,
                            children=[feature_b],
                            clauses=clauses,
                            description=f"{feature_a.name} excludes {feature_b.name}"
                        ))

        return constraints

    def generate_bias(self) -> Bias:
        """
        Generate complete bias B.

        Returns:
            Bias object containing all generated constraints

        Example output:
            Generating hierarchical constraints...
              Generated 8 hierarchical constraints
            Generating cross-tree constraints...
              Generated 24 cross-tree constraints
            Total bias size: 32 constraints
        """
        print("Generating hierarchical constraints...")
        hierarchical = self.generate_hierarchical_constraints()
        print(f"  Generated {len(hierarchical)} hierarchical constraints")

        mode = self.config.cross_tree_config.cross_tree_mode.value
        print(f"Generating cross-tree constraints (mode: {mode})...")
        cross_tree = self.generate_cross_tree_constraints()
        print(f"  Generated {len(cross_tree)} cross-tree constraints")

        all_constraints = hierarchical + cross_tree

        # Convert feature names to Feature objects
        features = [self._get_feature_obj(name) for name in self.config.features]

        bias = Bias(
            constraints=all_constraints,
            features=features
        )

        print(f"Total bias size: {len(bias.constraints)} constraints")
        return bias

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the bias that will be generated.

        Returns:
            Dictionary with statistics:
                {
                    'num_features': int,
                    'num_hierarchical': int,
                    'num_cross_tree': int,
                    'total': int,
                    'breakdown': Counter of operator types
                }
        """
        from collections import Counter

        # Generate to count
        hierarchical = self.generate_hierarchical_constraints()
        cross_tree = self.generate_cross_tree_constraints()
        all_constraints = hierarchical + cross_tree

        op_counts = Counter(c.operator.value for c in all_constraints)

        return {
            'num_features': len(self.config.features),
            'num_hierarchical': len(hierarchical),
            'num_cross_tree': len(cross_tree),
            'total': len(all_constraints),
            'breakdown': dict(op_counts)
        }
