"""
reality/classification/normalization.py

Semantic Firewall. Rejection-only: accepted proposals are built from the
provider's payload without coercion, sanitization or repair.

Per-candidate flow:
    1. not a dict                     -> NOT_A_DICTIONARY
    2. not strictly JSON-domain       -> NOT_JSON_DOMAIN
    3. schema validation (JSON mode)  -> SCHEMA_VIOLATION
    4. provenance check               -> PROVENANCE_MISMATCH
    5. otherwise                      -> accepted

Resource safety. A provider is untrusted code, so its object graph is too:
  * a node budget bounds EXPANDED traversal. This also stops DAGs that reuse
    the same child many times (a few bytes in memory, 2**60 paths) as well as
    cycles; a depth limit alone does not;
  * integers are range-limited, because json.dumps raises ValueError on huge
    ints (Python's int<->str digit limit), which would crash the whole batch;
  * audit output (preview, error details, error locations) is size-bounded.

The audit snapshot is produced by reality.bounded_snapshot (``project`` +
``snapshot``): separate, total, bounded functions shared with other layers
(RFC-004 R2-D8). They never influence what is accepted.
"""

import json
import math
from datetime import datetime, timezone
from typing import Callable, Iterable, cast

from pydantic import ValidationError

# The four MAX_PROJECTION_* names are re-exported for compatibility: they
# moved to reality.bounded_snapshot and are still importable from here.
from reality.bounded_snapshot import (
    INT_LIMIT,
    MAX_PROJECTION_DEPTH,
    MAX_PROJECTION_ITEMS,
    MAX_PROJECTION_NODES,
    MAX_PROJECTION_STR,
    snapshot,
)
from reality.classification.contracts import (
    MAX_DETAIL_LOC_PARTS,
    MAX_DETAIL_TEXT_CHARS,
    MAX_ERROR_DETAILS,
    REASON_CODE_TO_ERROR_TYPE,
    ClassificationReasonCode,
    ClassificationResult,
    DroppedProposal,
    ErrorDetail,
)
from reality.classification.schemas import SemanticProposal

__all__ = [
    "normalize_classification",
    "create_drop",
    "utc_now",
    "Clock",
    "MAX_PROJECTION_DEPTH",
    "MAX_PROJECTION_ITEMS",
    "MAX_PROJECTION_STR",
    "MAX_PROJECTION_NODES",
    "MAX_DOMAIN_NODES",
]

MAX_DOMAIN_NODES = 100_000
_MAX_DOMAIN_DEPTH = 64

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# JSON-domain gate
# ---------------------------------------------------------------------------

def _is_json_domain(value: object) -> bool:
    """
    True only for values that survive ``json.dumps`` without loss or guessing:
    exact ``dict`` (str keys), ``list``/``tuple``, ``str``, ``bool``, ``int``
    (|n| < 2**63), finite ``float`` and ``None``. Exact types are used on
    purpose: subclasses (and numpy scalars) can override behavior.
    """
    return _walk_domain(value, 0, [MAX_DOMAIN_NODES])


def _walk_domain(value: object, depth: int, budget: list[int]) -> bool:
    budget[0] -= 1
    if budget[0] < 0 or depth > _MAX_DOMAIN_DEPTH:
        return False

    t = type(value)
    if value is None or t is str or t is bool:
        return True
    if t is int:
        return -INT_LIMIT < cast(int, value) < INT_LIMIT
    if t is float:
        return math.isfinite(cast(float, value))
    if t is list or t is tuple:
        return all(
            _walk_domain(v, depth + 1, budget) for v in cast("list[object]", value)
        )
    if t is dict:
        return all(
            type(k) is str and _walk_domain(v, depth + 1, budget)
            for k, v in cast("dict[object, object]", value).items()
        )
    return False


# ---------------------------------------------------------------------------
# Drop construction
# ---------------------------------------------------------------------------

def create_drop(
    payload: object,
    reason_code: ClassificationReasonCode,
    clock: Clock,
    details: tuple[ErrorDetail, ...] = (),
    details_omitted: int = 0,
) -> DroppedProposal:
    preview, truncated, digest = snapshot(payload)
    return DroppedProposal(
        payload_preview=preview,
        payload_truncated=truncated,
        projection_hash=digest,
        error_type=REASON_CODE_TO_ERROR_TYPE[reason_code],
        reason_code=reason_code,
        details=details,
        details_omitted=details_omitted,
        created_at=clock(),
    )


def _bound_loc(loc: tuple[str | int, ...]) -> tuple[str | int, ...]:
    # An error location can contain attacker-controlled text (the offending key).
    return tuple(
        part[:MAX_DETAIL_TEXT_CHARS] if isinstance(part, str) else part
        for part in tuple(loc)[:MAX_DETAIL_LOC_PARTS]
    )


def _details_from_validation_error(
    error: ValidationError,
) -> tuple[tuple[ErrorDetail, ...], int]:
    """
    Bounded, payload-free view of a ValidationError: (details, omitted_count).
    Only type / loc / msg are kept; Pydantic's `input` and `ctx` would
    re-embed the rejected payload, and a hostile payload can produce
    thousands of errors, so only the first MAX_ERROR_DETAILS are kept.
    """
    errors = error.errors()
    kept = errors[:MAX_ERROR_DETAILS]
    details = tuple(
        ErrorDetail(
            type=str(e["type"])[:MAX_DETAIL_TEXT_CHARS],
            loc=_bound_loc(tuple(e["loc"])),
            msg=str(e["msg"])[:MAX_DETAIL_TEXT_CHARS],
        )
        for e in kept
    )
    return details, len(errors) - len(kept)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_classification(
    raw_output: object,
    observation_id: str,
    *,
    clock: Clock = utc_now,
) -> ClassificationResult:
    """
    Safely extracts proposals from untrusted provider output.

    Args:
        raw_output: whatever the provider returned (untrusted).
        observation_id: id of the Observation that was classified. A proposal
            whose ``source_observation_id`` differs is rejected: provenance is
            established by the caller, never by the provider.
        clock: injected time source (keeps results reproducible in tests).
    """
    accepted: list[SemanticProposal] = []
    dropped: list[DroppedProposal] = []

    candidates: Iterable[object] = ()

    if raw_output is None:
        dropped.append(create_drop(None, "NULL_OUTPUT", clock))
    elif isinstance(raw_output, list):
        candidates = raw_output
    else:
        # Same contract as reality.extraction.normalization: the root MUST be
        # a list. A bare dict or a tuple is a malformed container, not a
        # single candidate. (Difference kept on purpose: extraction raises
        # for a malformed root; here it is an audited drop in the result.)
        dropped.append(create_drop(raw_output, "INVALID_ROOT_TYPE", clock))

    for candidate in candidates:
        if not isinstance(candidate, dict):
            dropped.append(create_drop(candidate, "NOT_A_DICTIONARY", clock))
            continue

        if not _is_json_domain(candidate):
            dropped.append(create_drop(candidate, "NOT_JSON_DOMAIN", clock))
            continue

        try:
            # JSON domain: strict models accept nested objects and arrays here
            # but still reject every type coercion. The gate above bounds the
            # expanded size and int range, so json.dumps cannot blow up.
            proposal = SemanticProposal.model_validate_json(
                json.dumps(candidate, allow_nan=False)
            )
        except ValidationError as e:
            details, omitted = _details_from_validation_error(e)
            dropped.append(
                create_drop(
                    candidate,
                    "SCHEMA_VIOLATION",
                    clock,
                    details=details,
                    details_omitted=omitted,
                )
            )
            continue

        if proposal.source_observation_id != observation_id:
            dropped.append(
                create_drop(
                    candidate,
                    "PROVENANCE_MISMATCH",
                    clock,
                    details=(
                        ErrorDetail(
                            type="provenance_mismatch",
                            loc=("source_observation_id",),
                            msg="source_observation_id does not match the "
                            "classified observation",
                        ),
                    ),
                )
            )
            continue

        accepted.append(proposal)

    return ClassificationResult(accepted=tuple(accepted), dropped=tuple(dropped))