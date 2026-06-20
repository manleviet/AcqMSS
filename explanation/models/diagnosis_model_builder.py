"""Builder for creating DiagnosisModel (KB) instances.

The builder constructs the immutable knowledge base only — it loads/transforms a
feature model and optionally creates negated constraint forms (a KB property).
Per-task inputs (configuration, test cases, redundancy usage, incremental mode)
are NOT set here: pass them to ``model.prepare_task(TaskInput(...))`` and choose
the solver via the operation builder's ``with_incremental``/``with_solver``.
"""
from typing import Optional

from flamapy.metamodels.fm_metamodel.models import FeatureModel

from .pysat_diagnosis_model import DiagnosisModel


class DiagnosisModelBuilder:
    """Fluent builder that produces a KB-only DiagnosisModel.

    The builder constructs only the immutable KB; the task type is chosen later
    by the TaskInput passed to ``model.prepare_task(...)``. The single KB-level
    option here is ``with_negation()`` (creates negated constraint forms, needed
    only by WipeOutR_FM).

    End-to-end use cases (KB build → prepare_task input → task):

    | Use Case             | KB build (this builder)        | prepare_task(TaskInput(...))                                   | Task Type     |
    |----------------------|--------------------------------|---------------------------------------------------------------|---------------|
    | 1. Config diagnosis  | .build()                       | configuration=cfg                                             | DiagnosisTask |
    | 2. Config + FM       | .build()                       | configuration=cfg, with_cf_in_c=True                         | DiagnosisTask |
    | 3. FM diagnosis      | .build()                       | () (defaults)                                                | DiagnosisTask |
    | 4. Error diagnosis   | .build()                       | test_case=tc                                                 | DiagnosisTask |
    | 5. KBDiag            | .build()                       | positive_test_cases=tc, negative_test_cases=tv               | TestCaseTask  |
    | 6. WipeOutR_T        | .build()                       | positive_test_cases=ts, for_redundancy=True                  | TestCaseTask  |
    | 7. WipeOutR_FM       | .with_negation().build()       | for_redundancy=True                                          | DiagnosisTask |
    | 8. CXPlain (future)  | .build()                       | requirement=req, configuration=cfg, sub_configuration=sc     | DiagnosisTask |

    Examples:
        # Use Case 1: Configuration diagnosis
        model = DiagnosisModelBuilder.from_fide("smartwatch.xml").build()
        task = model.prepare_task(TaskInput(configuration=config))

        # Use Case 5: KBDiag with test cases
        model = DiagnosisModelBuilder.from_uvl("feature_model.uvl").build()
        task = model.prepare_task(TaskInput(
            positive_test_cases=positive_ts, negative_test_cases=negative_ts))

        # Use Case 7: FM redundancy detection (negated forms created at transform time)
        model = DiagnosisModelBuilder.from_uvl("redundant_fm.uvl").with_negation().build()
        task = model.prepare_task(TaskInput(for_redundancy=True))
    """

    def __init__(self):
        """Initialize builder with default values."""
        # Source configuration
        self._source_type: Optional[str] = None
        self._source_path: Optional[str] = None
        self._feature_model: Optional[FeatureModel] = None

        # KB-level: whether to create negated constraint forms (WipeOutR_FM).
        self._create_negation: bool = False

    # === Source Methods (class methods) ===

    @classmethod
    def from_fide(cls, path: str) -> 'DiagnosisModelBuilder':
        """Create builder from FeatureIDE XML file."""
        builder = cls()
        builder._source_type = 'fide'
        builder._source_path = path
        return builder

    @classmethod
    def from_uvl(cls, path: str) -> 'DiagnosisModelBuilder':
        """Create builder from UVL file."""
        builder = cls()
        builder._source_type = 'uvl'
        builder._source_path = path
        return builder

    @classmethod
    def from_dimacs(cls, path: str) -> 'DiagnosisModelBuilder':
        """Create builder from DIMACS CNF file."""
        builder = cls()
        builder._source_type = 'dimacs'
        builder._source_path = path
        return builder

    @classmethod
    def from_feature_model(cls, fm: FeatureModel) -> 'DiagnosisModelBuilder':
        """Create builder from existing FeatureModel object."""
        builder = cls()
        builder._source_type = 'feature_model'
        builder._feature_model = fm
        return builder

    # === KB options ===

    def with_negation(self, enabled: bool = True) -> 'DiagnosisModelBuilder':
        """Create negated constraint forms in the KB (needed for WipeOutR_FM).

        This is a KB property (it populates ``negated_constraint_map``). Whether a
        given task *uses* the negated forms is a separate per-task decision via
        ``TaskInput(for_redundancy=True)``.
        """
        self._create_negation = enabled
        return self

    # Backwards-readable alias kept for redundancy KBs; same KB-level meaning.
    for_redundancy = with_negation

    # === Build ===

    def build(self) -> DiagnosisModel:
        """Build and return the KB-only DiagnosisModel.

        Raises:
            ValueError: If source is not specified.
        """
        if self._source_path is None and self._feature_model is None:
            raise ValueError(
                "Source must be specified (use from_fide/from_uvl/from_dimacs/from_feature_model)")
        return self._create_model()

    def _create_model(self) -> DiagnosisModel:
        """Create DiagnosisModel from source. Lazy imports avoid circular deps."""
        needs_negation = self._create_negation

        if self._source_type == 'fide':
            from flamapy.metamodels.fm_metamodel.transformations import FeatureIDEReader
            from ..transformations.fm_to_diag_pysat import FmToDiagPysat

            fm = FeatureIDEReader(self._source_path).transform()
            return FmToDiagPysat(fm, create_negation=needs_negation).transform()

        elif self._source_type == 'uvl':
            from flamapy.metamodels.fm_metamodel.transformations import UVLReader
            from ..transformations.fm_to_diag_pysat import FmToDiagPysat

            fm = UVLReader(self._source_path).transform()
            return FmToDiagPysat(fm, create_negation=needs_negation).transform()

        elif self._source_type == 'dimacs':
            from ..transformations.dimacs_to_diag_pysat import DimacsToDiagPysat

            return DimacsToDiagPysat(self._source_path, create_negation=needs_negation).transform()

        elif self._source_type == 'feature_model':
            from ..transformations.fm_to_diag_pysat import FmToDiagPysat

            return FmToDiagPysat(self._feature_model, create_negation=needs_negation).transform()

        raise ValueError(f"Unknown source type: {self._source_type}")
