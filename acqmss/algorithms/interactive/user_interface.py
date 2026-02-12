"""
Oracle interfaces for interactive constraint acquisition.

Provides different oracle implementations:
- AutomatedOracle: Uses FeatureModelOracle for automated experiments
- UserPromptOracle: Prompts human expert for truly interactive mode
"""

import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from acqmss.testcases.oracle import FeatureModelOracle


class InteractiveOracle(ABC):
    """
    Abstract oracle interface for interactive learning.

    An oracle answers membership queries: is this configuration valid?
    """

    @abstractmethod
    def ask(self, query: Dict[str, bool]) -> bool:
        """
        Ask oracle if configuration is valid.

        Args:
            query: Configuration as {feature_name: True/False}

        Returns:
            True if configuration is valid (belongs to target language)
        """
        pass

    @abstractmethod
    def get_feature_count(self) -> int:
        """Get the number of features."""
        pass


class AutomatedOracle(InteractiveOracle):
    """
    Automated oracle using feature model as ground truth.

    Used for experiments where the ground truth is known.
    Automatically answers membership queries using SAT solving.

    Example:
        >>> oracle = AutomatedOracle('data/fms/model.uvl')
        >>> oracle.ask({'root': True, 'child': False})
        True
    """

    def __init__(self, fm_path: str):
        """
        Initialize automated oracle from feature model.

        Args:
            fm_path: Path to feature model file (.uvl format)
        """
        self.fm_oracle = FeatureModelOracle(fm_path)

    def ask(self, query: Dict[str, bool]) -> bool:
        """
        Answer membership query using SAT solver.

        Args:
            query: Configuration as {feature_name: True/False}

        Returns:
            True if configuration satisfies the feature model
        """
        return self.fm_oracle.is_valid(query)

    def get_feature_count(self) -> int:
        """Get the number of features in the feature model."""
        return len(self.fm_oracle.features)

    def get_features(self):
        """Get all feature names."""
        return self.fm_oracle.get_features()

    def get_feature_ids(self):
        """Get feature name to SAT variable ID mapping."""
        return self.fm_oracle.get_feature_ids()

    def get_root_feature(self) -> str:
        """Get the root feature name from the feature model."""
        return self.fm_oracle.get_root_feature()

    def __repr__(self):
        return f"AutomatedOracle(features={len(self.fm_oracle.features)})"


class UserPromptOracle(InteractiveOracle):
    """
    Interactive oracle that prompts user for answers.

    Used for truly interactive constraint acquisition where
    a human expert answers membership queries.

    Example:
        >>> oracle = UserPromptOracle(features=['A', 'B', 'C'])
        >>> answer = oracle.ask({'A': True, 'B': False, 'C': True})
        Query: A=True, B=False, C=True
        Is this configuration valid? (y/n):
    """

    def __init__(self, features: list, verbose: bool = True):
        """
        Initialize user prompt oracle.

        Args:
            features: List of feature names
            verbose: If True, show detailed query information
        """
        self.features = set(features)
        self.verbose = verbose
        self._query_count = 0

    def ask(self, query: Dict[str, bool]) -> bool:
        """
        Prompt user for membership query answer.

        Args:
            query: Configuration as {feature_name: True/False}

        Returns:
            True if user answers 'y' or 'yes'
        """
        self._query_count += 1

        # Format query for display
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Query #{self._query_count}")
            print(f"{'='*60}")

            # Show selected features
            selected = sorted([f for f, v in query.items() if v])
            deselected = sorted([f for f, v in query.items() if not v])

            print(f"Selected features ({len(selected)}):")
            for f in selected:
                print(f"  + {f}")

            if deselected:
                print(f"\nDeselected features ({len(deselected)}):")
                for f in deselected[:10]:  # Show first 10
                    print(f"  - {f}")
                if len(deselected) > 10:
                    print(f"  ... and {len(deselected) - 10} more")
        else:
            # Compact format
            config_str = ', '.join(f"{k}={v}" for k, v in sorted(query.items())[:5])
            if len(query) > 5:
                config_str += f", ... ({len(query) - 5} more)"
            print(f"\nQuery #{self._query_count}: {config_str}")

        # Get user answer
        while True:
            answer = input("\nIs this configuration valid? (y/n): ").strip().lower()
            if answer in ('y', 'yes', '1', 'true'):
                return True
            elif answer in ('n', 'no', '0', 'false'):
                return False
            else:
                print("Please answer 'y' for yes or 'n' for no.")

    def get_feature_count(self) -> int:
        """Get the number of features."""
        return len(self.features)

    def get_query_count(self) -> int:
        """Get number of queries asked so far."""
        return self._query_count

    def __repr__(self):
        return f"UserPromptOracle(features={len(self.features)}, queries={self._query_count})"


class CachedOracle(InteractiveOracle):
    """
    Oracle wrapper that caches answers to avoid redundant queries.

    Useful when the same configuration might be queried multiple times.

    Example:
        >>> base_oracle = AutomatedOracle('model.uvl')
        >>> oracle = CachedOracle(base_oracle)
        >>> oracle.ask({'A': True})  # Asks base oracle
        >>> oracle.ask({'A': True})  # Returns cached answer
    """

    def __init__(self, base_oracle: InteractiveOracle):
        """
        Initialize cached oracle.

        Args:
            base_oracle: Underlying oracle to cache
        """
        self.base_oracle = base_oracle
        self._cache: Dict[tuple, bool] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _config_to_key(self, config: Dict[str, bool]) -> tuple:
        """Convert configuration to hashable cache key."""
        return tuple(sorted(config.items()))

    def ask(self, query: Dict[str, bool]) -> bool:
        """
        Answer query, using cache if available.

        Args:
            query: Configuration as {feature_name: True/False}

        Returns:
            Cached or fresh answer from base oracle
        """
        key = self._config_to_key(query)

        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]

        self._cache_misses += 1
        answer = self.base_oracle.ask(query)
        self._cache[key] = answer
        return answer

    def get_feature_count(self) -> int:
        """Get the number of features."""
        return self.base_oracle.get_feature_count()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'size': len(self._cache)
        }

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def __repr__(self):
        return (f"CachedOracle(hits={self._cache_hits}, "
                f"misses={self._cache_misses}, size={len(self._cache)})")


class ExampleProvider:
    """
    Provides examples from a shuffled mixed pool (no E+/E- distinction).

    Used for example-based QuAcq evaluation. Examples are shuffled
    with a reproducible seed and yielded one at a time.
    """

    def __init__(self, examples: List[Dict[str, bool]], seed: int = None):
        """
        Initialize with mixed example pool.

        Args:
            examples: Mixed list of examples (no E+/E- distinction)
            seed: Random seed for reproducible shuffling
        """
        self._examples = list(examples)
        if seed is not None:
            random.Random(seed).shuffle(self._examples)
        else:
            random.shuffle(self._examples)
        self._index = 0

    def next_example(self) -> Optional[Dict[str, bool]]:
        """Pick next example from shuffled pool. None when exhausted."""
        if self._index >= len(self._examples):
            return None
        e = self._examples[self._index]
        self._index += 1
        return e

    def is_exhausted(self) -> bool:
        """Check if all examples have been consumed."""
        return self._index >= len(self._examples)

    def remaining(self) -> int:
        """Number of examples remaining in pool."""
        return len(self._examples) - self._index

    def __repr__(self):
        return (f"ExampleProvider(total={len(self._examples)}, "
                f"used={self._index}, remaining={self.remaining()})")
