"""
The spine: Observation -> Extraction -> Normalization -> Validation ->
Assertion -> Engine -> Persistence -> Trace, composed MANUALLY (no
orchestrator yet), using the scripted fake provider.

If these pass, the R0 contracts work together; any later failure in the
orchestrator is then the orchestrator's own.
"""

from reality import engine
from reality import repository as repo
from reality.db import transaction
from reality.extraction.pipeline import extract
from reality.schemas import Observation
from tests.support.fake_provider import ScriptedProvider
from tests.support.recording_sink import RecordingSink


def _count(table: str) -> int:
    with transaction() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _counts() -> tuple[int, int, int, int]:
    return tuple(_count(t) for t in ("observations", "assertions", "entities", "relationships"))


def _persist(text: str) -> Observation:
    return engine.process_observation(Observation(raw_text=text))


def test_spine_relationship_from_observation_to_traceable_stored_effect():
    obs = _persist("Sara works at Acme")
    provider = ScriptedProvider([{
        "assertion_type": "relationship",
        "subject_text": "Sara", "subject_type": "Person",
        "predicate": "works_at",
        "object_text": "Acme", "object_type": "Company",
    }])
    sink = RecordingSink()

    assertions = extract(obs, provider=provider, audit_sink=sink)

    # Extraction produced one claim and wrote nothing but the Observation.
    assert provider.calls[0] is obs
    assert sink.drops == []
    assert len(assertions) == 1
    assert _counts() == (1, 0, 0, 0)

    result = engine.process_assertion(assertions[0])

    assert _counts() == (1, 1, 2, 1)
    assert (result.subject_entity.name, result.subject_entity.entity_type) == ("Sara", "Person")
    assert (result.object_entity.name, result.object_entity.entity_type) == ("Acme", "Company")
    assert result.relationship.relation_type == "works_at"
    assert result.assertion.observation_id == obs.id
    assert (result.assertion.subject_type, result.assertion.object_type) == ("Person", "Company")

    trace = engine.get_full_trace(result.relationship.id)
    assert trace is not None
    traced_relationship, traced_assertion, traced_observation = trace
    assert traced_relationship == result.relationship
    assert traced_assertion == result.assertion
    assert traced_observation == obs
    assert traced_observation.raw_text == "Sara works at Acme"


def test_spine_attribute_from_observation_to_stored_state_with_assertion_provenance():
    obs = _persist("Sara is happy")
    provider = ScriptedProvider([{
        "assertion_type": "attribute",
        "subject_text": "Sara", "subject_type": "Person",
        "predicate": "mood", "object_text": "happy",
    }])
    sink = RecordingSink()

    assertions = extract(obs, provider=provider, audit_sink=sink)

    assert sink.drops == []
    assert len(assertions) == 1
    assert _counts() == (1, 0, 0, 0)

    result = engine.process_assertion(assertions[0])

    assert result.relationship is None and result.object_entity is None
    assert result.subject_entity.attributes == {"mood": "happy"}
    assert _counts() == (1, 1, 1, 0)

    # No attribute trace API exists (RFC-004 section 11: provenance is derived),
    # so check the Assertion -> Observation hop the rule relies on.
    with transaction() as conn:
        stored = repo.get_assertion_by_id(conn, result.assertion.id)
        source = repo.get_observation_by_id(conn, stored.observation_id)
    assert stored == result.assertion
    assert source == obs