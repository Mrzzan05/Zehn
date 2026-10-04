"""
reality/bounded_snapshot.py

Neutral, deterministic bounding of untrusted objects (RFC-004 R2-D8).

This module converts an arbitrary object into a BOUNDED, JSON-safe,
canonical form, and fingerprints it. That is all it does.

Admission rule: BOUNDS, NOT POLICY. The module may define how much of an
untrusted value is retained and how it is fingerprinted. It must never
decide whether a value is acceptable, interpret a rejection, touch a domain
type, a clock, storage or any I/O, and it imports only the standard library.
Anything that is not "how much do we keep" belongs elsewhere.

Changing any limit below changes every snapshot, so it must also bump
SNAPSHOT_VERSION (stored beside every persisted record, R2-D12).

Both functions are total: they never raise and never call str()/repr() on
the input, so no user-defined code runs. Only the exact type name of unknown
objects is recorded.

Semantics worth stating precisely:
  * ``truncated`` means ONLY that the preview string was cut. Cuts made
    inside the projection (more than MAX_PROJECTION_ITEMS items, depth over
    MAX_PROJECTION_DEPTH, a string over MAX_PROJECTION_STR) are marked
    in-band and do not set the flag.
  * The hash identifies the bounded projection, not the raw payload: two
    different payloads sharing the same bounded projection hash equally.
"""

import hashlib
import json
import math
from typing import Final, cast

__all__ = [
    "SNAPSHOT_VERSION",
    "MAX_PROJECTION_DEPTH",
    "MAX_PROJECTION_ITEMS",
    "MAX_PROJECTION_STR",
    "MAX_PROJECTION_NODES",
    "MAX_PAYLOAD_PREVIEW_CHARS",
    "INT_LIMIT",
    "project",
    "snapshot",
]

SNAPSHOT_VERSION: Final = 1

MAX_PROJECTION_DEPTH: Final = 8
MAX_PROJECTION_ITEMS: Final = 64
MAX_PROJECTION_STR: Final = 1024
MAX_PROJECTION_NODES: Final = 2_000
MAX_PAYLOAD_PREVIEW_CHARS: Final = 1024

# json.dumps raises ValueError on huge ints (Python's int<->str digit limit),
# so integers at or beyond this magnitude are reported, never serialized.
INT_LIMIT: Final = 2**63


def project(value: object, depth: int = 0, budget: list[int] | None = None) -> object:
    """
    Bounded, JSON-safe diagnostic projection of untrusted data. Only the exact
    type name of unknown objects is recorded, so no user-defined code runs.
    Tuples become lists; long strings, collections, deep and oversized graphs
    are truncated.

    ``depth`` and ``budget`` are internal recursion state; callers must not
    pass them.
    """
    if budget is None:
        budget = [MAX_PROJECTION_NODES]
    budget[0] -= 1
    if budget[0] < 0:
        return {"truncated": "node_budget"}
    if depth > MAX_PROJECTION_DEPTH:
        return {"truncated": "max_depth"}

    t = type(value)
    if value is None or t is bool:
        return value
    if t is int:
        return value if -INT_LIMIT < cast(int, value) < INT_LIMIT else {"int_out_of_range": True}
    if t is float:
        f = cast(float, value)
        return f if math.isfinite(f) else {"non_finite_float": True}
    if t is str:
        return cast(str, value)[:MAX_PROJECTION_STR]

    if t is list or t is tuple:
        items = list(cast("list[object]", value))
        out_list: list[object] = [
            project(v, depth + 1, budget) for v in items[:MAX_PROJECTION_ITEMS]
        ]
        if len(items) > MAX_PROJECTION_ITEMS:
            out_list.append({"truncated_items": len(items) - MAX_PROJECTION_ITEMS})
        return out_list

    if t is dict:
        entries = list(cast("dict[object, object]", value).items())
        out_dict: dict[str, object] = {}
        for i, (k, v) in enumerate(entries[:MAX_PROJECTION_ITEMS]):
            key = (
                cast(str, k)[:MAX_PROJECTION_STR]
                if type(k) is str
                else f"<non_string_key_{i}:{type(k).__name__}>"
            )
            out_dict[key] = project(v, depth + 1, budget)
        if len(entries) > MAX_PROJECTION_ITEMS:
            out_dict["<truncated_items>"] = len(entries) - MAX_PROJECTION_ITEMS
        return out_dict

    return {"unserializable_type": t.__qualname__}


def snapshot(payload: object) -> tuple[str, bool, str]:
    """
    (preview, truncated, hash) for an untrusted payload.

    ensure_ascii=True makes the canonical text pure ASCII, so hashing cannot
    fail on lone surrogates or other exotic characters. The projection holds
    only bounded ints, so json.dumps cannot hit the int digit limit.
    """
    canonical = json.dumps(
        project(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    digest = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    truncated = len(canonical) > MAX_PAYLOAD_PREVIEW_CHARS
    return canonical[:MAX_PAYLOAD_PREVIEW_CHARS], truncated, digest