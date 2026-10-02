import pytest

from reality import engine
from reality.db import transaction
from reality.engine import UnsupportedAssertionType
from reality.schemas import Assertion, Observation


def _obs(text: str = "x"):
    return engine.process_observation(Observation(raw_text=text))


def _assertion(obs_id, kind, subject, predicate, obj, **meta):
    return Assertion(
        observation_id=obs_id, assertion_type=kind,
        subject=subject, predicate=predicate, object=obj, metadata=meta,
    )


def _count(table: str) -> int:
    with transaction() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_relationship_creates_both_entities_and_a_traceable_edge():
    obs = _obs("Sara works at Acme")
    r = engine.process_assertion(_assertion(
        obs.id, "relationship", "Sara", "works_at", "Acme",
        subject_type="Person", object_type="Company"))

    assert (r.subject_entity.name, r.subject_entity.entity_type) == ("Sara", "Person")
    assert (r.object_entity.name, r.object_entity.entity_type) == ("Acme", "Company")

    rel, assertion, observation = engine.get_full_trace(r.relationship.id)
    assert assertion.id == r.assertion.id
    assert observation.id == obs.id


def test_same_name_and_type_reuses_the_entity():
    first = engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "mood", "happy", subject_type="Person"))
    second = engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "city", "Tehran", subject_type="Person"))

    assert first.subject_entity.id == second.subject_entity.id


def test_same_name_with_a_different_type_is_a_different_entity():
    person = engine.process_assertion(_assertion(_obs().id, "attribute", "Mercury", "k", "v", subject_type="Person"))
    planet = engine.process_assertion(_assertion(_obs().id, "attribute", "Mercury", "k", "v", subject_type="Planet"))

    assert person.subject_entity.id != planet.subject_entity.id


def test_attribute_overwrites_by_key_and_preserves_other_keys():
    engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "mood", "happy", subject_type="Person"))
    engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "city", "Tehran", subject_type="Person"))
    result = engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "mood", "sad", subject_type="Person"))

    assert result.subject_entity.attributes == {"mood": "sad", "city": "Tehran"}


def test_unsupported_assertion_type_is_rejected_before_any_write():
    obs = _obs()
    with pytest.raises(UnsupportedAssertionType):
        engine.process_assertion(
            _assertion(obs.id, "unclassified", "Sara", "mood", "happy", subject_type="Person")
        )

    assert _count("assertions") == 0
    assert _count("entities") == 0


def test_failure_mid_processing_rolls_everything_back(monkeypatch):
    obs = _obs()

    def boom(*a, **k):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(engine.repo, "create_relationship", boom)

    with pytest.raises(RuntimeError):
        engine.process_assertion(_assertion(
            obs.id, "relationship", "Sara", "works_at", "Acme",
            subject_type="Person", object_type="Company"))

    for table in ("assertions", "entities", "relationships"):
        assert _count(table) == 0


def test_processing_the_same_relationship_twice_is_a_noop():
    obs = _obs("Sara works at Acme")
    a = _assertion(obs.id, "relationship", "Sara", "works_at", "Acme",
                   subject_type="Person", object_type="Company")

    first = engine.process_assertion(a)
    second = engine.process_assertion(a)

    assert second.assertion.id == first.assertion.id
    assert second.relationship.id == first.relationship.id
    assert _count("assertions") == 1
    assert _count("relationships") == 1
    assert _count("entities") == 2


def test_reprocessing_an_old_attribute_does_not_overwrite_newer_state():
    old_obs, new_obs = _obs("happy"), _obs("sad")
    happy = _assertion(old_obs.id, "attribute", "Sara", "mood", "happy", subject_type="Person")
    sad = _assertion(new_obs.id, "attribute", "Sara", "mood", "sad", subject_type="Person")

    engine.process_assertion(happy)
    engine.process_assertion(sad)
    result = engine.process_assertion(happy)  # replay of the OLD one

    assert result.subject_entity.attributes["mood"] == "sad"


def test_same_content_from_two_observations_is_not_deduplicated():
    a1 = engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "mood", "happy", subject_type="Person"))
    a2 = engine.process_assertion(_assertion(_obs().id, "attribute", "Sara", "mood", "happy", subject_type="Person"))

    assert a1.assertion.id != a2.assertion.id
    assert _count("assertions") == 2