import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from reality import bounded_snapshot as bs
from reality.classification import contracts, normalization
from tests.support.snapshot_cases import CASES

REPO = Path(__file__).resolve().parent.parent
MODULE_SOURCE = REPO / "reality" / "bounded_snapshot.py"
CASES_SOURCE = REPO / "tests" / "support" / "snapshot_cases.py"
GOLDEN = json.loads((REPO / "tests" / "support" / "snapshot_golden.json").read_text(encoding="utf-8"))
FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)

PUBLIC_NAMES = {
    "SNAPSHOT_VERSION", "MAX_PROJECTION_DEPTH", "MAX_PROJECTION_ITEMS",
    "MAX_PROJECTION_STR", "MAX_PROJECTION_NODES", "MAX_PAYLOAD_PREVIEW_CHARS",
    "INT_LIMIT", "project", "snapshot",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _canonical(value: object) -> str:
    return json.dumps(bs.project(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def test_golden_snapshots_are_identical_to_the_pre_move_behavior():
    assert set(GOLDEN["cases"]) == set(CASES)

    mismatched = []
    for name, build in CASES.items():
        value = build()
        preview, truncated, digest = bs.snapshot(value)
        actual = {
            "project_sha256": hashlib.sha256(_canonical(value).encode("ascii")).hexdigest(),
            "preview": preview,
            "truncated": truncated,
            "hash": digest,
        }
        if actual != GOLDEN["cases"][name]:
            mismatched.append(name)

    assert mismatched == []
    assert GOLDEN["constants"] == {
        "MAX_PROJECTION_DEPTH": bs.MAX_PROJECTION_DEPTH,
        "MAX_PROJECTION_ITEMS": bs.MAX_PROJECTION_ITEMS,
        "MAX_PROJECTION_STR": bs.MAX_PROJECTION_STR,
        "MAX_PROJECTION_NODES": bs.MAX_PROJECTION_NODES,
        "MAX_PAYLOAD_PREVIEW_CHARS": bs.MAX_PAYLOAD_PREVIEW_CHARS,
        "INT_LIMIT": bs.INT_LIMIT,
    }


def test_constants_and_version_are_pinned():
    # Changing a limit changes every snapshot: it must bump SNAPSHOT_VERSION
    # and be recorded in the RFC. Edit this test only together with both.
    assert (
        bs.MAX_PROJECTION_DEPTH, bs.MAX_PROJECTION_ITEMS, bs.MAX_PROJECTION_STR,
        bs.MAX_PROJECTION_NODES, bs.MAX_PAYLOAD_PREVIEW_CHARS, bs.INT_LIMIT,
    ) == (8, 64, 1024, 2000, 1024, 2**63)
    assert bs.SNAPSHOT_VERSION == 1


def test_public_surface_is_pinned():
    # Adding a public name to this module requires an RFC amendment: it exists
    # only to bound untrusted values, never to collect shared helpers.
    assert set(bs.__all__) == PUBLIC_NAMES
    assert len(bs.__all__) == len(PUBLIC_NAMES)


def test_module_imports_only_the_standard_library_allowlist():
    assert _imported_modules(MODULE_SOURCE) - {"hashlib", "json", "math", "typing"} == set()
    assert [m for m in _imported_modules(CASES_SOURCE) if m == "reality" or m.startswith("reality.")] == []


def test_snapshot_matches_an_independent_recomputation_of_the_canonical_form():
    for name, build in CASES.items():
        value = build()
        canonical = _canonical(value)
        expected = (
            canonical[:1024],
            len(canonical) > 1024,
            hashlib.sha256(canonical.encode("ascii")).hexdigest(),
        )
        assert bs.snapshot(value) == expected, name


def test_snapshots_are_deterministic_and_key_order_independent():
    assert bs.snapshot({"x": 1, "y": [1, 2]}) == bs.snapshot({"y": [1, 2], "x": 1})
    assert bs.snapshot({"x": 1})[2] != bs.snapshot({"x": 2})[2]
    for name, build in CASES.items():
        assert bs.snapshot(build()) == bs.snapshot(build()), name


def test_preview_is_bounded_and_the_flag_marks_only_a_cut_preview():
    for name, build in CASES.items():
        preview, _, _ = bs.snapshot(build())
        assert len(preview) <= bs.MAX_PAYLOAD_PREVIEW_CHARS, name

    # The canonical form of a string is its length plus two quote characters.
    assert bs.snapshot("x" * 1022)[1] is False
    assert bs.snapshot("x" * 1023)[1] is True

    # A cut made INSIDE the projection is marked in-band and does not set the flag.
    preview, truncated, _ = bs.snapshot({f"k{i}": i for i in range(65)})
    assert '"<truncated_items>":1' in preview
    assert truncated is False


def test_previews_are_pure_ascii_and_hashes_are_sha256_hex():
    for name, build in CASES.items():
        preview, _, digest = bs.snapshot(build())
        assert preview.isascii(), name
        assert re.fullmatch(r"[0-9a-f]{64}", digest), name


def test_classification_still_exports_the_same_limits_and_names():
    for name in ("MAX_PROJECTION_DEPTH", "MAX_PROJECTION_ITEMS", "MAX_PROJECTION_STR", "MAX_PROJECTION_NODES"):
        assert getattr(normalization, name) == getattr(bs, name)
        assert name in normalization.__all__
    for name in ("MAX_DOMAIN_NODES", "normalize_classification", "create_drop", "utc_now", "Clock"):
        assert name in normalization.__all__
        assert hasattr(normalization, name)
    assert contracts.MAX_PAYLOAD_PREVIEW_CHARS == bs.MAX_PAYLOAD_PREVIEW_CHARS
    assert normalization.snapshot is bs.snapshot


def test_create_drop_stores_exactly_the_snapshot():
    payload = {"a": ["x" * 5000], "b": None}

    drop = normalization.create_drop(payload, "SCHEMA_VIOLATION", lambda: FIXED)

    preview, truncated, digest = bs.snapshot(payload)
    assert (drop.payload_preview, drop.payload_truncated, drop.projection_hash) == (preview, truncated, digest)
    assert drop.payload_truncated is True


def test_classification_holds_no_second_copy_of_the_snapshot_logic():
    for name in ("_project", "_snapshot", "_INT_LIMIT", "hashlib"):
        assert not hasattr(normalization, name), name