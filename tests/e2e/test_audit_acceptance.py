"""
R2.7: acceptance of the persistent audit trail through the real path.

Observation -> orchestrator -> extraction -> SqliteAuditSink (real file) ->
reality.audit_diagnostics, with the real Engine and database. Orchestration
semantics are already pinned in test_orchestrator.py and test_acceptance.py
with a RecordingSink; this module pins what is new: that the drops survive
in a real store and are readable back, bounded and per Observation.

Helpers are duplicated on purpose, as in the rest of the e2e suite.
"""

from datetime import datetime, timezone

import pytest

from reality import db, engine
from reality.audit_diagnostics import count_drops, drops_for_observation
from reality.audit_store import AuditSchemaMismatch, SqliteAuditSink
from reality.bounded_snapshot import MAX_PAYLOAD_PREVIEW_CHARS
from reality.db import transaction
from reality.extraction.errors import ExtractionMalformedOutput
from reality.orchestrator import ingest_observation
from reality.provider_errors import ProviderTimeout
from reality.schemas import Observation
from tests.support.fake_provider import ScriptedProvider
from tests.support.recording_sink import RecordingSink

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)


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


def _count(table: str) -> int:
    with transaction() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _counts() -> tuple[int, int, int, int]:
    """(observations, assertions, entities, relationships)"""
    return tuple(_count(t) for t in ("observations", "assertions", "entities", "relationships"))


def _entity_names() -> list[str]:
    with transaction() as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM entities ORDER BY id")]


def _sink(path) -> SqliteAuditSink:
    return SqliteAuditSink(path, clock=lambda: FIXED)


@pytest.fixture
def audit_path(tmp_path):
    return tmp_path / "audit.db"


def test_a_mixed_batch_is_readable_back_per_observation_in_order(audit_path):
    claims = [
        _rel(),                           # valid
        "junk",                           # normalization drop: not a dictionary
        _attr(confidence=0.9),            # normalization drop: extra field
        _rel(assertion_type="banana"),    # validation drop: unsupported kind
        _attr(),                          # valid
    ]

    result = ingest_observation(
        Observation(raw_text="mixed"),
        provider=ScriptedProvider(claims),
        audit_sink=_sink(audit_path),
    )

    records = drops_for_observation(audit_path, result.observation.id)
    assert [r.stage for r in records] == ["normalization", "normalization", "validation"]
    assert [r.id for r in records] == sorted(r.id for r in records)
    assert {r.observation_id for r in records} == {result.observation.id}
    assert sum(r.stage == "normalization" for r in records) == result.normalization_drops
    assert sum(r.stage == "validation" for r in records) == result.validation_drops
    assert count_drops(audit_path) == 3
    assert _counts() == (1, 2, 2, 1)


def test_smuggled_authority_fields_are_audited_and_never_reach_reality(audit_path):
    claims = [_attr(subject_text="Mallory", confidence=0.9), _rel()]

    result = ingest_observation(
        Observation(raw_text="smuggle"),
        provider=ScriptedProvider(claims),
        audit_sink=_sink(audit_path),
    )

    (record,) = drops_for_observation(audit_path, result.observation.id)
    assert record.stage == "normalization"
    assert "Mallory" in record.payload_preview
    assert record.payload_truncated is False
    assert len(record.payload_hash) == 64
    assert _entity_names() == ["Sara", "Acme"]
    assert _counts() == (1, 1, 2, 1)


def test_an_oversized_dropped_claim_is_stored_bounded_and_hashed(audit_path):
    claims = [_attr(confidence=0.9, object_text="z" * 5000)]

    result = ingest_observation(
        Observation(raw_text="huge"),
        provider=ScriptedProvider(claims),
        audit_sink=_sink(audit_path),
    )

    (record,) = drops_for_observation(audit_path, result.observation.id)
    assert record.payload_truncated is True
    assert len(record.payload_preview) <= MAX_PAYLOAD_PREVIEW_CHARS
    assert len(record.payload_hash) == 64
    assert "z" * 2000 not in record.payload_preview


def test_a_malformed_root_is_audited_once_before_the_failure_is_raised(audit_path):
    provider = ScriptedProvider("not a list")

    with pytest.raises(ExtractionMalformedOutput):
        ingest_observation(
            Observation(raw_text="x"), provider=provider, audit_sink=_sink(audit_path)
        )

    assert len(provider.calls) == 1
    (record,) = drops_for_observation(audit_path, 1)
    assert record.stage == "normalization"
    assert record.observation_id == 1
    assert '"not a list"' in record.payload_preview
    assert count_drops(audit_path) == 1
    assert _counts() == (1, 0, 0, 0)  # the Observation only, no Reality effect


def test_two_observations_in_one_store_are_separable_and_ordered(audit_path):
    sink = _sink(audit_path)
    first = ingest_observation(
        Observation(raw_text="one"), provider=ScriptedProvider(["junk"]), audit_sink=sink
    )
    second = ingest_observation(
        Observation(raw_text="two"),
        provider=ScriptedProvider(["junk", _rel(assertion_type="banana")]),
        audit_sink=sink,
    )

    first_records = drops_for_observation(audit_path, first.observation.id)
    second_records = drops_for_observation(audit_path, second.observation.id)

    assert (first.observation.id, second.observation.id) == (1, 2)
    assert [r.id for r in first_records] == [1]
    assert [r.id for r in second_records] == [2, 3]
    assert [r.stage for r in second_records] == ["normalization", "validation"]
    assert count_drops(audit_path) == 3


def test_a_clean_ingest_and_exhausted_retries_write_no_audit_rows(audit_path):
    sink = _sink(audit_path)
    ingest_observation(
        Observation(raw_text="clean"), provider=ScriptedProvider([_rel()]), audit_sink=sink
    )
    assert count_drops(audit_path) == 0

    provider = ScriptedProvider(ProviderTimeout("first"), ProviderTimeout("last"))
    with pytest.raises(ProviderTimeout):
        ingest_observation(Observation(raw_text="down"), provider=provider, audit_sink=sink)

    assert count_drops(audit_path) == 0
    assert drops_for_observation(audit_path, 2) == ()
    assert _counts() == (2, 1, 2, 1)  # the Observation of the failed run is still persisted


def test_extraction_drops_are_already_durable_when_the_engine_fails(audit_path, monkeypatch):
    real_create_relationship = engine.repo.create_relationship
    boom = RuntimeError("simulated failure")
    calls = {"n": 0}

    def flaky(conn, relationship):
        calls["n"] += 1
        if calls["n"] == 2:
            raise boom
        return real_create_relationship(conn, relationship)

    monkeypatch.setattr(engine.repo, "create_relationship", flaky)
    claims = [_rel(), "junk", _rel(subject_text="Bob", object_text="Globex")]

    with pytest.raises(RuntimeError) as caught:
        ingest_observation(
            Observation(raw_text="batch"),
            provider=ScriptedProvider(claims),
            audit_sink=_sink(audit_path),
        )

    assert caught.value is boom
    (record,) = drops_for_observation(audit_path, 1)
    assert record.stage == "normalization"
    assert _counts() == (1, 1, 2, 1)  # Observation + the first unit only


def test_reality_is_identical_whether_the_sink_is_persistent_or_recording(
    audit_path, tmp_path, monkeypatch
):
    claims = [_rel(), "junk", _attr(), _rel(assertion_type="banana")]

    def run(db_file, sink):
        monkeypatch.setattr(db, "DB_PATH", db_file)
        db.initialize_database()
        result = ingest_observation(
            Observation(raw_text="same"), provider=ScriptedProvider(claims), audit_sink=sink
        )
        shape = (
            [o.assertion.assertion_type for o in result.outcomes],
            (result.normalization_drops, result.validation_drops, result.provider_attempts),
            _counts(),
            _entity_names(),
        )
        return shape

    with_store = run(tmp_path / "reality_a.db", _sink(audit_path))
    with_recording = run(tmp_path / "reality_b.db", RecordingSink())

    assert with_store == with_recording
    assert count_drops(audit_path) == 2


def test_the_trail_survives_reopening_the_store(audit_path):
    result = ingest_observation(
        Observation(raw_text="durable"),
        provider=ScriptedProvider(["junk", _rel(assertion_type="banana")]),
        audit_sink=_sink(audit_path),
    )
    before = drops_for_observation(audit_path, result.observation.id)

    reopened = _sink(audit_path)  # a fresh sink on the same file

    assert reopened is not None
    assert drops_for_observation(audit_path, result.observation.id) == before
    assert count_drops(audit_path) == len(before) == 2


def test_a_tampered_schema_version_fails_loudly_for_readers_and_writers(audit_path):
    import sqlite3

    ingest_observation(
        Observation(raw_text="tamper"),
        provider=ScriptedProvider(["junk"]),
        audit_sink=_sink(audit_path),
    )
    conn = sqlite3.connect(audit_path)
    try:
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(AuditSchemaMismatch) as reader:
        drops_for_observation(audit_path, 1)
    with pytest.raises(AuditSchemaMismatch) as writer:
        _sink(audit_path)

    assert reader.value.found_version == 2
    assert writer.value.found_version == 2