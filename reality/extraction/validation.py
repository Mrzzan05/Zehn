from pydantic import ValidationError

from reality.extraction.contracts import (
    NormalizedClaim,
    ValidationSuccess,
    ValidationRejected,
    ValidationResult
)
from reality.schemas import Assertion

# NormalizedClaim carries no assertion-type signal, and validation must not
# infer one. Every validated claim is therefore tagged with this neutral
# value; classifying it as "attribute" or "relationship" is a later,
# semantic decision that does not belong in this layer.
UNCLASSIFIED_ASSERTION_TYPE = "unclassified"


def validate(claim: NormalizedClaim, observation_id: int) -> ValidationResult:
    """
    Validates a NormalizedClaim semantically by constructing an Assertion.
    
    Delegates all structural/type coercion (e.g., whitespace stripping) to the 
    frozen Assertion schema. MUST NOT infer missing entities, resolve identity, 
    merge, or repair semantic content.
    """
    try:
        # Direct 1:1 mapping. 
        # No orchestration-level repair or inference is performed.
        # Explicit None handling is used to strictly avoid truthiness semantics.
        assertion = Assertion(
            observation_id=observation_id,
            assertion_type=UNCLASSIFIED_ASSERTION_TYPE,
            subject=claim.subject_text,
            predicate=claim.predicate,
            object=claim.object_text,
            metadata=claim.type_hints if claim.type_hints is not None else {}
        )
        return ValidationSuccess(assertion=assertion)
        
    except ValidationError as e:
        # Class 5 Semantic Failure: The claim reached Validation intact (Class 4 passed),
        # but lacks semantically required fields (e.g., subject is None) or violates 
        # the frozen Assertion rules.
        return ValidationRejected(
            reason=f"Semantic validation failed: {e.error_count()} schema violation(s)."
        )