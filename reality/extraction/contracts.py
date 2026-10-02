from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from reality.schemas import Assertion


# Recursive type definition for JSON-compatible projection.
#
# PEP 695 named type alias (Python 3.12+): the `type` statement evaluates
# its right-hand side lazily, in its own deferred scope, so JsonValue can
# reference itself directly (list[JsonValue], dict[str, JsonValue]) without
# quoted forward references. This is what fixes the RecursionError under
# Pydantic 2.13: Pydantic recognizes PEP 695 TypeAliasType objects natively
# and resolves the self-reference once via that deferred scope, instead of
# repeatedly re-walking quoted 'JsonValue' ForwardRefs inside a plain
# Union[...] alias, which is what caused unbounded recursion.
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


class NormalizedClaim(BaseModel):
    """
    Class 4 -> Class 5 Transport Boundary.

    All fields are nullable to permit transport of incomplete claims.
    Validation is responsible for semantic enforcement.
    """
    model_config = ConfigDict(extra="forbid")

    subject_text: Optional[str] = None
    object_text: Optional[str] = None
    predicate: Optional[str] = None
    # Declared by the provider (RFC-004 section 9, A1). Transport only: no
    # vocabulary, presence or consistency check happens at this boundary;
    # that is validation's job. Nullable like every other field here.
    assertion_type: Optional[str] = None
    subject_type: Optional[str] = None
    object_type: Optional[str] = None
    
    # Field itself may be None.
    # Internal keys and values must remain strings.
    type_hints: Optional[Dict[str, str]] = None


class DroppedClaim(BaseModel):
    """
    Audit record for claims dropped during normalization or validation.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    stage: Literal["normalization", "validation"]

    reason: str = Field(
        ...,
        pattern=r"\S",
        description="Must contain non-whitespace characters"
    )

    # Deterministic JSON-compatible projection.
    # MUST NOT contain raw provider objects.
    payload_projection: Dict[str, JsonValue]


class NormalizationSuccess(BaseModel):
    """
    Result for successfully completing structural normalization.

    Contains valid NormalizedClaim objects and structural drops.
    """

    model_config = ConfigDict(extra="forbid")

    claims: List[NormalizedClaim]
    dropped: List[DroppedClaim]


class NormalizationMalformed(BaseModel):
    """
    Class 3 failure.

    Provider output cannot structurally be interpreted as a fragment batch.
    """

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        ...,
        pattern=r"\S",
        description="Must contain non-whitespace characters"
    )


NormalizationResult = Union[
    NormalizationSuccess,
    NormalizationMalformed
]


class ValidationRejected(BaseModel):
    """
    Class 5 failure.

    NormalizedClaim cannot become a valid Assertion.
    """

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        ...,
        pattern=r"\S",
        description="Must contain non-whitespace characters"
    )


class ValidationSuccess(BaseModel):
    """
    Successful semantic validation result.
    """

    model_config = ConfigDict(extra="forbid")

    assertion: Assertion


ValidationResult = Union[
    ValidationSuccess,
    ValidationRejected
]