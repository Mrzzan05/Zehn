from typing import List

from reality.schemas import Observation, Assertion
from reality.extraction.errors import (
    ExtractionError,
    ExtractionMalformedOutput,
    ExtractionInternalError
)
from reality.extraction.audit import get_audit_sink
from reality.extraction.provider_lifecycle import get_provider
from reality.extraction.normalization import normalize
from reality.extraction.validation import validate
from reality.extraction.contracts import (
    DroppedClaim,
    NormalizationMalformed,
    ValidationSuccess,
    ValidationRejected
)


def extract(observation: Observation) -> List[Assertion]:
    """
    Executes the reality extraction pipeline for a given observation.
    Orchestrates provider invocation, structural normalization, and semantic validation.
    """
    # Step 0: Persistence Precondition (Must happen before ANY other action)
    if observation.id is None:
        raise ValueError("Observation.id must not be None prior to extraction.")

    # All unexpected errors beyond this point are wrapped in ExtractionInternalError (Class 6)
    try:
        # Step 1: Resolve audit sink exactly once
        audit_sink = get_audit_sink()

        # Step 2: Resolve provider exactly once (strictly local reference)
        provider = get_provider()

        # Step 3: Call provider (opaque output)
        # Note: Provider protocol is assumed to expose .extract(). If the frozen protocol 
        # defines __call__ instead, this should be updated to `provider(observation)`.
        raw_output = provider.extract(observation)

        # Step 4: Run normalization
        norm_result = normalize(raw_output)

        if isinstance(norm_result, NormalizationMalformed):
            raise ExtractionMalformedOutput(norm_result.reason)

        # Step 5: Immediately audit normalization drops
        for drop in norm_result.dropped:
            audit_sink.record(drop)

        # Step 6: Validation
        assertions: List[Assertion] = []
        
        for claim in norm_result.claims:
            val_result = validate(claim, observation.id)
            
            if isinstance(val_result, ValidationSuccess):
                assertions.append(val_result.assertion)
            
            elif isinstance(val_result, ValidationRejected):
                # Construct explicit deterministic dictionary projection of the claim boundary.
                # Avoids coupling to Pydantic's serialization mechanisms.
                projection = {
                    "subject_text": claim.subject_text,
                    "object_text": claim.object_text,
                    "predicate": claim.predicate,
                    "type_hints": claim.type_hints
                }
                
                drop = DroppedClaim(
                    stage="validation",
                    reason=val_result.reason,
                    payload_projection=projection
                )
                audit_sink.record(drop)

        # Step 7: Return collected Assertions
        return assertions

    except ExtractionError:
        # Existing Class 1-5 extraction exceptions propagate unchanged
        raise
    
    except Exception as e:
        # Class 6: Wrap unexpected exceptions (KeyError, TypeError, audit failure, etc.)
        raise ExtractionInternalError(
            f"An unexpected internal error occurred during orchestration: {str(e)}"
        ) from e