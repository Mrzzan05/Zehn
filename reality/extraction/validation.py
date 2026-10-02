"""
reality/extraction/validation.py

Semantic admission of a NormalizedClaim into an Assertion (RFC-004 section 9).

Validation TRANSCRIBES what the provider declared and either admits or
rejects it. It never infers the structural kind, never defaults a missing
declaration, never repairs a malformed one and never reads behavior from
free-form hints (type_hints stay inert annotation).

Declaration rules come from reality.vocabulary, the same source the Engine
enforces, so the two layers cannot drift apart. Rejection reasons name
fields and rules only, never provider content, so audit records cannot
re-embed what the provider sent.
"""

from pydantic import ValidationError

from reality.extraction.contracts import (
    NormalizedClaim,
    ValidationRejected,
    ValidationResult,
    ValidationSuccess,
)
from reality.schemas import Assertion
from reality.vocabulary import (
    OBJECT_TYPE_FIELD,
    SUBJECT_TYPE_FIELD,
    SUPPORTED_ASSERTION_TYPES,
    TYPE_FIELD_RULES,
)

_REASON_PREFIX = "Semantic validation failed"


def _reject(detail: str) -> ValidationRejected:
    return ValidationRejected(reason=f"{_REASON_PREFIX}: {detail}")


def validate(claim: NormalizedClaim, observation_id: int) -> ValidationResult:
    """
    Admit a claim as an Assertion, or reject it. Checks run in a fixed order,
    the same order the Engine uses at its own boundary: kind declared and
    supported, required type fields declared, forbidden type fields absent,
    then the Assertion schema itself (non-blank subject, predicate, object).
    """
    kind = claim.assertion_type
    if kind is None:
        return _reject("assertion_type is not declared.")
    if kind not in SUPPORTED_ASSERTION_TYPES:
        return _reject("assertion_type is not in the supported vocabulary.")

    rule = TYPE_FIELD_RULES[kind]
    declared = {
        name
        for name in (SUBJECT_TYPE_FIELD, OBJECT_TYPE_FIELD)
        if getattr(claim, name) is not None
    }

    missing = rule.required - declared
    if missing:
        return _reject(f"missing required type field(s): {', '.join(sorted(missing))}.")

    contradictory = rule.forbidden & declared
    if contradictory:
        return _reject(
            f"contradictory type field(s) for this assertion_type: "
            f"{', '.join(sorted(contradictory))}."
        )

    try:
        # Direct 1:1 transcription. Explicit None handling, no truthiness.
        assertion = Assertion(
            observation_id=observation_id,
            assertion_type=kind,
            subject=claim.subject_text,
            subject_type=claim.subject_type,
            predicate=claim.predicate,
            object=claim.object_text,
            object_type=claim.object_type,
            metadata=claim.type_hints if claim.type_hints is not None else {},
        )
        return ValidationSuccess(assertion=assertion)

    except ValidationError as e:
        # The claim passed the declaration rules but violates the Assertion
        # schema (missing or blank subject, predicate, object or type).
        return _reject(f"{e.error_count()} schema violation(s).")