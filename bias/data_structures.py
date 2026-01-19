"""
Data structures for constraint bias generation.

This module defines the core data structures used in constraint acquisition:
- Feature: Represents a binary feature in a feature model
- Constraint: Represents a constraint with operator and CNF clauses
- Bias: Collection of constraints forming the constraint bias B
- Configuration classes for simplified YAML input
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class OperatorType(Enum):
    """Types of operators in feature models"""
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    ALTERNATIVE = "alternative"
    OR = "or"
    REQUIRES = "requires"
    EXCLUDES = "excludes"


class RelationshipType(Enum):
    """Type of hierarchical relationship"""
    BINARY = "binary"  # mandatory/optional
    GROUP = "group"  # alternative/or


@dataclass
class Feature:
    """Represents a binary feature in a feature model"""
    name: str
    id: int  # SAT variable ID (positive integer)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Feature) and self.id == other.id

    def __repr__(self):
        return f"Feature({self.name}, id={self.id})"


@dataclass
class Constraint:
    """Represents a constraint in bias B"""
    id: str  # e.g., "c1", "c2"
    operator: Optional[OperatorType]
    parent: Optional[Feature] = None
    children: List[Feature] = field(default_factory=list)
    clauses: List[List[int]] = field(default_factory=list)  # CNF clauses
    description: str = ""

    def to_cnf(self) -> List[List[int]]:
        """Convert constraint to CNF clauses"""
        return self.clauses

    def __str__(self):
        if self.operator in [OperatorType.MANDATORY, OperatorType.OPTIONAL]:
            return f"{self.id}: {self.parent.name} --{self.operator.value}--> {self.children[0].name}"
        elif self.operator in [OperatorType.ALTERNATIVE, OperatorType.OR]:
            child_names = [c.name for c in self.children]
            return f"{self.id}: {self.parent.name} --{self.operator.value}--> {child_names}"
        elif self.operator == OperatorType.REQUIRES:
            return f"{self.id}: {self.parent.name} requires {self.children[0].name}"
        elif self.operator == OperatorType.EXCLUDES:
            return f"{self.id}: {self.parent.name} excludes {self.children[0].name}"
        else:
            return f"{self.id}: {self.description}"


@dataclass
class Bias:
    """Constraint bias B - collection of candidate constraints"""
    constraints: List[Constraint]
    features: List[Feature]

    def get_constraint_by_id(self, cid: str) -> Optional[Constraint]:
        """Get constraint by ID"""
        for c in self.constraints:
            if c.id == cid:
                return c
        return None

    def to_cnf(self) -> List[List[int]]:
        """Get all CNF clauses from all constraints"""
        clauses = []
        for c in self.constraints:
            clauses.extend(c.clauses)
        return clauses

    def __len__(self):
        return len(self.constraints)

    def __repr__(self):
        return f"Bias({len(self.constraints)} constraints, {len(self.features)} features)"


@dataclass
class SimplifiedHierarchicalCandidate:
    """Simplified hierarchical candidate specification for config file"""
    parent: str
    children: List[str]
    relationship_type: RelationshipType

    def get_allowed_operators(self) -> List[str]:
        """Get allowed operators based on relationship type"""
        if self.relationship_type == RelationshipType.BINARY:
            return ['mandatory', 'optional']
        else:  # GROUP
            return ['alternative', 'or']


class CrossTreeMode(Enum):
    """Mode for cross-tree constraint generation"""
    ALL = "all"    # Generate constraints between all features
    LEAF = "leaf"  # Generate constraints only between leaf features


@dataclass
class SimplifiedCrossTreeConfig:
    """Simplified cross-tree configuration"""
    cross_tree_mode: CrossTreeMode = CrossTreeMode.LEAF
    specific_pairs: List[tuple] = field(default_factory=list)

    def get_allowed_operators(self) -> List[str]:
        """Always generate both requires and excludes"""
        return ['requires', 'excludes']


@dataclass
class SimplifiedBiasConfig:
    """Simplified bias configuration loaded from YAML"""
    name: str
    features: List[str]  # All feature names
    leaf_features: List[str]  # Leaf feature names (features with no children)
    hierarchical_candidates: List[SimplifiedHierarchicalCandidate]
    cross_tree_config: SimplifiedCrossTreeConfig

    def get_feature_ids(self) -> Dict[str, int]:
        """Auto-assign IDs to features (starting from 1)"""
        feature_ids = {}
        for i, feature_name in enumerate(self.features, start=1):
            feature_ids[feature_name] = i
        return feature_ids

    def get_cross_tree_features(self) -> List[str]:
        """Get features to use for cross-tree constraint generation based on mode"""
        if self.cross_tree_config.cross_tree_mode == CrossTreeMode.LEAF:
            return self.leaf_features
        else:  # ALL
            return self.features
