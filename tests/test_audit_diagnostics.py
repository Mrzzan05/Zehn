import ast
import dataclasses
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from reality import audit_diagnostics
from reality.audit_diagnostics import AuditRecord, count_drops, drops_for_observation
from reality.audit_store import AuditSchemaMismatch, SqliteAuditSink
from reality.bounded_snapshot import SNAPSHOT_VERSION, snapshot
from reality.extraction.contracts import DroppedClaim

REALITY_DIR = Path(__file__).resolve().parent.parent / "reality"
DIAGNOSTICS_SOURCE = REALITY_DIR / "audit_diagnostics.py"

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)

# The write path (R2-D7): none of these may depend on diagnostics. This is a
# dependency-direction rule, so it lists modules explicitly instead of
# scanning the whole package: a future read-only facade inside reality/ is
# allowed to import diagnostics.
WRITE_PATH = sorted((REALITY_DIR / "extraction").glob("*.py")) + [
    REALITY_DIR / name
    for name in ("orchestrator.py", "engine.py", "repository.py", "audit_store.py", "db.py")
]

ALLOWED_IMPORTS = {
    "dataclasses",
    "datetime",
    "os",
    "pathlib",
    "sqlite3",
    "typing",
    "reality.audit_store",
}

RECORD_FIELDS = [
    "id",
    "recorded_at",
    "observation_id",
    "stage",
    "reason_preview",
    "reason_truncated",
    "reason_hash",
    "payload_preview",
    "payload_truncated",
    "payload_hash",
    "snapshot_version",
]


def clock() -> datetime:
    return FIXED


def _drop(observation_id=7, stage="validation", reason=None, projection=None) -> DroppedClaim:
    return DroppedClaim(
        stage=stage,
        reason="Semantic validation failed: assertion_type is not declared."
        if reason is None else reason,
        payload_projection={"subject_text": "Sara"} if projection is None else projection,
        observation_id=observation_id,
    )


def _store(path) -> SqliteAuditSink:
    return SqliteAuditSink(path, clock=clock)


def _exec(path, sql: str) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            if node.module == "reality":
                modules.update(f"reality.{alias.name}" for alias in node.names)
    return modules


def test_records_come_back_in_id_order_with_every_field_mapped(tmp_path):
    # The directory name holds a space and URI-special characters on purpose:
    # the read-only URI must be built from the path safely.
    directory = tmp_path / "a b!c#d%e"
    directory.mkdir()
    path = directory / "audit.db"
    sink = _store(path)
    short = _drop(stage="validation")
    oversized = _drop(stage="normalization", reason="x" * 5000, projection={"value": "y"})
    sink.record(short)
    sink.record(oversized)

    records = drops_for_observation(path, 7)

    assert [r.id for r in records] == [1, 2]
    first, second = records
    assert isinstance(first, AuditRecord)
    assert first.recorded_at == FIXED
    assert first.recorded_at.tzinfo is not None
    assert first.observation_id == 7
    assert first.stage == "validation"
    assert first.snapshot_version == SNAPSHOT_VERSION

    reason_preview, reason_truncated, reason_hash = snapshot(short.reason)
    assert (first.reason_preview, first.reason_truncated, first.reason_hash) == (
        reason_preview, reason_truncated, reason_hash,
    )
    assert first.reason_preview == json.dumps(short.reason)
    payload_preview, payload_truncated, payload_hash = snapshot(short.payload_projection)
    assert (first.payload_preview, first.payload_truncated, first.payload_hash) == (
        payload_preview, payload_truncated, payload_hash,
    )

    # Flags are real booleans, not the stored 0 and 1.
    assert first.reason_truncated is False and first.payload_truncated is False
    assert second.stage == "normalization"
    assert second.reason_truncated is True
    assert second.payload_truncated is False


def test_the_filter_is_exact_and_observations_are_separable(tmp_path):
    path = tmp_path / "audit.db"
    sink = _store(path)
    for observation_id in (7, 3, 7, 70, 3):  # 7 and 70 must never mix
        sink.record(_drop(observation_id=observation_id))

    assert [r.id for r in drops_for_observation(path, 7)] == [1, 3]
    assert [r.id for r in drops_for_observation(path, 3)] == [2, 5]
    assert [r.id for r in drops_for_observation(path, 70)] == [4]
    assert {r.observation_id for r in drops_for_observation(path, 7)} == {7}


def test_an_unknown_observation_id_returns_an_empty_tuple(tmp_path):
    path = tmp_path / "audit.db"
    _store(path).record(_drop(observation_id=7))

    result = drops_for_observation(path, 999)

    assert result == ()
    assert isinstance(result, tuple)


def test_count_drops_returns_the_total_and_zero_for_an_empty_store(tmp_path):
    path = tmp_path / "audit.db"
    sink = _store(path)
    assert count_drops(path) == 0

    for observation_id in (1, 2, 2):
        sink.record(_drop(observation_id=observation_id))

    assert count_drops(path) == 3


def test_the_connection_is_read_only(tmp_path):
    path = tmp_path / "audit.db"
    _store(path).record(_drop())

    # Proves mode=ro itself, without relying on file permissions, which are
    # unreliable on Windows.
    conn = audit_diagnostics._open_read_only(path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM extraction_drops").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute(
                "INSERT INTO extraction_drops (recorded_at, observation_id, stage, "
                "reason_preview, reason_truncated, reason_hash, payload_preview, "
                "payload_truncated, payload_hash, snapshot_version) "
                "VALUES ('t', 1, 'validation', 'r', 0, 'h', 'p', 0, 'h', 1)"
            )
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM extraction_drops")
    finally:
        conn.close()


def test_a_missing_file_raises_and_is_not_created(tmp_path):
    path = tmp_path / "nope.db"

    with pytest.raises(sqlite3.OperationalError):
        count_drops(path)
    with pytest.raises(sqlite3.OperationalError):
        drops_for_observation(path, 1)

    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def _version_two(path) -> None:
    _store(path)
    _exec(path, "PRAGMA user_version = 2")


def _foreign_database(path) -> None:
    _exec(path, "CREATE TABLE entities (id INTEGER PRIMARY KEY)")


@pytest.mark.parametrize(
    "prepare, found",
    [(_version_two, 2), (_foreign_database, 0)],
    ids=["version-2", "foreign-database-version-0"],
)
def test_a_version_mismatch_fails_loudly_through_both_functions_and_changes_nothing(
    tmp_path, prepare, found
):
    path = tmp_path / "audit.db"
    prepare(path)
    before = path.read_bytes()

    for call in (lambda: count_drops(path), lambda: drops_for_observation(path, 1)):
        with pytest.raises(AuditSchemaMismatch) as caught:
            call()
        assert caught.value.found_version == found
        assert caught.value.expected_version == 1

    assert path.read_bytes() == before


def test_reading_changes_nothing_and_leaves_no_side_files(tmp_path):
    path = tmp_path / "audit.db"
    _store(path).record(_drop())
    before = path.read_bytes()

    for _ in range(2):
        drops_for_observation(path, 7)
        drops_for_observation(path, 999)
        count_drops(path)

    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["audit.db"]


def test_records_are_frozen_and_results_are_tuples(tmp_path):
    path = tmp_path / "audit.db"
    _store(path).record(_drop())

    records = drops_for_observation(path, 7)

    assert isinstance(records, tuple)
    assert dataclasses.is_dataclass(AuditRecord)
    assert [f.name for f in dataclasses.fields(AuditRecord)] == RECORD_FIELDS
    with pytest.raises(dataclasses.FrozenInstanceError):
        records[0].stage = "normalization"


def test_the_write_path_never_imports_diagnostics():
    assert len(WRITE_PATH) >= 6  # a renamed or moved module must not pass vacuously
    missing = [str(p.relative_to(REALITY_DIR)) for p in WRITE_PATH if not p.exists()]
    assert missing == []

    offenders = {}
    for path in WRITE_PATH:
        hits = sorted(
            m for m in _imported_modules(path)
            if m == "reality.audit_diagnostics" or m.startswith("reality.audit_diagnostics.")
        )
        if hits:
            offenders[str(path.relative_to(REALITY_DIR))] = hits
    assert offenders == {}


def test_the_module_imports_only_its_allowlist_and_exports_only_three_names():
    assert _imported_modules(DIAGNOSTICS_SOURCE) - ALLOWED_IMPORTS == set()
    # Public surface (R2-D7): nothing beyond these three belongs in R2.6.
    assert set(audit_diagnostics.__all__) == {"AuditRecord", "drops_for_observation", "count_drops"}