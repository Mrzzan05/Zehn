"""
reality/classification/pipeline.py
"""

from reality.classification.contracts import ClassificationProvider, ClassificationResult
from reality.classification.exceptions import ClassificationError, ClassificationInternalError
from reality.classification.normalization import Clock, normalize_classification, utc_now
from reality.classification.schemas import ClassificationObservation
from reality.classification.semantic_rules import apply_semantic_rules


def classify_observation(
    observation: ClassificationObservation,
    provider: ClassificationProvider,
    *,
    clock: Clock = utc_now,
) -> ClassificationResult:
    """
    Flow: Observation -> ClassificationProvider -> schema firewall
          (normalize_classification) -> semantic rules -> ClassificationResult

    Failure model (see exceptions.py):
      * bad provider OUTPUT  -> audited drop inside the result, never an exception;
      * provider FAILURE     -> a ClassificationError subclass raised by the
        provider (ProviderUnavailable, ProviderTimeout, ...) propagates
        unchanged; the caller decides about retry / failover / alerting;
      * anything unexpected  -> ClassificationInternalError, chained from the
        original. Its message carries only the exception TYPE, never the
        original message, so provider internals cannot leak through it.

    Provenance is anchored here: the id used to verify every proposal comes
    from the Observation, not from provider output.
    """
    try:
        raw_output = provider.classify(observation)
        result = normalize_classification(
            raw_output, observation.observation_id, clock=clock
        )
        return apply_semantic_rules(result, clock=clock)
    except ClassificationError:
        raise
    except Exception as exc:
        raise ClassificationInternalError(
            f"Unexpected error during classification: {type(exc).__name__}"
        ) from exc
