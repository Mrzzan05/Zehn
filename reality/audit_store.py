"""
reality/audit_store.py

Persistent audit store for extraction drops (RFC-004 R2-D2).

The store lives in its OWN SQLite file: a separate file, a separate
connection and a separate transaction from Reality. There is no ATTACH, no
foreign key and no import of Reality storage. A rollback in one database can
never affect the other.

Opening a database (R2-D11, R2-D15). Opening NEVER upgrades, recreates or
repairs anything:

  * a new database (user_version 0 and no tables) is created and stamped in
    ONE transaction, so a crash cannot leave tables without a version stamp;
  * a database with the expected version and exactly the expected schema is
    opened untouched;
  * anything else raises AuditSchemaMismatch: another version, a foreign
    database (including Reality's), or a changed schema.

Writing a record (R2-D3, R2-D5, R2-D9, R2-D12, R2-D14). The store is
append-only: ``record`` is its only public method, so there is no update and
no delete path. Each call:

  * refuses a drop that carries no observation_id (extract() always stamps
    it), before anything is read or written;
  * reads the injected clock once and requires a timezone-aware value, stored
    as UTC; recorded_at is informational, ordering is by the id;
  * stores BOTH the reason and the payload projection only as snapshot()
    output (bounded, ASCII-canonical, flagged, hashed), never as raw text;
  * records the snapshot format version beside every row;
  * uses its own connection and a single INSERT, which is its own atomic
    transaction.

Both collaborators are required and explicit, with no defaults and no module
state: the file path and the clock.
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Callable, Final

from reality.bounded_snapshot import SNAPSHOT_VERSION, snapshot
from reality.extraction.contracts import DroppedClaim

__all__ = ["SCHEMA_VERSION", "AuditSchemaMismatch", "SqliteAuditSink"]

SCHEMA_VERSION: Final = 1

_CREATE_TABLE: Final = """
CREATE TABLE extraction_drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    observation_id INTEGER NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('normalization', 'validation')),
    reason_preview TEXT NOT NULL,
    reason_truncated INTEGER NOT NULL,
    reason_hash TEXT NOT NULL,
    payload_preview TEXT NOT NULL,
    payload_truncated INTEGER NOT NULL,
    payload_hash TEXT NOT NULL,
    snapshot_version INTEGER NOT NULL
)
"""

_CREATE_INDEX: Final = (
    "CREATE INDEX idx_extraction_drops_observation_id "
    "ON extraction_drops (observation_id)"
)

_INSERT: Final = """
INSERT INTO extraction_drops (
    recorded_at, observation_id, stage,
    reason_preview, reason_truncated, reason_hash,
    payload_preview, payload_truncated, payload_hash,
    snapshot_version
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# (name, declared type, not null, primary key) in column order.
_EXPECTED_COLUMNS: Final = (
    ("id", "INTEGER", 0, 1),
    ("recorded_at", "TEXT", 1, 0),
    ("observation_id", "INTEGER", 1, 0),
    ("stage", "TEXT", 1, 0),
    ("reason_preview", "TEXT", 1, 0),
    ("reason_truncated", "INTEGER", 1, 0),
    ("reason_hash", "TEXT", 1, 0),
    ("payload_preview", "TEXT", 1, 0),
    ("payload_truncated", "INTEGER", 1, 0),
    ("payload_hash", "TEXT", 1, 0),
    ("snapshot_version", "INTEGER", 1, 0),
)


class AuditSchemaMismatch(Exception):
    """
    The database is not an audit store this code can use: another schema
    version, a foreign database, or a changed schema. It is raised at
    construction and never repaired, upgraded or recreated (I-40).
    """

    def __init__(self, found_version: int, expected_version: int, detail: str) -> None:
        super().__init__(
            f"Audit database schema mismatch: found user_version {found_version}, "
            f"expected {expected_version} ({detail})."
        )
        self.found_version = found_version
        self.expected_version = expected_version


def _user_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'"
    ).fetchall()
    return {row[0] for row in rows}


def _schema_matches(conn: sqlite3.Connection) -> bool:
    if _user_tables(conn) != {"extraction_drops"}:
        return False
    rows = conn.execute("PRAGMA table_info(extraction_drops)").fetchall()
    return tuple((r[1], r[2], r[3], r[5]) for r in rows) == _EXPECTED_COLUMNS


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create the tables, the index and the version stamp in ONE transaction."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
        # PRAGMA cannot take bound parameters. SCHEMA_VERSION is a module
        # constant (an int), never external input.
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def _open_or_create(path: str) -> None:
    # isolation_level=None: no implicit transactions, so every transaction
    # below is explicit and DDL takes part in it.
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = _user_tables(conn)

        if version == 0 and not tables:
            _create_schema(conn)
            return
        if version == 0:
            raise AuditSchemaMismatch(
                0, SCHEMA_VERSION, "unstamped database that already contains tables"
            )
        if version != SCHEMA_VERSION:
            raise AuditSchemaMismatch(version, SCHEMA_VERSION, "unsupported schema version")
        if not _schema_matches(conn):
            raise AuditSchemaMismatch(
                version, SCHEMA_VERSION, "tables or columns differ from the expected schema"
            )
    finally:
        conn.close()


class SqliteAuditSink:
    """
    Persistent AuditSink backed by its own SQLite file.

    ``path`` and ``clock`` are required: a forgotten collaborator must be
    impossible, not silent. The parent directory is NOT created here; the
    composition root owns directories. ``":memory:"`` is refused because every
    record uses its own connection and would silently lose all data.
    """

    def __init__(self, path: "str | os.PathLike[str]", *, clock: Callable[[], datetime]) -> None:
        if path is None:
            raise ValueError("path must be an explicit file path (got None).")
        text = os.fspath(path)
        if text == "":
            raise ValueError("path must not be empty.")
        if text == ":memory:":
            raise ValueError(
                "path must be a file: ':memory:' would silently lose every record "
                "because each record uses its own connection."
            )
        if clock is None:
            raise ValueError("clock must be injected explicitly (got None).")

        self._path = text
        self._clock = clock
        _open_or_create(text)

    def record(self, drop: DroppedClaim) -> None:
        """Append one bounded record. Never updates or deletes anything."""
        if drop.observation_id is None:
            raise ValueError(
                "drop.observation_id must be set before a drop is recorded "
                "(extract() stamps it)."
            )

        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime.")
        recorded_at = now.astimezone(timezone.utc).isoformat()

        # The same bounding function for every provider-influenced value (I-37).
        reason_preview, reason_truncated, reason_hash = snapshot(drop.reason)
        payload_preview, payload_truncated, payload_hash = snapshot(drop.payload_projection)

        # A file that vanished after construction is a loud failure. It is
        # never recreated: sqlite3.connect would otherwise create an empty one.
        if not os.path.exists(self._path):
            raise sqlite3.OperationalError("audit database file is missing.")

        # Its own connection; a single INSERT in autocommit mode is atomic.
        conn = sqlite3.connect(self._path, isolation_level=None)
        try:
            conn.execute(
                _INSERT,
                (
                    recorded_at,
                    drop.observation_id,
                    drop.stage,
                    reason_preview,
                    int(reason_truncated),
                    reason_hash,
                    payload_preview,
                    int(payload_truncated),
                    payload_hash,
                    SNAPSHOT_VERSION,
                ),
            )
        finally:
            conn.close()