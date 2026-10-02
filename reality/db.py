"""
reality/db.py

Owns the SQLite connection and table creation for Zehn.
No business logic and no repository (CRUD) logic lives here —
this file only knows how to connect and how to create the schema.

This is the frozen data-layer contract for Milestone 1.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Database lives at data/zehn.db, relative to the project root.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "zehn.db"


def get_connection() -> sqlite3.Connection:
    """
    Return a SQLite connection with sane defaults for this project:
    - row_factory so query results behave like dicts (row["column"])
    - foreign_keys enforced, since our trace (Relationship -> Assertion
      -> Observation) and our integrity constraints depend on it.
      SQLite ignores FOREIGN KEY clauses unless this is set per-connection.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ensure data/ exists

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def transaction():
    """
    One connection, one atomic unit of work. Commits on success, rolls back
    on ANY exception, always closes. The caller (the engine) owns this
    boundary; repository functions never commit.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize_database() -> None:
    """
    Create all Zehn tables (and supporting indexes) if they don't
    already exist. Safe to call every time the app starts.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # observations: immutable record of raw user input.
        # Nothing ever references INTO observations except by id;
        # this table is only ever appended to.
        # CHECK guards against empty/whitespace-only text making it to
        # storage even if a caller bypasses Pydantic validation.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL CHECK (length(trim(raw_text)) > 0),
                created_at TEXT NOT NULL
            )
        """)

        # assertions: structured claims extracted from an observation,
        # before being resolved into entities/relationships.
        # metadata is stored as a JSON string (SQLite has no native JSON type).
        # ON DELETE CASCADE: if an observation is ever removed, its derived
        # assertions are no longer meaningful and go with it.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assertions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_id INTEGER NOT NULL,
                assertion_type TEXT NOT NULL CHECK (length(trim(assertion_type)) > 0),
                subject TEXT NOT NULL CHECK (length(trim(subject)) > 0),
                predicate TEXT NOT NULL CHECK (length(trim(predicate)) > 0),
                object TEXT NOT NULL CHECK (length(trim(object)) > 0),
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (observation_id) REFERENCES observations(id)
                    ON DELETE CASCADE,
                UNIQUE (observation_id, assertion_type, subject, predicate, object)
            )
        """)

        # entities: persistent nodes in the reality model.
        # attributes is stored as a JSON string for flexibility across
        # very different entity types (Person, Project, Event, ...).
        # UNIQUE(name, entity_type) is the naive v0.1 resolution key:
        # the same name within the same type is treated as one entity.
        # (Known limitation: no fuzzy/alias matching yet — acceptable
        # for Milestone 1, to be handled by the Reality Engine later.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                entity_type TEXT NOT NULL CHECK (length(trim(entity_type)) > 0),
                attributes TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (name, entity_type)
            )
        """)

        # relationships: typed edges between two entities, each one
        # traceable back to the single assertion that produced it.
        # ON DELETE CASCADE on entity/assertion removal keeps the graph
        # consistent without needing manual cleanup logic elsewhere.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity_id INTEGER NOT NULL,
                target_entity_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL CHECK (length(trim(relation_type)) > 0),
                assertion_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_entity_id) REFERENCES entities(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (target_entity_id) REFERENCES entities(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (assertion_id) REFERENCES assertions(id)
                    ON DELETE CASCADE,
                UNIQUE (assertion_id)
            )
        """)

        # --- Indexes ---
        # Only added where they support a lookup Zehn actually needs:
        # tracing assertions back to their observation, tracing
        # relationships back to entities/assertions, and looking up
        # entities by type (used constantly during resolution).
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assertions_observation_id "
            "ON assertions(observation_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_source_entity_id "
            "ON relationships(source_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_target_entity_id "
            "ON relationships(target_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_assertion_id "
            "ON relationships(assertion_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_entity_type "
            "ON entities(entity_type)"
        )
        # Note: UNIQUE(name, entity_type) above already creates an implicit
        # index covering exact-match entity resolution lookups, so no
        # separate index is added for that pair.

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # Manual sanity check: running `python -m reality.db` sets up the DB.
    initialize_database()
    print(f"Database initialized at {DB_PATH}")
