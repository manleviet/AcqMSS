"""FrozenDict: an immutable ``dict`` used to deep-freeze mapping-valued fields.

Lives in its own module so both ``task_preparation`` (Task.negation_map) and
``assignment_assumption_map`` can import it without a cycle (task_preparation
imports AssignmentAssumptionMap at module load, before FrozenDict would be defined
inline). Re-exported through ``explanation.api`` for the conacq layer.
"""


class FrozenDict(dict):
    """An immutable ``dict``: every mutator raises, so a stored mapping cannot drift.

    Mapping-valued frozen-dataclass fields (``negation_map``, assignment maps) are
    read-only after construction (``in`` and ``[key]`` only), so the deep-freeze that
    coerces list fields to tuples extends here too. Unlike the abandoned
    ``MappingProxyType`` (ADR-0007) it *pickles* — required by FastDiagP, which
    ships the task to worker processes — via
    ``__reduce__`` reconstructing from a plain ``dict`` (so unpickling never calls the
    blocked ``__setitem__``). ``__ior__`` (``|=``, Python 3.9+) is blocked too.
    """
    __slots__ = ()

    def _no(self, *args, **kwargs):
        raise TypeError("FrozenDict is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _no

    def __reduce__(self):
        # Reconstruct from a plain dict so pickle/deepcopy bypass __setitem__.
        return (FrozenDict, (dict(self),))
