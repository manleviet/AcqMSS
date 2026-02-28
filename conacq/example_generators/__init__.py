"""Example generators for different sampling strategies."""

from .base import ExampleGenerator
from .random_sampling import RandomSamplingGenerator, BalancedRandomSamplingGenerator, ControlledRandomSamplingGenerator
from .feature_frequency import FeatureFrequencyGenerator
from .nwise_coverage import NWiseCoverageGenerator, TwoCoverageGenerator


# QueryProvider is lazily imported to avoid circular dependency:
# example_generators/__init__ -> query_provider -> algorithms.quacq.sat_utils
def __getattr__(name):
    if name in ('QueryProvider', 'clause_count_priority', 'literal_count_priority'):
        from .query_provider import QueryProvider, clause_count_priority, literal_count_priority
        globals()['QueryProvider'] = QueryProvider
        globals()['clause_count_priority'] = clause_count_priority
        globals()['literal_count_priority'] = literal_count_priority
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'ExampleGenerator',
    'RandomSamplingGenerator',
    'BalancedRandomSamplingGenerator',
    'ControlledRandomSamplingGenerator',
    'FeatureFrequencyGenerator',
    'NWiseCoverageGenerator',
    'TwoCoverageGenerator',
    'QueryProvider',
    'clause_count_priority',
    'literal_count_priority',
]
