import pytest

from reality import engine
from reality.db import transaction
from reality.schemas import Assertion, Observation
from reality.engine import (
    AssertionContractViolation,
    ContradictoryTypeField,
    MissingTypeField,
    UnsupportedAssertionType,
)


def _obs(text: str = "x"):
    return engine.process_observation(Observation(raw_text=text))


def _assertion(obs_id, kind, subject, predicate, obj, *,
               subject_type=None, object_type=None, **meta):
    return Assertion(
        observation_id=obs_id, assertion_type=kind,
        subject=subject, subject_type=subject_type,
        predicate=predicate,
        object=obj, object_type=object_type,
        metadata=meta,
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
            _assertion(obs.id, "banana", "Sara", "mood", "happy", subject_type="Person")
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


@pytest.mark.parametrize(
    "fields, expected",
    [
        pytest.param(
            dict(assertion_type="attribute"),
            MissingTypeField, id="attribute-missing-subject-type"),
        pytest.param(
            dict(assertion_type="relationship", object_type="Company"),
            MissingTypeField, id="relationship-missing-subject-type"),
        pytest.param(
            dict(assertion_type="relationship", subject_type="Person"),
            MissingTypeField, id="relationship-missing-object-type"),
        pytest.param(
            dict(assertion_type="attribute", subject_type="Person", object_type="Project"),
            ContradictoryTypeField, id="attribute-declares-object-type"),
        pytest.param(
            dict(assertion_type="attribute", metadata={"subject_type": "Person"}),
            MissingTypeField, id="types-only-in-metadata-are-not-types"),
    ],
)
def test_contract_violation_is_raised_before_any_write(fields, expected):
    obs = _obs()
    assertion = Assertion(
        observation_id=obs.id, subject="Sara", predicate="p", object="o", **fields)

    with pytest.raises(expected):
        engine.process_assertion(assertion)

    for table in ("assertions", "entities", "relationships"):
        assert _count(table) == 0


def test_contract_violation_hierarchy():
    for exc in (UnsupportedAssertionType, MissingTypeField, ContradictoryTypeField):
        assert issubclass(exc, AssertionContractViolation)
    assert issubclass(AssertionContractViolation, ValueError)
    assert not issubclass(MissingTypeField, UnsupportedAssertionType)
    assert not issubclass(ContradictoryTypeField, UnsupportedAssertionType)


def test_metadata_never_decides_entity_identity():
    obs = _obs()
    assertion = Assertion(
        observation_id=obs.id, assertion_type="attribute",
        subject="Mercury", subject_type="Person",
        predicate="k", object="v",
        metadata={"subject_type": "Planet"},  # disagrees with the typed field
    )

    result = engine.process_assertion(assertion)

    assert result.subject_entity.entity_type == "Person"


def test_same_triple_with_different_subject_types_are_distinct_claims():
    obs = _obs()
    person = engine.process_assertion(_assertion(
        obs.id, "attribute", "Mercury", "k", "v", subject_type="Person"))
    planet = engine.process_assertion(_assertion(
        obs.id, "attribute", "Mercury", "k", "v", subject_type="Planet"))

    assert person.assertion.id != planet.assertion.id
    assert person.subject_entity.id != planet.subject_entity.id
    assert _count("assertions") == 2


def test_same_triple_with_different_object_types_are_distinct_claims():
    obs = _obs()
    company = engine.process_assertion(_assertion(
        obs.id, "relationship", "Sara", "works_at", "Mercury",
        subject_type="Person", object_type="Company"))
    planet = engine.process_assertion(_assertion(
        obs.id, "relationship", "Sara", "works_at", "Mercury",
        subject_type="Person", object_type="Planet"))

    assert company.assertion.id != planet.assertion.id
    assert company.object_entity.id != planet.object_entity.id
    assert company.relationship.id != planet.relationship.id
    assert _count("relationships") == 2
    assert _count("entities") == 3  # Sara/Person, Mercury/Company, Mercury/Planet


def test_metadata_only_difference_is_a_replay_and_first_metadata_wins():
    obs = _obs()
    first = engine.process_assertion(_assertion(
        obs.id, "attribute", "Sara", "mood", "happy", subject_type="Person", note="first"))
    second = engine.process_assertion(_assertion(
        obs.id, "attribute", "Sara", "mood", "happy", subject_type="Person", note="second"))

    assert second.assertion.id == first.assertion.id
    assert second.assertion.metadata == {"note": "first"}
    assert _count("assertions") == 1