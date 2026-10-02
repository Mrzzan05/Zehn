"""
reality/classification/adapters.py

The ONLY place that knows how the canonical (frozen) Observation maps to the
provider-facing ClassificationObservation.

Why a separate, narrower model exists at all: a classification provider is
untrusted and should receive the minimum it needs (an id, the text, a
timestamp), not the full canonical Observation. The canonical Observation
stays the single source of truth; ClassificationObservation is a derived,
read-only projection of it and is never persisted.
"""

from reality.classification.schemas import ClassificationObservation
from reality.schemas import Observation


def to_classification_observation(observation: Observation) -> ClassificationObservation:
    """
    Project a canonical Observation for a classification provider.

    Provenance rule: the id handed to the provider, and later used to verify
    every proposal, is ``str(observation.id)``. The Observation must already
    be persisted (same precondition as extraction.pipeline.extract).
    """
    if observation.id is None:
        raise ValueError("Observation.id must not be None prior to classification.")

    return ClassificationObservation(
        observation_id=str(observation.id),
        raw_content=observation.raw_text,
        timestamp=observation.created_at,
        modality_metadata=(),
    )
