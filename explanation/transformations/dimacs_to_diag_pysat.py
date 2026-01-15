from typing import List, Tuple, Dict

from flamapy.core.exceptions import FlamaException
from flamapy.metamodels.pysat_metamodel.models import PySATModel
from flamapy.metamodels.pysat_metamodel.transformations import DimacsReader

from explanation.models.pysat_diagnosis_model import DiagnosisModel


class DimacsToDiagPysat(DimacsReader):

    @staticmethod
    def get_source_extension() -> str:
        return 'dimacs'

    def __init__(self, path: str) -> None:
        super().__init__(path)

    def transform(self) -> PySATModel:
        with open(self.path, 'r', encoding='utf-8') as file:
            lines = file.read().splitlines()
            features_lines = [line for line in lines if line.startswith('c')]
            problem = next((line for line in lines if line.startswith('p')), None)
            clauses_lines = [line for line in lines if line and not line.startswith(('c', 'p'))]

        if problem is None:
            raise FlamaException(f'Incorrect Dimacs format of {self.path}. No problem statement.')

        problem_list = problem.split()
        n_clauses = int(problem_list[3])
        if n_clauses != len(clauses_lines):
            raise FlamaException(f'Incorrect Dimacs format of {self.path}. Inconsistent number of clauses.')

        features, variables = self._parse_features_variables(features_lines)

        model = DiagnosisModel()
        model.features = features
        model.variables = variables

        self._parse_clauses(model, clauses_lines)

        return model

    def _parse_features_variables(self, lines: List[str]) -> Tuple[Dict[int, str], Dict[str, int]]:
        features = {int(line.split()[1]): line.split()[2] for line in lines}
        variables = {line.split()[2]: int(line.split()[1]) for line in lines}
        return features, variables

    def _parse_clauses(self, model: DiagnosisModel, lines: List[str]) -> None:
        for line in lines:
            clause = [int(c) for c in line.split() if c != '0']
            model.add_clause(clause)
            model.add_clause_to_map(line, [clause])
