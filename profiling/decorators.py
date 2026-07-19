"""Instance-aware profiling decorators (concern: measure_time / count_calls)."""
import time
from functools import wraps
from typing import Callable

from .registry import get_global_profiler


def measure_time(key: str) -> Callable:
    """
    Decorator to measure function/method execution time.

    Works with both standalone functions and instance methods.
    For instance methods, uses self.profiler if available.
    Otherwise, falls back to get_global_profiler().

    Args:
        key: Metric name for timing data

    Returns:
        Decorated function

    Example (instance method):
        class MyAlgorithm:
            def __init__(self, profiler_instance=None):
                self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

            @measure_time('operation_runtime')
            def operation(self):
                # ... algorithm logic ...
                pass

    Example (standalone function):
        @measure_time('function_runtime')
        def my_function(x):
            return x * 2
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Detect context: instance method vs standalone function
            # If first arg has 'profiler' attribute, it's likely 'self' from instance method
            if args and hasattr(args[0], 'profiler'):
                prof = args[0].profiler
            else:
                prof = get_global_profiler()

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                prof.record_time(key, duration)

        return wrapper

    return decorator


def count_calls(key: str) -> Callable:
    """
    Decorator to count function/method calls.

    Works with both standalone functions and instance methods.
    For instance methods, uses self.profiler if available.
    Otherwise, falls back to get_global_profiler().

    Args:
        key: Metric name for call counter

    Returns:
        Decorated function

    Example (instance method):
        class MyAlgorithm:
            def __init__(self, profiler_instance=None):
                self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

            @count_calls('operation_calls')
            def operation(self):
                # ... algorithm logic ...
                pass

    Example (standalone function):
        @count_calls('function_calls')
        def my_function(x):
            return x * 2
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Detect context: instance method vs standalone function
            # If first arg has 'profiler' attribute, it's likely 'self' from instance method
            if args and hasattr(args[0], 'profiler'):
                prof = args[0].profiler
            else:
                prof = get_global_profiler()

            try:
                result = func(*args, **kwargs)
                prof.increment(key)
                return result
            except Exception:
                # Still count the call even if it fails
                prof.increment(key)
                raise

        return wrapper

    return decorator
