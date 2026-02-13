"""
Oracle data extractor for evaluation.

Extracts constraint descriptions and CNF clauses from feature models
using the FeatureModelOracle.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict
from pathlib import Path

from acqmss.oracle import FeatureModelOracle


@dataclass
class OracleData:
    """
    Oracle data extracted from feature model.

    Attributes:
        descriptions: Set of constraint descriptions (for Strategy 1)
        clauses: All CNF clauses as lists (for Strategy 2)
        clause_set: Normalized clause set with sorted tuples
        feature_map: Mapping {feature_name: variable_id}
        root_feature: Name of root feature
    """
    descriptions: Set[str] = field(default_factory=set)
    clauses: List[List[int]] = field(default_factory=list)
    clause_set: Set[Tuple[int, ...]] = field(default_factory=set)
    feature_map: Dict[str, int] = field(default_factory=dict)
    root_feature: str = ""

    @classmethod
    def from_uvl(cls, uvl_path: Path) -> 'OracleData':
        """
        Load Oracle data from UVL file.

        Args:
            uvl_path: Path to feature model (.uvl format)

        Returns:
            OracleData instance
        """
        uvl_path = Path(uvl_path)
        oracle = FeatureModelOracle(str(uvl_path))

        # Extract descriptions (Strategy 1)
        descriptions = oracle.get_constraint_descriptions()

        # Extract clauses (Strategy 2)
        clauses = oracle.get_cnf_clauses()
        clause_set = {tuple(sorted(c)) for c in clauses}

        # Feature mapping
        feature_map = oracle.get_feature_ids()

        # Root feature
        root_feature = oracle.get_root_feature()

        # Clean up oracle
        del oracle

        return cls(
            descriptions=descriptions,
            clauses=clauses,
            clause_set=clause_set,
            feature_map=feature_map,
            root_feature=root_feature
        )

    @classmethod
    def from_oracle(cls, oracle: FeatureModelOracle) -> 'OracleData':
        """
        Create OracleData from existing FeatureModelOracle.

        Args:
            oracle: Existing oracle instance

        Returns:
            OracleData instance
        """
        descriptions = oracle.get_constraint_descriptions()
        clauses = oracle.get_cnf_clauses()
        clause_set = {tuple(sorted(c)) for c in clauses}
        feature_map = oracle.get_feature_ids()
        root_feature = oracle.get_root_feature()

        return cls(
            descriptions=descriptions,
            clauses=clauses,
            clause_set=clause_set,
            feature_map=feature_map,
            root_feature=root_feature
        )

    def __len__(self) -> int:
        """Number of descriptions/constraints."""
        return len(self.descriptions)

    def __repr__(self) -> str:
        return (f"OracleData(descriptions={len(self.descriptions)}, "
                f"clauses={len(self.clauses)}, features={len(self.feature_map)})")
