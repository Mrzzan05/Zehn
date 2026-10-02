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