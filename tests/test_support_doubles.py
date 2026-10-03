import ast
from pathlib import Path

import pytest

from reality.extraction.contracts import DroppedClaim
from reality.extraction.provider import Provider
from reality.provider_errors import ProviderTimeout
from reality.schemas import Observation
from tests.support.fake_provider import ScriptedProvider, ScriptExhausted
from tests.support.recording_sink import RecordingSink

FAKE_SOURCE = Path(__file__).resolve().parent / "support" / "fake_provider.py"
FORBIDDEN_IMPORTS = ("sqlite3", "random", "time", "datetime",
                     "reality.db", "reality.repository", "reality.engine")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_scripted_provider_satisfies_the_provider_contract_and_touches_no_storage():
    assert isinstance(ScriptedProvider(), Provider)

    offenders = sorted(
        m for m in _imported_modules(FAKE_SOURCE)
        if any(m == f or m.startswith(f + ".") for f in FORBIDDEN_IMPORTS)
    )
    assert offenders == []


def test_scripted_values_are_returned_by_identity_and_never_repaired():
    malformed = [{"not": "validated"}, ["a"], "plain string", None, 42]
    provider = ScriptedProvider(*malformed)
    obs = Observation.model_construct(id=1)

    for expected in malformed:
        assert provider.extract(obs) is expected


def test_scripted_failures_raise_the_very_same_exception_object_in_sequence():
    exc = ProviderTimeout("slow")
    value = [{"predicate": "p"}]
    provider = ScriptedProvider(exc, value)
    obs = Observation.model_construct(id=1)

    with pytest.raises(ProviderTimeout) as caught:
        provider.extract(obs)
    assert caught.value is exc

    assert provider.extract(obs) is value


def test_every_observation_received_is_recorded_in_order():
    first, second = Observation.model_construct(id=1), Observation.model_construct(id=2)
    provider = ScriptedProvider([], [])

    provider.extract(first)
    provider.extract(second)

    assert len(provider.calls) == 2
    assert provider.calls[0] is first
    assert provider.calls[1] is second


def test_calling_beyond_the_script_fails_loudly():
    obs = Observation.model_construct(id=1)

    with pytest.raises(ScriptExhausted):
        ScriptedProvider().extract(obs)

    provider = ScriptedProvider([])
    provider.extract(obs)
    with pytest.raises(ScriptExhausted):
        provider.extract(obs)
    assert len(provider.calls) == 2


def test_recording_sink_keeps_the_same_drop_objects_in_order():
    first = DroppedClaim(stage="normalization", reason="one", payload_projection={})
    second = DroppedClaim(stage="validation", reason="two", payload_projection={})
    sink = RecordingSink()

    sink.record(first)
    sink.record(second)

    assert len(sink.drops) == 2
    assert sink.drops[0] is first
    assert sink.drops[1] is second