"""Read-only diagnostics over the persistent audit store (R2.6).

Dependency direction (R2-D7): the write path never imports this module.
Schema authority stays in reality.audit_store; this module only checks the
version it stamped.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from reality.audit_store import SCHEMA_VERSION, AuditSchemaMismatch

__all__ = ["AuditRecord", "drops_for_observation", "count_drops"]

_COLUMNS = (
    "id, recorded_at, observation_id, stage, "
    "reason_preview, reason_truncated, reason_hash, "
    "payload_preview, payload_truncated, payload_hash, snapshot_version"
)


@dataclass(frozen=True)
class AuditRecord:
    id: int
    recorded_at: datetime
    observation_id: int
    stage: str
    reason_preview: str
    reason_truncated: bool
    reason_hash: str
    payload_preview: str
    payload_truncated: bool
    payload_hash: str
    snapshot_version: int


def _open_read_only(path) -> sqlite3.Connection:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _check_version(conn: sqlite3.Connection) -> None:
    found = conn.execute("PRAGMA user_version").fetchone()[0]
    if found != SCHEMA_VERSION:
        raise AuditSchemaMismatch(
            found_version=found,
            expected_version=SCHEMA_VERSION,
            detail="audit store has an unsupported schema version",
        )


def drops_for_observation(path, observation_id: int) -> tuple[AuditRecord, ...]:
    conn = _open_read_only(path)
    try:
        _check_version(conn)
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM extraction_drops "
            "WHERE observation_id = ? ORDER BY id ASC",
            (observation_id,),
        ).fetchall()
    finally:
        conn.close()
    return tuple(
        AuditRecord(
            id=row[0],
            recorded_at=datetime.fromisoformat(row[1]),
            observation_id=row[2],
            stage=row[3],
            reason_preview=row[4],
            reason_truncated=bool(row[5]),
            reason_hash=row[6],
            payload_preview=row[7],
            payload_truncated=bool(row[8]),
            payload_hash=row[9],
            snapshot_version=row[10],
        )
        for row in rows
    )


def count_drops(path) -> int:
    conn = _open_read_only(path)
    try:
        _check_version(conn)
        return conn.execute("SELECT COUNT(*) FROM extraction_drops").fetchone()[0]
    finally:
        conn.close()