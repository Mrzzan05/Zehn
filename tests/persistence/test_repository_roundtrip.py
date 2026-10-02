from reality import repository as repo
from reality.schemas import Assertion, Entity, Observation, Relationship


def _assertion(obs_id):
    return Assertion(
        observation_id=obs_id, assertion_type="attribute",
        subject="Sara", predicate="likes", object="cats", metadata={"k": "v"},
    )


def test_observation_assertion_roundtrip(conn):
    obs = repo.create_observation(conn, Observation(raw_text="Sara likes cats"))
    saved = repo.create_assertion(conn, _assertion(obs.id))

    assert repo.get_observation_by_id(conn, obs.id) == obs
    assert repo.get_assertion_by_id(conn, saved.id) == saved


def test_reading_a_row_written_by_sql_does_not_depend_on_the_create_path(conn):
    # Isolates the READ path: no Assertion is constructed on the way in.
    conn.execute("INSERT INTO observations (raw_text, created_at) VALUES ('x', '2026-01-01T00:00:00+00:00')")
    conn.execute(
        "INSERT INTO assertions (observation_id, assertion_type, subject, predicate, object, created_at) "
        "VALUES (1, 'attribute', 's', 'p', 'o', '2026-01-01T00:00:00+00:00')"
    )

    assert repo.get_assertion_by_id(conn, 1).observation_id == 1


def test_trace_returns_what_was_stored(conn):
    obs = repo.create_observation(conn, Observation(raw_text="Sara likes cats"))
    a = repo.create_assertion(conn, _assertion(obs.id))
    s = repo.create_entity(conn, Entity(name="Sara", entity_type="Person"))
    o = repo.create_entity(conn, Entity(name="cats", entity_type="Animal"))
    rel = repo.create_relationship(conn, Relationship(
        source_entity_id=s.id, target_entity_id=o.id, relation_type="likes", assertion_id=a.id))

    t_rel, t_assertion, t_obs = repo.trace_relationship_to_observation(conn, rel.id)

    assert (t_rel, t_assertion, t_obs) == (rel, a, obs)


def _typed_assertion(obs_id, **overrides):
    fields = dict(
        observation_id=obs_id, assertion_type="relationship",
        subject="Sara", subject_type="Person", predicate="works_at",
        object="Acme", object_type="Company", metadata={"note": "x"},
    )
    fields.update(overrides)
    return Assertion(**fields)


def test_typed_fields_roundtrip(conn):
    obs = repo.create_observation(conn, Observation(raw_text="Sara works at Acme"))
    saved = repo.create_assertion(conn, _typed_assertion(obs.id))

    loaded = repo.get_assertion_by_id(conn, saved.id)

    assert loaded == saved
    assert (loaded.subject_type, loaded.object_type) == ("Person", "Company")


def test_absent_types_are_stored_as_empty_string_never_null(conn):
    obs = repo.create_observation(conn, Observation(raw_text="x"))
    saved = repo.create_assertion(conn, _assertion(obs.id))  # declares no types

    row = conn.execute(
        "SELECT subject_type, object_type FROM assertions WHERE id = ?", (saved.id,)
    ).fetchone()
    assert (row["subject_type"], row["object_type"]) == ("", "")

    notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(assertions)")}
    assert notnull["subject_type"] == 1 and notnull["object_type"] == 1

    loaded = repo.get_assertion_by_id(conn, saved.id)
    assert loaded.subject_type is None and loaded.object_type is None
    assert loaded == saved


def test_trace_carries_the_typed_fields(conn):
    obs = repo.create_observation(conn, Observation(raw_text="Sara works at Acme"))
    a = repo.create_assertion(conn, _typed_assertion(obs.id))
    s = repo.create_entity(conn, Entity(name="Sara", entity_type="Person"))
    o = repo.create_entity(conn, Entity(name="Acme", entity_type="Company"))
    rel = repo.create_relationship(conn, Relationship(
        source_entity_id=s.id, target_entity_id=o.id,
        relation_type="works_at", assertion_id=a.id))

    t_rel, t_assertion, t_obs = repo.trace_relationship_to_observation(conn, rel.id)

    assert t_assertion == a
    assert (t_assertion.subject_type, t_assertion.object_type) == ("Person", "Company")


def test_metadata_is_stored_but_never_promoted_to_typed_fields(conn):
    obs = repo.create_observation(conn, Observation(raw_text="x"))
    hints = {"subject_type": "Person", "object_type": "Company"}
    saved = repo.create_assertion(conn, _typed_assertion(
        obs.id, assertion_type="attribute", subject_type=None, object_type=None, metadata=hints))

    loaded = repo.get_assertion_by_id(conn, saved.id)

    assert loaded.subject_type is None and loaded.object_type is None
    assert loaded.metadata == hints