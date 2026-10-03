import ast
from pathlib import Path

import pytest

from reality import provider_errors
from reality.classification import exceptions as classification_exceptions
from reality.classification.exceptions import ClassificationError
from reality.extraction import pipeline as extraction_pipeline
from reality.extraction.errors import ExtractionError

REPO = Path(__file__).resolve().parent.parent
FAMILY = ("ProviderError", "ProviderUnavailable", "ProviderTimeout", "ProviderInvalidResponse")


def _imported_modules(path: Path) -> set[str]:
    """Absolute module names a source file imports (the codebase uses absolute imports)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_provider_failures_form_one_neutral_family_outside_both_pipeline_families():
    base = provider_errors.ProviderError
    assert issubclass(base, Exception)

    for name in FAMILY[1:]:
        assert issubclass(getattr(provider_errors, name), base)

    for name in FAMILY:
        cls = getattr(provider_errors, name)
        assert not issubclass(cls, ClassificationError)
        assert not issubclass(cls, ExtractionError)


def test_classification_reexports_are_the_very_same_objects():
    for name in FAMILY:
        assert getattr(classification_exceptions, name) is getattr(provider_errors, name)
        assert name in classification_exceptions.__all__


def test_extraction_pipeline_uses_the_neutral_family():
    assert extraction_pipeline.ProviderError is provider_errors.ProviderError


@pytest.mark.parametrize(
    "paths, forbidden, label",
    [
        pytest.param(
            sorted((REPO / "reality" / "extraction").glob("*.py")),
            "reality.classification",
            "extraction-must-not-import-classification",
            id="extraction-does-not-import-classification",
        ),
        pytest.param(
            [REPO / "reality" / "provider_errors.py"],
            "reality",
            "neutral-module-imports-nothing-from-reality",
            id="neutral-module-imports-nothing-from-reality",
        ),
    ],
)
def test_dependency_direction(paths, forbidden, label):
    assert paths, f"{label}: no source files found"
    offenders = {
        path.name: sorted(
            m for m in _imported_modules(path)
            if m == forbidden or m.startswith(forbidden + ".")
        )
        for path in paths
    }
    assert {name: mods for name, mods in offenders.items() if mods} == {}