"""
Feature Frequency (FF) generator for test case generation.

Ensures each feature appears in both True and False states
in both positive and negative examples.
"""

import random
from typing import Optional, Dict, Set, List, Tuple
from conacq.examples.data_structures import Example, ExampleSet, ExampleType
from .base import ExampleGenerator


class FeatureFrequencyGenerator(ExampleGenerator):
    """
    Feature Frequency (FF) generator.

    Generates examples ensuring each feature appears:
    - As True in at least one positive example
    - As False in at least one positive example
    - As True in at least one negative example
    - As False in at least one negative example

    This ensures 4-way coverage for each feature.

    Example:
        >>> oracle = FMOracle('model.uvl')
        >>> gen = FeatureFrequencyGenerator(oracle)
        >>> examples = gen.generate(max_examples=500)
    """

    def generate(self,
                 max_examples: int = 1000,
                 seed: Optional[int] = None) -> ExampleSet:
        """
        Generate examples with feature frequency coverage.

        Uses SAT solver to generate positive examples (valid configs)
        and random generation for negative examples (invalid configs).

        Args:
            max_examples: Maximum examples to generate before stopping
            seed: Random seed for reproducibility

        Returns:
            ExampleSet with FF coverage
        """
        self._rng = random.Random(seed)

        example_set = ExampleSet(metadata={
            'method': 'FF',
            'max_examples': max_examples,
            'seed': seed
        })

        # Track coverage: {feature: {True: {'pos', 'neg'}, False: {'pos', 'neg'}}}
        coverage: Dict[str, Dict[bool, Set[str]]] = {
            f: {True: set(), False: set()}
            for f in self.features
        }

        features_list = sorted(self.features)
        generated_configs = set()  # Avoid duplicates
        count = 0

        # Phase 1: Generate positive examples to cover E+ requirements
        pos_count = 0
        max_pos_attempts = max_examples * 10

        while not self._is_pos_covered(coverage) and pos_count < max_pos_attempts and count < max_examples:
            # Find uncovered (feature, value) for positive
            uncovered = self._get_uncovered_pos(coverage)
            if not uncovered:
                break

            # Try to generate a valid config that covers some uncovered requirements
            config = self._generate_valid_config_for_coverage(features_list, uncovered)
            if config:
                config_tuple = tuple(sorted(config.items()))
                if config_tuple not in generated_configs:
                    generated_configs.add(config_tuple)
                    example = Example(
                        id=f"ff_{count + 1}",
                        assignments=config,
                        example_type=ExampleType.POSITIVE
                    )
                    example_set.positive.append(example)

                    # Update coverage
                    for f, val in config.items():
                        coverage[f][val].add('pos')
                    count += 1

            pos_count += 1

        # Phase 2: Generate negative examples to cover E- requirements
        neg_count = 0
        max_neg_attempts = max_examples * 10

        while not self._is_neg_covered(coverage) and neg_count < max_neg_attempts and count < max_examples:
            # Find uncovered (feature, value) for negative
            uncovered = self._get_uncovered_neg(coverage)
            if not uncovered:
                break

            # Generate random config biased toward uncovered requirements
            config = self._generate_biased_invalid_config(features_list, uncovered)

            # Check if invalid
            if not self.oracle.is_valid(config):
                config_tuple = tuple(sorted(config.items()))
                if config_tuple not in generated_configs:
                    generated_configs.add(config_tuple)
                    example = Example(
                        id=f"ff_{count + 1}",
                        assignments=config,
                        example_type=ExampleType.NEGATIVE
                    )
                    example_set.negative.append(example)

                    # Update coverage
                    for f, val in config.items():
                        coverage[f][val].add('neg')
                    count += 1

            neg_count += 1

        # Add coverage statistics to metadata
        example_set.metadata['coverage'] = self._coverage_stats(coverage)
        example_set.metadata['fully_covered'] = self._is_covered(coverage)
        example_set.metadata['pos_attempts'] = pos_count
        example_set.metadata['neg_attempts'] = neg_count

        return example_set

    def _is_pos_covered(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> bool:
        """Check if all features covered in positive examples."""
        for f, vals in coverage.items():
            if 'pos' not in vals[True] or 'pos' not in vals[False]:
                return False
        return True

    def _is_neg_covered(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> bool:
        """Check if all features covered in negative examples."""
        for f, vals in coverage.items():
            if 'neg' not in vals[True] or 'neg' not in vals[False]:
                return False
        return True

    def _get_uncovered_pos(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> List[Tuple[str, bool]]:
        """Get list of (feature, value) pairs not yet covered in positive examples."""
        uncovered = []
        for f, vals in coverage.items():
            if 'pos' not in vals[True]:
                uncovered.append((f, True))
            if 'pos' not in vals[False]:
                uncovered.append((f, False))
        return uncovered

    def _get_uncovered_neg(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> List[Tuple[str, bool]]:
        """Get list of (feature, value) pairs not yet covered in negative examples."""
        uncovered = []
        for f, vals in coverage.items():
            if 'neg' not in vals[True]:
                uncovered.append((f, True))
            if 'neg' not in vals[False]:
                uncovered.append((f, False))
        return uncovered

    def _generate_valid_config_for_coverage(
            self,
            features_list: List[str],
            uncovered: List[Tuple[str, bool]]
    ) -> Optional[Dict[str, bool]]:
        """
        Generate a valid configuration that covers some uncovered requirements.

        Args:
            features_list: List of all features
            uncovered: List of (feature, value) pairs to try to cover

        Returns:
            Valid configuration dict, or None if failed
        """
        self._rng.shuffle(uncovered)
        target_feature, target_value = uncovered[0]

        # Build partial with target + random extras for diversity
        partial = {target_feature: target_value}
        other_features = [f for f in features_list if f != target_feature]
        self._rng.shuffle(other_features)
        n_extra = min(len(other_features) // 3, 5)
        for f in other_features[:n_extra]:
            partial[f] = self._rng.choice([True, False])

        # Try full partial, then target-only fallback
        config = self.oracle.complete_configuration(partial)
        if config is None:
            config = self.oracle.complete_configuration({target_feature: target_value})
        return config

    def _generate_biased_invalid_config(
            self,
            features_list: List[str],
            uncovered: List[Tuple[str, bool]]
    ) -> Dict[str, bool]:
        """
        Generate a random configuration biased toward covering uncovered requirements.

        Args:
            features_list: List of all features
            uncovered: List of (feature, value) pairs to try to cover

        Returns:
            Configuration dict (may be valid or invalid)
        """
        # Start with random
        config = {f: self._rng.choice([True, False]) for f in features_list}

        # Bias toward uncovered requirements
        self._rng.shuffle(uncovered)
        for f, val in uncovered[:5]:  # Try to satisfy up to 5 uncovered
            config[f] = val

        return config

    def _is_covered(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> bool:
        """
        Check if all features covered in all 4 contexts.

        Args:
            coverage: Coverage tracking dictionary

        Returns:
            True if every feature appears as True/False in both pos/neg examples
        """
        for f, vals in coverage.items():
            for val in [True, False]:
                if len(vals[val]) < 2:  # Need both 'pos' and 'neg'
                    return False
        return True

    def _coverage_stats(self, coverage: Dict[str, Dict[bool, Set[str]]]) -> Dict:
        """
        Calculate coverage statistics.

        Args:
            coverage: Coverage tracking dictionary

        Returns:
            Dictionary with coverage statistics
        """
        total_needed = len(self.features) * 4  # features × 2 values × 2 types
        covered = 0

        uncovered_features = []

        for f, vals in coverage.items():
            f_covered = len(vals[True]) + len(vals[False])
            covered += f_covered

            if f_covered < 4:
                missing = []
                if 'pos' not in vals[True]:
                    missing.append('True/pos')
                if 'neg' not in vals[True]:
                    missing.append('True/neg')
                if 'pos' not in vals[False]:
                    missing.append('False/pos')
                if 'neg' not in vals[False]:
                    missing.append('False/neg')
                uncovered_features.append({'feature': f, 'missing': missing})

        return {
            'total_needed': total_needed,
            'covered': covered,
            'percentage': covered / total_needed * 100,
            'uncovered_features': uncovered_features[:10]  # Limit for readability
        }
