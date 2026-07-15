"""Universal base for the fluent model builders.

``AbstractModelBuilder`` factors the shape shared by every model builder — a
``build()`` template (validate, then construct) — without knowing anything about
the concrete model or its source. It lives in the framework and MUST NOT
reference the application (``conacq``); the boundary guard enforces that.

Two builders inherit it:

- ``DiagnosisModelBuilder`` (this package) — builds a ``DiagnosisModel`` from a
  file / feature-model source.
- ``OracleBiasModelBuilder`` (in ``conacq``) — builds bias+oracle models
  (ConGen, QuAcq); it inherits this base through ``explanation.api``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TModel = TypeVar("TModel")


class AbstractModelBuilder(ABC, Generic[TModel]):
    """Fluent-builder base: a ``build()`` template over two hooks.

    ``build()`` is a template method — validate the builder state, then construct
    the model. Subclasses supply the two hooks (``_validate`` and
    ``_create_model``); they never override ``build()`` itself. ``TModel`` is the
    concrete model each builder produces (a subclass parametrises it, e.g.
    ``AbstractModelBuilder[DiagnosisModel]``), so ``build`` is typed, not ``Any``.
    """

    def build(self) -> TModel:
        """Validate the builder state, then construct and return the model."""
        self._validate()
        return self._create_model()

    @abstractmethod
    def _validate(self) -> None:
        """Raise ``ValueError`` if the configured builder state is invalid."""
        ...

    @abstractmethod
    def _create_model(self) -> TModel:
        """Construct and return the model from the validated builder state."""
        ...
