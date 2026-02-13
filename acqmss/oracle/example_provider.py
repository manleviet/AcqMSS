"""
Example provider for example-based QuAcq evaluation.

Provides shuffled examples from a mixed pool one at a time.
"""

import random
from typing import Dict, List, Optional


class ExampleProvider:
    """Provides examples from a shuffled mixed pool (no E+/E- distinction).

    Used for example-based QuAcq evaluation. Examples are shuffled
    with a reproducible seed and yielded one at a time.
    """

    def __init__(self, examples: List[Dict[str, bool]], seed: int = None):
        """Initialize with mixed example pool.

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
