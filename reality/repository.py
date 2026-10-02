"""
reality/repository.py

Pure persistence layer for Zehn.

Every function takes an open sqlite3.Connection as its first argument and
never commits, rolls back or closes it. Transaction ownership belongs to
the caller (reality.engine, via reality.db.transaction()).

Explicitly NOT this file's job: deciding whether an Assertion matches an
existing Entity, merging, conflict resolution, or any other judgment call.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from reality.schemas import Assertion, Entity, Observation, Relationship


# ---------------------------------------------------------------------------
# Row <-> model conversion helpers (private to this module)
# ---------------------------------------------------------------------------

def _row_to_observation(row) -> Observation:
    return Observation(
        id=row["id"],
        raw_text=row["raw_text"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_assertion(row) -> Assertion:
    return Assertion(
        id=row["id"],
        observation_id=row["observation_id"],
        assertion_type=row["assertion_type"],
        subject=row["subject"],
        predicate=row["predicate"],
        object=row["object"],
        metadata=json.loads(row["metadata"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_entity(row) -> Entity:
    return Entity(
        id=row["id"],
        name=row["name"],
        entity_type=row["entity_type"],
        attributes=json.loads(row["attributes"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_relationship(row) -> Relationship:
    return Relationship(
        id=row["id"],
        source_entity_id=row["source_entity_id"],
        target_entity_id=row["target_entity_id"],
        relation_type=row["relation_type"],
        assertion_id=row["assertion_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

def create_observation(conn: sqlite3.Connection, observation: Observation) -> Observation:
    cursor = conn.execute(
        "INSERT INTO observations (raw_text, created_at) VALUES (?, ?)",
        (observation.raw_text, observation.created_at.isoformat()),
    )
    return observation.model_copy(update={"id": cursor.lastrowid})


def get_observation_by_id(conn: sqlite3.Connection, id: int) -> Optional[Observation]:
    row = conn.execute("SELECT * FROM observations WHERE id = ?", (id,)).fetchone()
    return _row_to_observation(row) if row else None


# ---------------------------------------------------------------------------
# Assertion
# ---------------------------------------------------------------------------

def create_assertion(conn: sqlite3.Connection, assertion: Assertion) -> Assertion:
    cursor = conn.execute(
        """
        INSERT INTO assertions
            (observation_id, assertion_type, subject, predicate, object,
             metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assertion.observation_id,
            assertion.assertion_type,
            assertion.subject,
            assertion.predicate,
            assertion.object,
            json.dumps(assertion.metadata),
            assertion.created_at.isoformat(),
        ),
    )
    return assertion.model_copy(update={"id": cursor.lastrowid})


def get_assertion_by_id(conn: sqlite3.Connection, id: int) -> Optional[Assertion]:
    row = conn.execute("SELECT * FROM assertions WHERE id = ?", (id,)).fetchone()
    return _row_to_assertion(row) if row else None


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

def create_entity(conn: sqlite3.Connection, entity: Entity) -> Entity:
    """Raises sqlite3.IntegrityError on UNIQUE(name, entity_type) violation."""
    cursor = conn.execute(
        """
        INSERT INTO entities
            (name, entity_type, attributes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            entity.name,
            entity.entity_type,
            json.dumps(entity.attributes),
            entity.created_at.isoformat(),
            entity.updated_at.isoformat(),
        ),
    )
    return entity.model_copy(update={"id": cursor.lastrowid})


def get_entity_by_id(conn: sqlite3.Connection, id: int) -> Optional[Entity]:
    row = conn.execute("SELECT * FROM entities WHERE id = ?", (id,)).fetchone()
    return _row_to_entity(row) if row else None


def find_entity_by_name_and_type(
    conn: sqlite3.Connection, name: str, entity_type: str
) -> Optional[Entity]:
    """Exact-match lookup only; no fuzzy matching, no judgment."""
    row = conn.execute(
        "SELECT * FROM entities WHERE name = ? AND entity_type = ?",
        (name, entity_type),
    ).fetchone()
    return _row_to_entity(row) if row else None


def update_entity_attributes(
    conn: sqlite3.Connection, id: int, attributes: dict[str, Any]
) -> Optional[Entity]:
    """Overwrite attributes wholesale and bump updated_at. Policy is the engine's."""
    updated_at = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "UPDATE entities SET attributes = ?, updated_at = ? WHERE id = ?",
        (json.dumps(attributes), updated_at, id),
    )
    if cursor.rowcount == 0:
        return None
    return get_entity_by_id(conn, id)


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------

def create_relationship(conn: sqlite3.Connection, relationship: Relationship) -> Relationship:
    cursor = conn.execute(
        """
        INSERT INTO relationships
            (source_entity_id, target_entity_id, relation_type,
             assertion_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship.relation_type,
            relationship.assertion_id,
            relationship.created_at.isoformat(),
        ),
    )
    return relationship.model_copy(update={"id": cursor.lastrowid})


def get_relationships_for_entity(
    conn: sqlite3.Connection, entity_id: int
) -> list[Relationship]:
    rows = conn.execute(
        "SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?",
        (entity_id, entity_id),
    ).fetchall()
    return [_row_to_relationship(row) for row in rows]


def trace_relationship_to_observation(
    conn: sqlite3.Connection, relationship_id: int
) -> Optional[tuple[Relationship, Assertion, Observation]]:
    """Walk Relationship -> Assertion -> Observation. None if the relationship is absent."""
    row = conn.execute(
        """
        SELECT
            r.id AS r_id, r.source_entity_id, r.target_entity_id,
            r.relation_type, r.assertion_id, r.created_at AS r_created_at,
            a.id AS a_id, a.observation_id, a.assertion_type,
            a.subject, a.predicate, a.object, a.metadata,
            a.created_at AS a_created_at,
            o.id AS o_id, o.raw_text, o.created_at AS o_created_at
        FROM relationships r
        JOIN assertions a ON a.id = r.assertion_id
        JOIN observations o ON o.id = a.observation_id
        WHERE r.id = ?
        """,
        (relationship_id,),
    ).fetchone()

    if row is None:
        return None

    relationship = Relationship(
        id=row["r_id"],
        source_entity_id=row["source_entity_id"],
        target_entity_id=row["target_entity_id"],
        relation_type=row["relation_type"],
        assertion_id=row["assertion_id"],
        created_at=datetime.fromisoformat(row["r_created_at"]),
    )
    assertion = Assertion(
        id=row["a_id"],
        observation_id=row["observation_id"],
        assertion_type=row["assertion_type"],
        subject=row["subject"],
        predicate=row["predicate"],
        object=row["object"],
        metadata=json.loads(row["metadata"]),
        created_at=datetime.fromisoformat(row["a_created_at"]),
    )
    observation = Observation(
        id=row["o_id"],
        raw_text=row["raw_text"],
        created_at=datetime.fromisoformat(row["o_created_at"]),
    )
    return relationship, assertion, observation

def find_assertion(conn: sqlite3.Connection, assertion: Assertion) -> Optional[Assertion]:
    """Exact natural-key lookup; used by the engine for idempotency."""
    row = conn.execute(
        """
        SELECT * FROM assertions
        WHERE observation_id = ? AND assertion_type = ? AND subject = ?
          AND predicate = ? AND object = ?
        """,
        (assertion.observation_id, assertion.assertion_type,
         assertion.subject, assertion.predicate, assertion.object),
    ).fetchone()
    return _row_to_assertion(row) if row else None

def get_relationship_by_assertion(conn: sqlite3.Connection, assertion_id: int) -> Optional[Relationship]:
    row = conn.execute(
        "SELECT * FROM relationships WHERE assertion_id = ?", (assertion_id,)
    ).fetchone()
    return _row_to_relationship(row) if row else None