"""Example generators for different sampling strategies."""

from .base import ExampleGenerator
from .random_sampling import RandomSamplingGenerator, BalancedRandomSamplingGenerator, ControlledRandomSamplingGenerator
from .feature_frequency import FeatureFrequencyGenerator
from .nwise_coverage import NWiseCoverageGenerator, TwoCoverageGenerator
from .example_provider import ExampleProvider

# QueryGenerator is lazily imported to avoid circular dependency:
# example_generators/__init__ -> query_generator -> algorithms.quacq._task_compat
# -> algorithms/__init__ -> acqmss/__init__ -> quacq/__init__ -> quacq.py
# -> quacq.py imports from example_generators (circular!)


def __getattr__(name):
    if name in ('QueryGenerator', 'clause_count_priority', 'literal_count_priority'):
        from .query_generator import QueryGenerator, clause_count_priority, literal_count_priority
        globals()['QueryGenerator'] = QueryGenerator
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
    'QueryGenerator',
    'clause_count_priority',
    'literal_count_priority',
    'ExampleProvider',
]
