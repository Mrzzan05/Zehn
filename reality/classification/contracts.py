"""
reality/classification/contracts.py

Boundary types of the Semantic Firewall.

Deep immutability rule: no dict / list / set fields in this module (see
schemas.py). Rejected payloads are therefore stored as a bounded canonical-JSON
string plus a hash, never as a live container.
"""

from datetime import datetime
from typing import Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from reality.bounded_snapshot import MAX_PAYLOAD_PREVIEW_CHARS
from reality.classification.schemas import ClassificationObservation, SemanticProposal

ClassificationErrorType = Literal[
    "MalformedContainer",
    "InvalidPayloadType",
    "FirewallRejection",
    "SemanticRejection",
]

# Closed vocabulary. Adding a code is a contract change: extend this Literal
# AND REASON_CODE_TO_ERROR_TYPE (a test enforces that they stay in sync).
ClassificationReasonCode = Literal[
    "NULL_OUTPUT",
    "INVALID_ROOT_TYPE",
    "NOT_A_DICTIONARY",
    "NOT_JSON_DOMAIN",
    "SCHEMA_VIOLATION",
    "PROVENANCE_MISMATCH",
    "SEMANTIC_RULE_VIOLATION",
]

# error_type is derived from reason_code, so there is a single taxonomy.
REASON_CODE_TO_ERROR_TYPE: Final[dict[str, ClassificationErrorType]] = {
    "NULL_OUTPUT": "MalformedContainer",
    "INVALID_ROOT_TYPE": "MalformedContainer",
    "NOT_A_DICTIONARY": "InvalidPayloadType",
    "NOT_JSON_DOMAIN": "InvalidPayloadType",
    "SCHEMA_VIOLATION": "FirewallRejection",
    "PROVENANCE_MISMATCH": "FirewallRejection",
    "SEMANTIC_RULE_VIOLATION": "SemanticRejection",
}


# Audit-size bounds: a hostile payload can trigger thousands of schema errors
# and put megabytes into an error location (the offending key itself).
MAX_ERROR_DETAILS: Final = 32
MAX_DETAIL_LOC_PARTS: Final = 16
MAX_DETAIL_TEXT_CHARS: Final = 256


class ClassificationProvider(Protocol):
    """
    Protocol strictly for classification providers.

    The return type is ``object`` (not ``Any``): provider output is
    untrusted, and ``object`` forces callers to narrow before use.

    A provider returns a value (however wrong) or raises a ProviderError
    (see exceptions.py). It must never turn a failure into an empty result.
    """

    def classify(self, observation: ClassificationObservation) -> object: ...


class ErrorDetail(BaseModel):
    """
    One machine-readable schema failure.

    Deliberately excludes Pydantic's ``input`` and ``ctx`` entries: they
    re-embed the rejected payload and may hold non-JSON objects.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    type: str = Field(max_length=MAX_DETAIL_TEXT_CHARS)
    loc: tuple[str | int, ...] = Field(max_length=MAX_DETAIL_LOC_PARTS)
    msg: str = Field(max_length=MAX_DETAIL_TEXT_CHARS)

    @field_validator("loc")
    @classmethod
    def _loc_parts_must_be_short(cls, loc: tuple[str | int, ...]) -> tuple[str | int, ...]:
        for part in loc:
            if isinstance(part, str) and len(part) > MAX_DETAIL_TEXT_CHARS:
                raise ValueError("loc part too long")
        return loc


class DroppedProposal(BaseModel):
    """
    Machine-readable record of a payload rejected by the Semantic Firewall.

    The rejected payload is NOT retained. The audit trail keeps:
      * payload_preview    - canonical JSON of a bounded projection, cut at
                            MAX_PAYLOAD_PREVIEW_CHARS (human debugging);
      * payload_truncated  - whether the preview was cut;
      * projection_hash      - SHA-256 of the full bounded projection
                            (correlating identical rejects). Equal hashes mean
                            equal projections, not necessarily equal raw input.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    payload_preview: str = Field(max_length=MAX_PAYLOAD_PREVIEW_CHARS)
    payload_truncated: bool
    projection_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    error_type: ClassificationErrorType
    reason_code: ClassificationReasonCode
    # At most MAX_ERROR_DETAILS entries are kept; the rest are only counted.
    details: tuple[ErrorDetail, ...] = Field(max_length=MAX_ERROR_DETAILS)
    details_omitted: int = Field(default=0, ge=0)
    created_at: datetime

    @model_validator(mode="after")
    def _error_type_must_match_reason_code(self) -> "DroppedProposal":
        expected = REASON_CODE_TO_ERROR_TYPE[self.reason_code]
        if self.error_type != expected:
            raise ValueError(
                f"error_type {self.error_type!r} does not match "
                f"reason_code {self.reason_code!r} (expected {expected!r})"
            )
        return self


class ClassificationResult(BaseModel):
    """Immutable result of the classification pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    accepted: tuple[SemanticProposal, ...]
    dropped: tuple[DroppedProposal, ...]
