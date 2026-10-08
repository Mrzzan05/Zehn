"""
End-to-end acceptance: Observation -> Orchestrator -> Extraction ->
Normalization -> Validation -> Assertion -> Engine -> Persistence -> Trace,
with the scripted fake provider and the real Engine and database.

E1 is the canonical architectural acceptance test of R0 + R1.
"""

import pytest

from reality import engine
from reality.db import transaction
from reality.extraction.errors import ExtractionMalformedOutput
from reality.orchestrator import ingest_observation
from reality.provider_errors import ProviderTimeout, ProviderUnavailable
from reality.schemas import Observation
from tests.support.fake_provider import ScriptedProvider
from tests.support.recording_sink import RecordingSink


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


def test_e1_canonical_observation_to_traceable_reality_effect():
    provider, sink = ScriptedProvider([_rel()]), RecordingSink()

    result = ingest_observation(
        Observation(raw_text="Sara works at Acme"), provider=provider, audit_sink=sink
    )

    # The provider saw the PERSISTED Observation; nothing was dropped.
    assert provider.calls[0] is result.observation
    assert isinstance(result.observation.id, int)
    assert sink.drops == []
    assert (result.normalization_drops, result.validation_drops, result.provider_attempts) == (0, 0, 1)

    # Exactly one of each, plus the two resolved entities.
    assert _counts() == (1, 1, 2, 1)
    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert (outcome.subject_entity.name, outcome.subject_entity.entity_type) == ("Sara", "Person")
    assert (outcome.object_entity.name, outcome.object_entity.entity_type) == ("Acme", "Company")
    assert outcome.relationship.relation_type == "works_at"

    # The whole architectural claim: Relationship -> Assertion -> Observation.
    trace = engine.get_full_trace(outcome.relationship.id)
    assert trace is not None
    relationship, assertion, observation = trace
    assert relationship == outcome.relationship
    assert assertion == outcome.assertion
    assert observation == result.observation
    assert observation.raw_text == "Sara works at Acme"
    assert assertion.observation_id == observation.id
    assert (assertion.subject_type, assertion.object_type) == ("Person", "Company")
    assert relationship.source_entity_id == outcome.subject_entity.id
    assert relationship.target_entity_id == outcome.object_entity.id


def test_e2_attribute_evolution_keeps_history_and_attributes_the_latest_assertion():
    first = ingest_observation(
        Observation(raw_text="Sara is happy"),
        provider=ScriptedProvider([_attr(object_text="happy")]), audit_sink=RecordingSink(),
    )
    second = ingest_observation(
        Observation(raw_text="Sara is sad"),
        provider=ScriptedProvider([_attr(object_text="sad")]), audit_sink=RecordingSink(),
    )

    assert _counts() == (2, 2, 1, 0)  # both Observations and Assertions remain; one Entity
    assert first.outcomes[0].subject_entity.id == second.outcomes[0].subject_entity.id
    assert first.outcomes[0].subject_entity.attributes == {"mood": "happy"}
    assert second.outcomes[0].subject_entity.attributes == {"mood": "sad"}

    # RFC-004 section 11: an attribute's provenance is the latest attribute
    # Assertion for that entity and predicate, in insertion order.
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, observation_id FROM assertions "
            "WHERE subject = ? AND subject_type = ? AND predicate = ? "
            "ORDER BY id DESC LIMIT 1",
            ("Sara", "Person", "mood"),
        ).fetchone()
    assert row["id"] == second.outcomes[0].assertion.id
    assert row["observation_id"] == second.observation.id


def test_e3_a_mixed_batch_applies_the_valid_claims_and_audits_every_drop():
    sink = RecordingSink()
    claims = [
        _rel(),                           # valid
        "junk",                           # normalization drop: not a dictionary
        _attr(confidence=0.9),            # normalization drop: extra field
        _rel(assertion_type="banana"),    # validation drop: unsupported kind
        _attr(),                          # valid
    ]

    result = ingest_observation(
        Observation(raw_text="mixed"), provider=ScriptedProvider(claims), audit_sink=sink
    )

    assert (result.normalization_drops, result.validation_drops) == (2, 1)
    assert [d.stage for d in sink.drops] == ["normalization", "normalization", "validation"]
    assert [o.assertion.assertion_type for o in result.outcomes] == ["relationship", "attribute"]
    assert result.outcomes[0].subject_entity.id == result.outcomes[1].subject_entity.id
    assert result.outcomes[1].subject_entity.attributes == {"mood": "happy"}
    assert _counts() == (1, 2, 2, 1)


def test_e4a_the_same_text_twice_is_two_events_with_shared_entities():
    first = ingest_observation(
        Observation(raw_text="Sara works at Acme"),
        provider=ScriptedProvider([_rel()]), audit_sink=RecordingSink(),
    )
    second = ingest_observation(
        Observation(raw_text="Sara works at Acme"),
        provider=ScriptedProvider([_rel()]), audit_sink=RecordingSink(),
    )

    assert first.observation.id != second.observation.id
    assert first.outcomes[0].assertion.id != second.outcomes[0].assertion.id
    assert first.outcomes[0].relationship.id != second.outcomes[0].relationship.id
    assert first.outcomes[0].subject_entity.id == second.outcomes[0].subject_entity.id
    assert first.outcomes[0].object_entity.id == second.outcomes[0].object_entity.id
    assert _counts() == (2, 2, 2, 2)  # never deduplicated across Observations

    for result in (first, second):  # each effect traces to ITS OWN Observation
        _, _, observation = engine.get_full_trace(result.outcomes[0].relationship.id)
        assert observation.id == result.observation.id


def test_e4b_the_same_claim_twice_in_one_batch_is_a_replay_no_op():
    result = ingest_observation(
        Observation(raw_text="Sara works at Acme"),
        provider=ScriptedProvider([_rel(), _rel()]), audit_sink=RecordingSink(),
    )

    first, second = result.outcomes
    assert second.assertion.id == first.assertion.id
    assert second.relationship.id == first.relationship.id
    assert _counts() == (1, 1, 2, 1)


@pytest.mark.parametrize("exc_type", [ProviderTimeout, ProviderUnavailable])
def test_e5_a_transient_failure_then_success_leaves_exactly_one_effect(exc_type):
    provider = ScriptedProvider(exc_type("transient"), [_rel()])

    result = ingest_observation(
        Observation(raw_text="Sara works at Acme"), provider=provider, audit_sink=RecordingSink()
    )

    assert result.provider_attempts == 2
    assert _counts() == (1, 1, 2, 1)  # one Observation, not one per attempt
    _, _, observation = engine.get_full_trace(result.outcomes[0].relationship.id)
    assert observation == result.observation


def test_e6_exhausted_retries_leave_only_the_observation_and_resubmission_is_a_new_one():
    last = ProviderTimeout("last")
    provider = ScriptedProvider(ProviderTimeout("first"), last)

    with pytest.raises(ProviderTimeout) as caught:
        ingest_observation(
            Observation(raw_text="Sara works at Acme"), provider=provider, audit_sink=RecordingSink()
        )

    assert caught.value is last
    assert _counts() == (1, 0, 0, 0)
    with transaction() as conn:
        stored = conn.execute("SELECT raw_text FROM observations").fetchone()
    assert stored["raw_text"] == "Sara works at Acme"

    # CHARACTERIZATION of a known limitation (R1 plan section 8): the failed
    # run's Observation id is not returned, so re-submitting the text creates
    # a NEW Observation. A future "resume" decision may change this test.
    retry = ingest_observation(
        Observation(raw_text="Sara works at Acme"),
        provider=ScriptedProvider([_rel()]), audit_sink=RecordingSink(),
    )

    assert retry.observation.id == 2
    assert _counts() == (2, 1, 2, 1)


def test_e7_malformed_provider_output_leaves_only_observations_and_is_not_retried():
    for index, bad in enumerate(("not a list", {"claims": []}, None, 42), start=1):
        provider, sink = ScriptedProvider(bad), RecordingSink()

        with pytest.raises(ExtractionMalformedOutput):
            ingest_observation(Observation(raw_text="x"), provider=provider, audit_sink=sink)

        assert len(provider.calls) == 1
        # R2-D13: the malformed root is audited once, stamped with the persisted Observation.
        assert len(sink.drops) == 1
        drop = sink.drops[0]
        assert drop.stage == "normalization"
        assert drop.observation_id == index
        assert drop.payload_projection == {"value": bad}

    assert _counts() == (4, 0, 0, 0)  # four Observations, no Reality effect


def test_e8_an_engine_failure_mid_batch_keeps_the_applied_prefix_and_rolls_back_the_failing_unit(monkeypatch):
    real_create_relationship = engine.repo.create_relationship
    boom = RuntimeError("simulated failure")
    calls = {"n": 0}

    def flaky(conn, relationship):
        calls["n"] += 1
        if calls["n"] == 2:
            raise boom
        return real_create_relationship(conn, relationship)

    monkeypatch.setattr(engine.repo, "create_relationship", flaky)
    claims = [_rel(), _rel(subject_text="Bob", object_text="Globex"), _attr(subject_text="Cid")]
    provider = ScriptedProvider(claims)

    with pytest.raises(RuntimeError) as caught:
        ingest_observation(Observation(raw_text="batch"), provider=provider, audit_sink=RecordingSink())

    assert caught.value is boom
    assert len(provider.calls) == 1               # extraction was not repeated
    assert _counts() == (1, 1, 2, 1)              # Observation + the first unit only
    assert _entity_names() == ["Sara", "Acme"]    # Bob and Globex rolled back; Cid never reached
    assert engine.get_full_trace(1) is not None   # the applied prefix still traces


def test_e9_smuggled_authority_fields_are_dropped_at_normalization_and_never_reach_reality():
    sink = RecordingSink()
    claims = [_rel(id=5), _rel(entity_uuid="uuid-123"), _rel(observation_id=99), _rel()]

    result = ingest_observation(
        Observation(raw_text="Sara works at Acme"), provider=ScriptedProvider(claims), audit_sink=sink
    )

    assert result.normalization_drops == 3
    assert len(result.outcomes) == 1
    assert result.outcomes[0].assertion.observation_id == result.observation.id
    assert {d.stage for d in sink.drops} == {"normalization"}
    smuggled = {key for d in sink.drops for key in d.payload_projection}
    assert {"id", "entity_uuid", "observation_id"} <= smuggled
    assert _counts() == (1, 1, 2, 1)