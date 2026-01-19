#!/usr/bin/env python3
"""
Generate YAML bias config from a feature model (.uvl).

This script reads a feature model and generates a YAML bias configuration file
that can be used with the bias generation system.

Usage:
    python generate_bias_config.py <feature_model.uvl> [output.yaml]

Example:
    python generate_bias_config.py data/fms/REAL-FM-7.uvl configs/REAL-FM-7.yaml
"""
import os
import sys
import argparse
from argparse import Namespace
from pathlib import Path
from typing import List, Dict, Any

from flamapy.metamodels.fm_metamodel.models import FeatureModel

# This is a workaround to set the root project folder as the current working directory
ROOT_PROJECT_FOLDER = Path(__file__).resolve().parent.parent
os.chdir(ROOT_PROJECT_FOLDER)
sys.path.insert(0, os.getcwd())

def parse_argument() -> Namespace:
    parser = argparse.ArgumentParser(
        description="Generate YAML bias config from a feature model (.uvl)"
    )
    parser.add_argument(
        "fm_path",
        help="Path to feature model file (.uvl)"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Output YAML file path (default: data/bias-config/<model_name>.yaml)"
    )
    parser.add_argument(
        "--no-auto-cross-tree",
        action="store_true",
        help="Disable auto-generation of cross-tree constraints"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()
    return args

def load_feature_model(fm_path: str):
    """
    Load feature model from UVL file.

    Args:
        fm_path: Path to .uvl file

    Returns:
        Feature model object
    """
    from flamapy.metamodels.fm_metamodel.transformations import UVLReader

    if not Path(fm_path).exists():
        raise FileNotFoundError(f"Feature model not found: {fm_path}")

    reader = UVLReader(fm_path)
    return reader.transform()

# def extract_hierarchical_candidates(fm: FeatureModel) -> List[Dict[str, Any]]:
#
#     candidates = []
#
#     def process_feature(feature):
#         relations = feature.get_relations()
#
#         for relation in relations:
#             children = [child.name for child in relation.children]
#
#             if not children:
#                 continue
#
#             # Determine relationship type based on relation properties
#             if relation.is_mandatory() or relation.is_optional():
#                 # Binary relationship: one child at a time
#                 relationship_type = "binary"
#             elif relation.is_or() or relation.is_alternative():
#                 # Group relationship: multiple children
#                 relationship_type = "group"
#             else:
#                 # Default to binary for unknown types
#                 relationship_type = "binary"
#
#             candidate = {
#                 'parent': feature.name,
#                 'children': children,
#                 'relationship_type': relationship_type
#             }
#             candidates.append(candidate)
#
#         # Process children recursively
#         for child in feature.get_children():
#             process_feature(child)
#
#     process_feature(fm.root)
#     return candidates

def extract_hierarchical_candidates(fm: FeatureModel) -> List[Dict[str, Any]]:
    """
        Extract hierarchical relationships from feature model.

        Args:
            fm: Feature model object

        Returns:
            List of hierarchical candidate dictionaries
        """
    candidates = []

    for relationship in fm.get_relations():
        parent = relationship.parent.name
        children = [child.name for child in relationship.children]

        if not children:
            continue

        # Determine relationship type based on relation properties
        if relationship.is_mandatory() or relationship.is_optional():
            # Binary relationship: one child at a time
            relationship_type = "binary"
        elif relationship.is_or() or relationship.is_alternative():
            # Group relationship: multiple children
            relationship_type = "group"
        else:
            # Default to binary for unknown types
            relationship_type = "binary"

        candidate = {
            'parent': parent,
            'children': children,
            'relationship_type': relationship_type
        }
        candidates.append(candidate)
    return candidates

def extract_cross_tree_constraints(fm) -> List[Dict[str, Any]]:
    """
    Extract cross-tree constraints from feature model.

    Args:
        fm: Feature model object

    Returns:
        List of constraint info (for reference in comments)
    """
    constraints = []
    for ctc in fm.get_constraints():
        constraints.append({
            'text': str(ctc),
        })
    return constraints

def generate_yaml_content(
        name: str,
        features: List[str],
        hierarchical_candidates: List[Dict[str, Any]],
        cross_tree_constraints: List[Dict[str, Any]],
        auto_generate_cross_tree: bool = True
) -> str:
    """
    Generate YAML content for bias config.

    Args:
        name: Model name
        features: List of feature names
        hierarchical_candidates: List of hierarchical relationships
        cross_tree_constraints: List of cross-tree constraints (for comments)
        auto_generate_cross_tree: Whether to auto-generate cross-tree candidates

    Returns:
        YAML content as string
    """
    lines = [f"# Bias Config for {name} Feature Model",  # Header
             f"# Auto-generated from feature model",
             "",
             f"name: {name}",  # Model name
             "",
             "# List of all features in the model", "features:"]

    # Features
    for feature in features:
        lines.append(f"  - {feature}")
    lines.append("")

    # Hierarchical candidates
    lines.append("# Hierarchical relationship candidates")
    lines.append("# The generator will create constraints with allowed operators based on relationship_type")
    lines.append("hierarchical_candidates:")

    for candidate in hierarchical_candidates:
        parent = candidate['parent']
        children = candidate['children']
        rel_type = candidate['relationship_type']

        if rel_type == "binary":
            lines.append(f"  # Binary relationships: will generate with mandatory and optional operators")
        else:
            lines.append(f"  # Group relationships: will generate with alternative and or operators")

        lines.append(f"  - parent: {parent}")

        # Format children as inline list
        if len(children) == 1:
            lines.append(f"    children: [{children[0]}]")
        else:
            children_str = ", ".join(children)
            lines.append(f"    children: [{children_str}]")

        lines.append(f"    relationship_type: {rel_type}")
        lines.append("")

    # Cross-tree candidates
    lines.append("# Cross-tree constraint candidates")

    if cross_tree_constraints:
        lines.append("# Original cross-tree constraints from feature model:")
        for ctc in cross_tree_constraints:
            lines.append(f"#   {ctc['text']}")
        lines.append("#")

    lines.append("# auto_generate: true will create all possible requires and excludes for all feature pairs")
    lines.append("cross_tree_candidates:")
    lines.append(f"  auto_generate: {str(auto_generate_cross_tree).lower()}")
    lines.append("")

    return "\n".join(lines)


def main():
    args = parse_argument()

    # Load feature model
    if args.verbose:
        print(f"Loading feature model: {args.fm_path}")

    try:
        fm = load_feature_model(args.fm_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading feature model: {e}")
        sys.exit(1)

    # Extract model name from file
    model_name = Path(args.fm_path).stem

    if args.verbose:
        print(f"Model name: {model_name}")
        print(f"Root feature: {fm.root.name}")

    # Extract features
    features = [item.name for item in fm.get_features()]
    if args.verbose:
        print(f"Features: {len(features)}")

    # Extract hierarchical candidates
    hierarchical_candidates = extract_hierarchical_candidates(fm)
    if args.verbose:
        print(f"Hierarchical candidates: {len(hierarchical_candidates)}")

    # Extract cross-tree constraints
    cross_tree_constraints = extract_cross_tree_constraints(fm)
    if args.verbose:
        print(f"Cross-tree constraints: {len(cross_tree_constraints)}")

    # Generate YAML content
    yaml_content = generate_yaml_content(
        name=model_name,
        features=features,
        hierarchical_candidates=hierarchical_candidates,
        cross_tree_constraints=cross_tree_constraints,
        auto_generate_cross_tree=not args.no_auto_cross_tree
    )

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("data/bias-config") / f"{model_name}.yaml"

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML file
    with open(output_path, 'w') as f:
        f.write(yaml_content)

    print(f"Generated bias config: {output_path}")
    print(f"  Features: {len(features)}")
    print(f"  Hierarchical candidates: {len(hierarchical_candidates)}")
    print(f"  Cross-tree auto-generate: {not args.no_auto_cross_tree}")

if __name__ == "__main__":
    main()
