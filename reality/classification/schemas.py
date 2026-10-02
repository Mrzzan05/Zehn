"""
reality/classification/schemas.py

Semantic Firewall models (RFC-006).

Placed in the classification package on purpose: reality/schemas.py is
frozen and also defines Assertion / Entity / Relationship, which the engine,
repository and extraction layers import.

STRICT MODE AND UNTRUSTED INPUT
    Every model here is strict. Untrusted provider output MUST enter through
    ``model_validate_json`` (the JSON domain), which is what
    reality.classification.normalization does. Do not "fix" a failing payload
    by loosening ``strict``.

DEEP IMMUTABILITY
    ``frozen=True`` only blocks attribute assignment; a ``dict`` or ``list``
    inside a frozen model can still be mutated. Therefore NO model in this
    module (or in contracts.py) may contain dict / list / set fields: use
    tuples of frozen models instead. tests/classification/test_immutability.py
    enforces this structurally.

ClassificationObservation
    Named differently from the frozen extraction ``Observation`` on purpose
    (different fields). If RFC-001 defines the canonical Observation, replace
    this class with an import of that one.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SemanticType = Literal["Fact", "Belief", "Memory", "Goal", "Commitment", "Preference"]

TemporalLabel = Literal["before", "after", "during", "at", "starts", "ends"]


class MetadataEntry(BaseModel):
    """One immutable key/value pair of observation metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    key: str = Field(min_length=1, max_length=64)
    value: str = Field(max_length=256)


class ClassificationObservation(BaseModel):
    """Source reality event from which semantics will be proposed."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    observation_id: str
    raw_content: str
    timestamp: datetime
    # A tuple of entries, not a dict: a dict inside a frozen model is mutable.
    modality_metadata: tuple[MetadataEntry, ...] = Field(default_factory=tuple)

    @field_validator("modality_metadata")
    @classmethod
    def _keys_must_be_unique(
        cls, entries: tuple[MetadataEntry, ...]
    ) -> tuple[MetadataEntry, ...]:
        keys = [e.key for e in entries]
        if len(keys) != len(set(keys)):
            raise ValueError("modality_metadata keys must be unique")
        return entries

    def metadata_as_dict(self) -> dict[str, str]:
        """
        A fresh, detached ``key -> value`` copy. LOSSY convenience view: if
        MetadataEntry ever gains more fields, they are not represented here.
        Mutating the result changes nothing in the observation.
        """
        return {e.key: e.value for e in self.modality_metadata}


class CandidateAttribute(BaseModel):
    """Typed attribute primitive (prevents hidden semantic injection)."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    key: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=256)


class CandidateSubjectDescriptor(BaseModel):
    """Candidate identity attributes proposed by the Classifier."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # ":" is rejected so a classifier cannot smuggle an identity such as
    # "Sara:person_123" through the human-readable label.
    label: str = Field(min_length=1, max_length=128, pattern=r"^[^:]+$")
    attributes: tuple[CandidateAttribute, ...] = Field(default_factory=tuple)


class TemporalMarker(BaseModel):
    """A time reference with a closed relation vocabulary."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    label: TemporalLabel
    # Free text on purpose (not parsed here); length-bounded only.
    value: str = Field(min_length=1, max_length=64)


class DerivationMetadata(BaseModel):
    """Epistemic origin of a proposal. Forbids absolute-truth claims."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    derivation_type: Literal["explicit", "inferred", "hypothesis", "suggested"]
    engine: str
    reasoning_trace_id: str | None = None


class SemanticProposal(BaseModel):
    """An immutable, non-authoritative representation of interpreted meaning."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source_observation_id: str
    semantic_type: SemanticType

    candidate_subject_descriptor: CandidateSubjectDescriptor | None = None

    predicate: str = Field(min_length=1, max_length=128)
    object_text: str | None = None

    temporal_markers: tuple[TemporalMarker, ...] = Field(default_factory=tuple)

    # The Classifier's mechanical certainty, 0.0 to 1.0. It is NOT the
    # Reality Engine's confidence in a fact; the two must never share a field.
    classification_confidence: float = Field(..., ge=0.0, le=1.0)

    derivation_metadata: DerivationMetadata

    @field_validator("classification_confidence", mode="before")
    @classmethod
    def _confidence_must_be_a_real_float(cls, value: object) -> object:
        """
        No numeric widening: ``1``, ``0`` and ``True`` are rejected; the
        provider must send ``1.0`` / ``0.0``.
        """
        if type(value) is not float:
            raise ValueError("classification_confidence must be a float")
        return value
