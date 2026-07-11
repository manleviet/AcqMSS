"""Architectural boundary guard — keep the three packages cleanly layered.

The repo is a three-tier stack with strictly one-directional dependencies::

    conacq        (application)      ── may use ──▶ explanation.api, profiling
      │
      ▼
    explanation   (framework)       ── may use ──▶ profiling
      │
      ▼
    profiling     (neutral leaf)    ── uses nothing but stdlib + itself

Each tier reaches the tier below ONLY through that tier's public façade, never
through submodule paths or underscore-private names. The leaf depends on
neither tier above it, so it stays a reusable, cycle-free port.

These tests parse every source file's imports with ``ast`` and pin the current,
clean state, enforcing five rules:

  (1) conacq → explanation : only ``explanation.api`` (no deep paths, no privates)
  (2) conacq → profiling   : only the ``profiling`` façade (no deep paths)
  (3) explanation → profiling : only the ``profiling`` façade (no deep paths)
  (4) explanation ⊥ conacq : the framework never imports the app
  (5) profiling is a leaf  : it never imports explanation or conacq

A red test means a real breach (an import cycle or a leaked internal), not a
false alarm — report it rather than loosening the rule.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONACQ_DIR = REPO_ROOT / "conacq"
EXPLANATION_DIR = REPO_ROOT / "explanation"
PROFILING_DIR = REPO_ROOT / "profiling"

# The sole façade module of each tier that the tier above may import from.
EXPLANATION_FACADE = frozenset({"explanation.api"})
PROFILING_FACADE = frozenset({"profiling"})


def _iter_source_files(root: Path):
    """Yield every ``.py`` file under ``root`` (skipping bytecode caches)."""
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _iter_imports(path: Path):
    """Yield ``(module, imported_name, lineno)`` for each absolute import.

    ``import a.b.c``        -> ("a.b.c", None, lineno)
    ``from a.b import c``   -> ("a.b", "c", lineno)

    Relative imports (``from . import x``) stay within their own package and can
    never cross a tier boundary, so they are skipped.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:  # relative import — intra-package
                continue
            module = node.module or ""
            for alias in node.names:
                yield module, alias.name, node.lineno


def _top_package(module: str) -> str:
    return module.split(".", 1)[0]


def _facade_breaches(root: Path, target_top: str, facade: frozenset) -> list:
    """Imports of ``target_top`` from ``root`` that bypass the façade.

    A breach is a deep submodule path (anything under ``target_top`` other than
    the blessed façade module) or an underscore-private symbol name.
    """
    allowed = " / ".join(sorted(facade))
    breaches = []
    for path in _iter_source_files(root):
        rel = path.relative_to(REPO_ROOT)
        for module, name, lineno in _iter_imports(path):
            if _top_package(module) != target_top:
                continue
            if module not in facade:
                breaches.append(f"{rel}:{lineno}: deep import `{module}` (route through {allowed})")
                continue
            if name is not None and name.startswith("_"):
                breaches.append(f"{rel}:{lineno}: private symbol `{name}` from `{module}`")
    return breaches


def _dependency_breaches(root: Path, forbidden_top: str) -> list:
    """Any import of ``forbidden_top`` from files under ``root``."""
    breaches = []
    for path in _iter_source_files(root):
        rel = path.relative_to(REPO_ROOT)
        for module, _name, lineno in _iter_imports(path):
            if _top_package(module) == forbidden_top:
                breaches.append(f"{rel}:{lineno}: imports `{module}`")
    return breaches


def test_conacq_imports_explanation_only_through_public_api():
    """(1) App reaches the framework solely via ``explanation.api``."""
    breaches = _facade_breaches(CONACQ_DIR, "explanation", EXPLANATION_FACADE)
    assert not breaches, "conacq → explanation breaches:\n  " + "\n  ".join(breaches)


def test_conacq_imports_profiling_only_through_facade():
    """(2) App reaches the profiling leaf solely via the ``profiling`` façade."""
    breaches = _facade_breaches(CONACQ_DIR, "profiling", PROFILING_FACADE)
    assert not breaches, "conacq → profiling breaches:\n  " + "\n  ".join(breaches)


def test_explanation_imports_profiling_only_through_facade():
    """(3) Framework reaches the profiling leaf solely via the ``profiling`` façade."""
    breaches = _facade_breaches(EXPLANATION_DIR, "profiling", PROFILING_FACADE)
    assert not breaches, "explanation → profiling breaches:\n  " + "\n  ".join(breaches)


def test_explanation_never_imports_conacq():
    """(4) Framework has zero knowledge of the app."""
    breaches = _dependency_breaches(EXPLANATION_DIR, "conacq")
    assert not breaches, (
        "explanation → conacq breaches (framework must not know app):\n  "
        + "\n  ".join(breaches)
    )


def test_profiling_is_a_leaf():
    """(5) The profiling leaf depends on neither tier above it."""
    breaches = _dependency_breaches(PROFILING_DIR, "explanation") + _dependency_breaches(
        PROFILING_DIR, "conacq"
    )
    assert not breaches, (
        "profiling is not a leaf (must not import explanation/conacq):\n  "
        + "\n  ".join(breaches)
    )
