import ast
import inspect
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from reality import audit_store, db
from reality.audit_store import AuditSchemaMismatch, SqliteAuditSink
from reality.bounded_snapshot import SNAPSHOT_VERSION, snapshot
from reality.extraction.audit import AuditSink
from reality.extraction.contracts import DroppedClaim

REALITY_DIR = Path(__file__).resolve().parent.parent / "reality"
AUDIT_STORE_SOURCE = REALITY_DIR / "audit_store.py"
ALLOWED_IMPORTS = {
    "os",
    "sqlite3",
    "datetime",
    "typing",
    "reality.bounded_snapshot",
    "reality.extraction.contracts",
}

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)

EXPECTED_COLUMNS = [
    ("id", "INTEGER"),
    ("recorded_at", "TEXT"),
    ("observation_id", "INTEGER"),
    ("stage", "TEXT"),
    ("reason_preview", "TEXT"),
    ("reason_truncated", "INTEGER"),
    ("reason_hash", "TEXT"),
    ("payload_preview", "TEXT"),
    ("payload_truncated", "INTEGER"),
    ("payload_hash", "TEXT"),
    ("snapshot_version", "INTEGER"),
]


def clock() -> datetime:
    return FIXED


def _exec(path, sql: str) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def _user_tables(conn) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def test_opening_a_new_path_creates_the_schema_the_version_stamp_and_the_index(tmp_path):
    path = tmp_path / "audit.db"

    SqliteAuditSink(path, clock=clock)

    conn = sqlite3.connect(path)
    try:
        assert audit_store.SCHEMA_VERSION == 1
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert _user_tables(conn) == {"extraction_drops"}

        columns = conn.execute("PRAGMA table_info(extraction_drops)").fetchall()
        assert [(c[1], c[2]) for c in columns] == EXPECTED_COLUMNS
        assert [c[1] for c in columns if c[5]] == ["id"]            # primary key
        assert all(c[3] == 1 for c in columns if c[1] != "id")      # NOT NULL

        indexes = conn.execute("PRAGMA index_list(extraction_drops)").fetchall()
        indexed = [
            [i[2] for i in conn.execute(f"PRAGMA index_info({idx[1]})").fetchall()]
            for idx in indexes
        ]
        assert ["observation_id"] in indexed
    finally:
        conn.close()


def test_reopening_an_existing_store_changes_nothing(tmp_path):
    path = tmp_path / "audit.db"
    SqliteAuditSink(path, clock=clock)
    before = path.read_bytes()

    SqliteAuditSink(path, clock=clock)

    assert path.read_bytes() == before


def test_a_zero_byte_file_is_treated_as_a_new_database(tmp_path):
    path = tmp_path / "audit.db"
    path.write_bytes(b"")

    SqliteAuditSink(path, clock=clock)

    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert _user_tables(conn) == {"extraction_drops"}
    finally:
        conn.close()


def _version_two(path) -> None:
    SqliteAuditSink(path, clock=clock)
    _exec(path, "PRAGMA user_version = 2")


def _foreign_tables(path) -> None:
    _exec(path, "CREATE TABLE entities (id INTEGER PRIMARY KEY)")


def _missing_column(path) -> None:
    _exec(
        path,
        "CREATE TABLE extraction_drops "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, recorded_at TEXT NOT NULL)",
    )
    _exec(path, "PRAGMA user_version = 1")


def _extra_table(path) -> None:
    SqliteAuditSink(path, clock=clock)
    _exec(path, "CREATE TABLE stray (x TEXT)")


def _no_tables(path) -> None:
    # Create and drop a table so the file is non-empty, then stamp version 1.
    _exec(path, "CREATE TABLE t (x TEXT)")
    _exec(path, "DROP TABLE t")
    _exec(path, "PRAGMA user_version = 1")


@pytest.mark.parametrize(
    "prepare, found",
    [
        (_version_two, 2),
        (_foreign_tables, 0),
        (_missing_column, 1),
        (_extra_table, 1),
        (_no_tables, 1),
    ],
    ids=["version-2", "foreign-tables-version-0", "version-1-missing-column",
         "version-1-extra-table", "version-1-no-tables"],
)
def test_a_schema_or_version_mismatch_fails_loudly_and_changes_nothing(tmp_path, prepare, found):
    path = tmp_path / "audit.db"
    prepare(path)
    assert path.stat().st_size > 0
    before = path.read_bytes()

    with pytest.raises(AuditSchemaMismatch) as caught:
        SqliteAuditSink(path, clock=clock)

    assert caught.value.found_version == found
    assert caught.value.expected_version == 1
    assert path.read_bytes() == before


def test_a_file_that_is_not_a_database_raises_and_is_left_unchanged(tmp_path):
    path = tmp_path / "audit.db"
    path.write_bytes(b"this is not an sqlite database " * 100)
    before = path.read_bytes()

    with pytest.raises(sqlite3.DatabaseError):
        SqliteAuditSink(path, clock=clock)

    assert path.read_bytes() == before


def test_a_missing_parent_directory_raises_and_is_not_created(tmp_path):
    parent = tmp_path / "missing"

    with pytest.raises(sqlite3.OperationalError):
        SqliteAuditSink(parent / "audit.db", clock=clock)

    assert not parent.exists()


@pytest.mark.parametrize(
    "path_kind, clock_arg, match",
    [
        ("none", clock, "path"),
        ("empty", clock, "path"),
        ("memory", clock, "path"),
        ("valid", None, "clock"),
    ],
    ids=["none-path", "empty-path", "memory-path", "none-clock"],
)
def test_bad_constructor_arguments_are_refused_before_anything_is_created(
    tmp_path, path_kind, clock_arg, match
):
    path = {"none": None, "empty": "", "memory": ":memory:", "valid": tmp_path / "audit.db"}[path_kind]

    with pytest.raises(ValueError, match=match):
        SqliteAuditSink(path, clock=clock_arg)

    assert list(tmp_path.iterdir()) == []


def test_a_failure_while_stamping_the_version_leaves_no_partial_schema(tmp_path, monkeypatch):
    path = tmp_path / "audit.db"

    # The version is formatted into a PRAGMA at creation time. A value that
    # makes it two statements fails AFTER the tables were created, inside the
    # same transaction, so nothing may survive.
    with monkeypatch.context() as patch:
        patch.setattr(audit_store, "SCHEMA_VERSION", "1; SELECT 1")
        with pytest.raises(Exception):
            SqliteAuditSink(path, clock=clock)

    conn = sqlite3.connect(path)
    try:
        assert _user_tables(conn) == set()
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    finally:
        conn.close()

    SqliteAuditSink(path, clock=clock)  # a retry on the same path succeeds

    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert _user_tables(conn) == {"extraction_drops"}
    finally:
        conn.close()

def _drop(**overrides) -> DroppedClaim:
    fields = dict(
        stage="validation",
        reason="Semantic validation failed: assertion_type is not declared.",
        payload_projection={"subject_text": "Sara"},
        observation_id=7,
    )
    fields.update(overrides)
    return DroppedClaim(**fields)


def _rows(path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM extraction_drops ORDER BY id").fetchall()
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


def test_a_record_round_trips_with_the_injected_clock_and_the_snapshot_version(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)
    drop = _drop()

    sink.record(drop)

    rows = _rows(path)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == 1
    assert row["recorded_at"] == "2026-01-01T00:00:00+00:00"
    assert row["observation_id"] == 7
    assert row["stage"] == "validation"
    assert row["snapshot_version"] == SNAPSHOT_VERSION
    # Independent expectation: the canonical JSON text of each value.
    assert row["reason_preview"] == json.dumps(drop.reason)
    assert row["reason_truncated"] == 0
    assert row["payload_preview"] == '{"subject_text":"Sara"}'
    assert row["payload_truncated"] == 0
    assert len(row["reason_hash"]) == 64 and len(row["payload_hash"]) == 64


def test_the_reason_is_stored_through_the_shared_snapshot_never_as_raw_text(tmp_path):
    path = tmp_path / "audit.db"
    reason = 'دلیل ناموفق "quoted" \n second line'
    SqliteAuditSink(path, clock=clock).record(_drop(reason=reason))

    row = _rows(path)[0]
    preview, truncated, digest = snapshot(reason)
    assert (row["reason_preview"], row["reason_truncated"], row["reason_hash"]) == (
        preview, int(truncated), digest,
    )
    assert row["reason_preview"].isascii()
    assert row["reason_preview"] != reason


def test_the_payload_is_stored_through_the_shared_snapshot(tmp_path):
    path = tmp_path / "audit.db"
    projection = {"subject_text": "سارا", "type_hints": {"a": "b"}, "nested": [1, None, True]}
    SqliteAuditSink(path, clock=clock).record(_drop(payload_projection=projection))

    row = _rows(path)[0]
    preview, truncated, digest = snapshot(projection)
    assert (row["payload_preview"], row["payload_truncated"], row["payload_hash"]) == (
        preview, int(truncated), digest,
    )


def test_a_hundred_thousand_key_payload_is_stored_bounded(tmp_path):
    path = tmp_path / "audit.db"
    projection = {f"k{i}": i for i in range(100_000)}
    SqliteAuditSink(path, clock=clock).record(_drop(payload_projection=projection))

    row = _rows(path)[0]
    assert len(row["payload_preview"]) <= 1024
    assert '"<truncated_items>":99936' in row["payload_preview"]
    assert len(row["payload_hash"]) == 64
    assert path.stat().st_size < 100_000


def test_an_oversized_reason_is_bounded_and_flagged_and_a_short_one_is_not(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)

    sink.record(_drop(reason="x" * 5000))
    sink.record(_drop(reason="short reason"))

    long_row, short_row = _rows(path)
    assert long_row["reason_truncated"] == 1
    assert len(long_row["reason_preview"]) <= 1024
    assert len(long_row["reason_hash"]) == 64
    assert short_row["reason_truncated"] == 0


def test_a_lone_surrogate_cannot_break_the_audit_write(tmp_path):
    path = tmp_path / "audit.db"
    drop = DroppedClaim.model_construct(
        stage="normalization",
        reason="bad\ud800reason",
        payload_projection={"value": "bad\ud800text"},
        observation_id=3,
    )

    SqliteAuditSink(path, clock=clock).record(drop)

    row = _rows(path)[0]
    assert row["reason_preview"].isascii()
    assert row["payload_preview"].isascii()


def test_a_drop_without_an_observation_id_is_refused_and_nothing_is_written(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)

    with pytest.raises(ValueError, match="observation_id"):
        sink.record(_drop(observation_id=None))

    assert _rows(path) == []


def test_identical_drops_are_two_rows(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)
    drop = _drop()

    sink.record(drop)
    sink.record(drop)

    first, second = _rows(path)
    assert first["id"] != second["id"]
    assert {k: first[k] for k in first.keys() if k != "id"} == {
        k: second[k] for k in second.keys() if k != "id"
    }


def test_row_ids_follow_the_order_of_the_calls(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)

    for observation_id, stage in ((3, "normalization"), (1, "validation"), (2, "normalization")):
        sink.record(_drop(observation_id=observation_id, stage=stage))

    rows = _rows(path)
    assert [r["observation_id"] for r in rows] == [3, 1, 2]
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids) and len(set(ids)) == 3


def test_a_naive_clock_value_is_refused_and_nothing_is_written(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=lambda: datetime(2026, 1, 1))

    with pytest.raises(ValueError, match="timezone"):
        sink.record(_drop())

    assert _rows(path) == []


def test_the_clock_is_read_once_per_record_and_stored_as_utc(tmp_path):
    path = tmp_path / "audit.db"
    tehran = timezone(timedelta(hours=3, minutes=30))
    times = iter([FIXED, FIXED + timedelta(seconds=5), datetime(2026, 1, 1, 3, 30, tzinfo=tehran)])
    calls: list[int] = []

    def ticking() -> datetime:
        calls.append(1)
        return next(times)

    sink = SqliteAuditSink(path, clock=ticking)
    assert calls == []  # construction must not read the clock

    for _ in range(3):
        sink.record(_drop())

    assert len(calls) == 3
    assert [r["recorded_at"] for r in _rows(path)] == [
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:05+00:00",
        "2026-01-01T00:00:00+00:00",
    ]


def test_a_file_deleted_after_construction_fails_loudly_and_is_never_silently_recreated(tmp_path):
    path = tmp_path / "audit.db"
    sink = SqliteAuditSink(path, clock=clock)
    path.unlink()

    with pytest.raises(sqlite3.OperationalError):
        sink.record(_drop())

    if path.exists():
        conn = sqlite3.connect(path)
        try:
            assert _user_tables(conn) == set()
        finally:
            conn.close()


def test_the_public_api_is_exactly_record():
    # Append-only is enforced by API surface (R2-D14): no update, no delete.
    assert [n for n in dir(SqliteAuditSink) if not n.startswith("_")] == ["record"]


def test_the_record_signature_conforms_to_the_audit_sink_protocol():
    ours = inspect.signature(SqliteAuditSink.record)
    protocol = inspect.signature(AuditSink.record)

    assert list(ours.parameters) == list(protocol.parameters) == ["self", "drop"]
    assert ours.return_annotation is None or ours.return_annotation == protocol.return_annotation


def test_only_the_audit_file_is_created_and_reality_storage_is_untouched(tmp_path, monkeypatch):
    reality_path = tmp_path / "reality.db"
    monkeypatch.setattr(db, "DB_PATH", reality_path)
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()

    sink = SqliteAuditSink(audit_dir / "audit.db", clock=clock)
    sink.record(_drop())

    assert sorted(p.name for p in audit_dir.iterdir()) == ["audit.db"]
    assert not reality_path.exists()


def test_the_store_imports_only_its_allowlist():
    assert _imported_modules(AUDIT_STORE_SOURCE) - ALLOWED_IMPORTS == set()


def test_nothing_else_in_reality_imports_the_store():
    offenders = {}
    for path in REALITY_DIR.rglob("*.py"):
        # audit_diagnostics is the one sanctioned reader (R2.6): it imports
        # only SCHEMA_VERSION and AuditSchemaMismatch, enforced by
        # test_audit_diagnostics.py. Anything else importing the store is
        # still a wiring violation.
        if path.name in ("audit_store.py", "audit_diagnostics.py"):
            continue
        hits = sorted(
            m for m in _imported_modules(path)
            if m == "reality.audit_store" or m.startswith("reality.audit_store.")
        )
        if hits:
            offenders[str(path.relative_to(REALITY_DIR))] = hits
    assert offenders == {}


def test_the_database_rejects_an_invalid_stage(tmp_path):
    path = tmp_path / "audit.db"
    SqliteAuditSink(path, clock=clock)

    conn = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO extraction_drops (recorded_at, observation_id, stage, "
                "reason_preview, reason_truncated, reason_hash, payload_preview, "
                "payload_truncated, payload_hash, snapshot_version) "
                "VALUES ('t', 1, 'bogus', 'r', 0, 'h', 'p', 0, 'h', 1)"
            )
    finally:
        conn.close()