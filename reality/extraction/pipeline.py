from typing import List

from reality.extraction.audit import AuditSink
from reality.extraction.contracts import (
    DroppedClaim,
    NormalizationMalformed,
    ValidationRejected,
    ValidationSuccess,
)
from reality.extraction.errors import (
    ExtractionError,
    ExtractionInternalError,
    ExtractionMalformedOutput,
)
from reality.extraction.normalization import normalize
from reality.extraction.provider import Provider
from reality.extraction.validation import validate
from reality.provider_errors import ProviderError
from reality.schemas import Assertion, Observation


def _stamped(drop: DroppedClaim, observation_id: int) -> DroppedClaim:
    """
    Return a COPY of ``drop`` carrying the authoritative Observation id
    (RFC-004 R2-D1). The original is never mutated, and any id it already
    holds is overwritten: provenance is anchored here by the caller, never
    taken from the drop or from provider data. The copy is shallow on purpose,
    so a large hostile projection is not duplicated.
    """
    return drop.model_copy(update={"observation_id": observation_id})

def extract(
    observation: Observation,
    *,
    provider: Provider,
    audit_sink: AuditSink,
) -> List[Assertion]:
    """
    Executes the reality extraction pipeline for a given observation.
    Orchestrates provider invocation, structural normalization, and semantic
    validation.

    The provider and the audit sink are injected explicitly and are required
    (RFC-004 A8, R1-D4): nothing is resolved from module-level state, and a
    sink is never defaulted, so an unaudited run can only happen when a
    caller deliberately passes NullAuditSink. Both are keyword-only because
    they are structurally similar protocols that could be swapped silently.

    Every drop is delivered to the audit sink as a COPY stamped with
    ``observation.id`` (RFC-004 R2-D1). ``normalize()`` and ``validate()``
    stay unaware of the Observation; this function is the provenance
    authority, and an id already present on a drop is overwritten.
    """
    # Step 0: Preconditions (must happen before ANY other action)
    if observation.id is None:
        raise ValueError("Observation.id must not be None prior to extraction.")
    if provider is None:
        raise ValueError("provider must be injected explicitly (got None).")
    if audit_sink is None:
        raise ValueError("audit_sink must be injected explicitly (got None).")

    # All unexpected errors beyond this point are wrapped in ExtractionInternalError (Class 6)
    try:
        # Step 1: Call provider (opaque output)
        raw_output = provider.extract(observation)

        # Step 2: Run normalization
        norm_result = normalize(raw_output)

        if isinstance(norm_result, NormalizationMalformed):
            raise ExtractionMalformedOutput(norm_result.reason)

        # Step 3: Immediately audit normalization drops
        for drop in norm_result.dropped:
            audit_sink.record(_stamped(drop, observation.id))

        # Step 4: Validation
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
                    "type_hints": claim.type_hints,
                    # Declared by the provider, copied verbatim (RFC-004 R2-D3).
                    # None when the claim did not declare the field.
                    "assertion_type": claim.assertion_type,
                    "subject_type": claim.subject_type,
                    "object_type": claim.object_type,
                }

                drop = DroppedClaim(
                    stage="validation",
                    reason=val_result.reason,
                    payload_projection=projection,
                )
                audit_sink.record(_stamped(drop, observation.id))

        # Step 5: Return collected Assertions
        return assertions

    except ExtractionError:
        # Existing Class 1-5 extraction exceptions propagate unchanged
        raise

    except ProviderError:
        # Declared provider failures (unavailable, timeout, invalid response)
        # propagate unchanged so the caller can distinguish "the provider is
        # down or slow" from "the pipeline has a bug" (RFC-004 section 13,
        # A7, A10). Never converted into an empty result (I-25). Only the
        # declared family is exempt: any other exception is still wrapped.
        raise

    except Exception as e:
        # Class 6: Wrap unexpected exceptions (KeyError, TypeError, audit failure, etc.)
        raise ExtractionInternalError(
            f"An unexpected internal error occurred during orchestration: {str(e)}"
        ) from e