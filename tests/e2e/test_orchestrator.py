import ast
import dataclasses
import sqlite3
import time
from pathlib import Path

import pytest

from reality import db, orchestrator
from reality.db import transaction
from reality.engine import AssertionResult, ContradictoryTypeField
from reality.extraction.errors import ExtractionInternalError, ExtractionMalformedOutput
from reality.orchestrator import OrchestrationResult, ingest_observation
from reality.provider_errors import (
    ProviderError,
    ProviderInvalidResponse,
    ProviderTimeout,
    ProviderUnavailable,
)
from reality.schemas import Assertion, Observation
from tests.support.fake_provider import ScriptedProvider
from tests.support.recording_sink import RecordingSink

ORCHESTRATOR_SOURCE = Path(__file__).resolve().parents[2] / "reality" / "orchestrator.py"
FORBIDDEN_IMPORTS = ("sqlite3", "reality.db", "reality.repository", "reality.classification")
ALLOWED_IMPORTS = {
    "dataclasses",
    "reality.engine",
    "reality.extraction.audit",
    "reality.extraction.contracts",
    "reality.extraction.pipeline",
    "reality.extraction.provider",
    "reality.provider_errors",
    "reality.schemas",
}


def _rel(**overrides):
    fields = {
        "assertion_type": "relationship",
        "subject_text": "Sara", "subject_type": "Person",
        "predicate": "works_at",
        "object_text": "Acme", "object_type": "Company",
    }
    fields.update(overrides)
    return fields


def _attr(**overrides):
    fields = {
        "assertion_type": "attribute",
        "subject_text": "Sara", "subject_type": "Person",
        "predicate": "mood", "object_text": "happy",
    }
    fields.update(overrides)
    return fields


def _obs(text: str = "Sara works at Acme") -> Observation:
    return Observation(raw_text=text)


def _count(table: str) -> int:
    with transaction() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _counts() -> tuple[int, int, int, int]:
    """(observations, assertions, entities, relationships)"""
    return tuple(_count(t) for t in ("observations", "assertions", "entities", "relationships"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class _FailingSink:
    def record(self, drop):
        raise RuntimeError("audit disk full")


class _LockProbingProvider:
    """Proves no write transaction is held while the provider runs."""

    def __init__(self):
        self.probed = False

    def extract(self, observation):
        conn = sqlite3.connect(db.DB_PATH, timeout=0.1, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")  # fails fast if a write lock is held
            conn.execute("ROLLBACK")
        finally:
            conn.close()
        self.probed = True
        return []


# ---------------------------------------------------------------------------
# Completed runs
# ---------------------------------------------------------------------------

def test_happy_path_returns_a_completed_result():
    provider, sink = ScriptedProvider([_rel()]), RecordingSink()

    result = ingest_observation(_obs(), provider=provider, audit_sink=sink)

    assert isinstance(result, OrchestrationResult)
    assert isinstance(result.observation.id, int)
    assert result.observation.raw_text == "Sara works at Acme"
    assert provider.calls[0] is result.observation
    assert len(result.outcomes) == 1
    assert isinstance(result.outcomes[0], AssertionResult)
    assert result.outcomes[0].assertion.observation_id == result.observation.id
    assert (result.normalization_drops, result.validation_drops, result.provider_attempts) == (0, 0, 1)
    assert sink.drops == []
    assert _counts() == (1, 1, 2, 1)


def test_a_valid_empty_output_is_a_completed_run_not_a_failure():
    result = ingest_observation(_obs(), provider=ScriptedProvider([]), audit_sink=RecordingSink())

    assert result.outcomes == ()
    assert (result.normalization_drops, result.validation_drops) == (0, 0)
    assert _counts() == (1, 0, 0, 0)


def test_a_normalization_drop_is_counted_and_audited_and_the_valid_sibling_is_applied():
    sink = RecordingSink()

    result = ingest_observation(_obs(), provider=ScriptedProvider([_rel(), "junk"]), audit_sink=sink)

    assert (result.normalization_drops, result.validation_drops) == (1, 0)
    assert len(sink.drops) == 1 and sink.drops[0].stage == "normalization"
    assert len(result.outcomes) == 1
    assert _counts() == (1, 1, 2, 1)


def test_a_validation_rejection_is_counted_and_audited_and_the_batch_continues():
    sink = RecordingSink()
    claims = [_rel(), _rel(assertion_type="banana"), _attr()]

    result = ingest_observation(_obs(), provider=ScriptedProvider(claims), audit_sink=sink)

    assert (result.normalization_drops, result.validation_drops) == (0, 1)
    assert len(sink.drops) == 1 and sink.drops[0].stage == "validation"
    assert len(result.outcomes) == 2
    assert _counts() == (1, 2, 2, 1)


def test_outcomes_follow_the_provider_order():
    result = ingest_observation(
        _obs(), provider=ScriptedProvider([_attr(), _rel()]), audit_sink=RecordingSink()
    )

    assert [o.assertion.assertion_type for o in result.outcomes] == ["attribute", "relationship"]


def test_the_result_is_immutable_and_carries_no_failure_field():
    result = ingest_observation(_obs(), provider=ScriptedProvider([_rel()]), audit_sink=RecordingSink())

    assert dataclasses.is_dataclass(result)
    assert isinstance(result.outcomes, tuple)
    names = {f.name for f in dataclasses.fields(result)}
    assert names == {"observation", "outcomes", "normalization_drops", "validation_drops", "provider_attempts"}
    for name in names:
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(result, name, None)


# ---------------------------------------------------------------------------
# Retry policy: positive, bounded, no backoff
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc_type", [ProviderTimeout, ProviderUnavailable])
def test_a_retryable_failure_then_success_takes_two_attempts_and_persists_once(exc_type):
    provider = ScriptedProvider(exc_type("transient"), [_rel()])

    result = ingest_observation(_obs(), provider=provider, audit_sink=RecordingSink())

    assert result.provider_attempts == 2
    assert len(provider.calls) == 2
    assert provider.calls[0] is provider.calls[1] is result.observation
    assert _counts() == (1, 1, 2, 1)


@pytest.mark.parametrize("exc_type", [ProviderTimeout, ProviderUnavailable])
def test_retries_are_bounded_and_the_last_error_is_raised_unchanged(exc_type):
    first, last = exc_type("first"), exc_type("last")
    provider, sink = ScriptedProvider(first, last), RecordingSink()

    with pytest.raises(exc_type) as caught:
        ingest_observation(_obs(), provider=provider, audit_sink=sink)

    assert caught.value is last
    assert len(provider.calls) == 2
    assert sink.drops == []
    assert _counts() == (1, 0, 0, 0)  # only the Observation


@pytest.mark.parametrize(
    "exc",
    [ProviderInvalidResponse("garbled"), ProviderError("base")],
    ids=["invalid-response", "base-provider-error"],
)
def test_every_other_provider_error_is_terminal(exc):
    provider = ScriptedProvider(exc)

    with pytest.raises(type(exc)) as caught:
        ingest_observation(_obs(), provider=provider, audit_sink=RecordingSink())

    assert caught.value is exc
    assert len(provider.calls) == 1
    assert _counts() == (1, 0, 0, 0)


def test_malformed_output_is_terminal_and_not_retried():
    provider = ScriptedProvider("not a list")

    with pytest.raises(ExtractionMalformedOutput):
        ingest_observation(_obs(), provider=provider, audit_sink=RecordingSink())

    assert len(provider.calls) == 1
    assert _counts() == (1, 0, 0, 0)


def test_an_audit_sink_failure_is_terminal_and_not_retried():
    provider = ScriptedProvider([{"unknown_field": 1}])  # a normalization drop -> sink.record

    with pytest.raises(ExtractionInternalError):
        ingest_observation(_obs(), provider=provider, audit_sink=_FailingSink())

    assert len(provider.calls) == 1
    assert _counts() == (1, 0, 0, 0)


def test_retry_never_sleeps(monkeypatch):
    def forbidden_sleep(*args, **kwargs):
        raise AssertionError("R1 retry must not back off")

    monkeypatch.setattr(time, "sleep", forbidden_sleep)

    result = ingest_observation(
        _obs(), provider=ScriptedProvider(ProviderTimeout("t"), [_rel()]), audit_sink=RecordingSink()
    )

    assert result.provider_attempts == 2


# ---------------------------------------------------------------------------
# Engine failures abort, unchanged
# ---------------------------------------------------------------------------

def test_an_engine_contract_violation_aborts_the_rest_of_the_batch(monkeypatch):
    def fake_extract(observation, *, provider, audit_sink):
        def attribute(subject, **extra):
            return Assertion(
                observation_id=observation.id, assertion_type="attribute",
                subject=subject, subject_type="Person",
                predicate="mood", object="happy", **extra,
            )
        # The middle claim contradicts its kind: unreachable through validation.
        return [attribute("Ann"), attribute("Bob", object_type="Company"), attribute("Cid")]

    monkeypatch.setattr(orchestrator, "extract", fake_extract)

    with pytest.raises(ContradictoryTypeField):
        ingest_observation(_obs(), provider=ScriptedProvider(), audit_sink=RecordingSink())

    assert _counts() == (1, 1, 1, 0)  # Observation + Ann only


def test_an_unexpected_engine_failure_aborts_unchanged_and_is_not_retried(monkeypatch):
    real_process = orchestrator.process_assertion
    boom = RuntimeError("boom")
    calls = {"engine": 0}

    def flaky(assertion):
        calls["engine"] += 1
        if calls["engine"] == 2:
            raise boom
        return real_process(assertion)

    monkeypatch.setattr(orchestrator, "process_assertion", flaky)
    provider = ScriptedProvider([_attr(), _attr(subject_text="Bob"), _attr(subject_text="Cid")])

    with pytest.raises(RuntimeError) as caught:
        ingest_observation(_obs(), provider=provider, audit_sink=RecordingSink())

    assert caught.value is boom
    assert calls["engine"] == 2
    assert len(provider.calls) == 1  # extraction was not repeated
    assert _counts() == (1, 1, 1, 0)


# ---------------------------------------------------------------------------
# Ordering and transaction ownership
# ---------------------------------------------------------------------------

def test_extraction_completes_before_the_first_engine_call(monkeypatch):
    log: list[str] = []
    real_extract, real_process = orchestrator.extract, orchestrator.process_assertion

    def logging_extract(*args, **kwargs):
        result = real_extract(*args, **kwargs)
        log.append("extract-returned")
        return result

    def logging_process(assertion):
        log.append("engine")
        return real_process(assertion)

    monkeypatch.setattr(orchestrator, "extract", logging_extract)
    monkeypatch.setattr(orchestrator, "process_assertion", logging_process)

    ingest_observation(_obs(), provider=ScriptedProvider([_attr(), _rel()]), audit_sink=RecordingSink())

    assert log == ["extract-returned", "engine", "engine"]


def test_no_write_transaction_is_held_while_the_provider_runs():
    provider = _LockProbingProvider()

    result = ingest_observation(_obs(), provider=provider, audit_sink=RecordingSink())

    assert provider.probed is True
    assert result.outcomes == ()


# ---------------------------------------------------------------------------
# Preconditions: all checked before any side effect
# ---------------------------------------------------------------------------

def test_an_already_persisted_observation_is_rejected_before_any_action():
    provider = ScriptedProvider()

    with pytest.raises(ValueError, match="persisted"):
        ingest_observation(Observation(id=5, raw_text="x"), provider=provider, audit_sink=RecordingSink())

    assert provider.calls == []
    assert _counts() == (0, 0, 0, 0)


def test_provider_and_sink_are_required_keyword_only():
    obs, provider, sink = _obs(), ScriptedProvider(), RecordingSink()

    with pytest.raises(TypeError):
        ingest_observation(obs)
    with pytest.raises(TypeError):
        ingest_observation(obs, provider, sink)
    with pytest.raises(TypeError):
        ingest_observation(obs, provider=provider)
    with pytest.raises(TypeError):
        ingest_observation(obs, audit_sink=sink)

    assert provider.calls == []
    assert _counts() == (0, 0, 0, 0)


@pytest.mark.parametrize("which", ["provider", "audit_sink"])
def test_a_none_collaborator_is_rejected_before_any_action(which):
    collaborators = {"provider": ScriptedProvider(), "audit_sink": RecordingSink()}
    collaborators[which] = None

    with pytest.raises(ValueError, match=which):
        ingest_observation(_obs(), **collaborators)

    assert _counts() == (0, 0, 0, 0)


@pytest.mark.parametrize("bad", [0, -1])
def test_the_attempt_limit_must_be_positive(bad):
    with pytest.raises(ValueError, match="max_attempts"):
        ingest_observation(
            _obs(), provider=ScriptedProvider(), audit_sink=RecordingSink(), max_attempts=bad
        )

    assert _counts() == (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Dependency direction: public entry points only
# ---------------------------------------------------------------------------

def test_the_orchestrator_never_imports_storage_or_classification():
    imported = _imported_modules(ORCHESTRATOR_SOURCE)

    offenders = sorted(
        m for m in imported
        if any(m == f or m.startswith(f + ".") for f in FORBIDDEN_IMPORTS)
    )
    assert offenders == []


def test_the_orchestrator_imports_only_its_allowed_public_entry_points():
    assert _imported_modules(ORCHESTRATOR_SOURCE) - ALLOWED_IMPORTS == set()