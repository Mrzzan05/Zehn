"""
Deep-immutability guard for the classification models.

`frozen=True` only blocks attribute assignment. A dict / list / set held in a
frozen model can still be mutated in place, so none may appear in any field
annotation of the classification models.
"""

import inspect
import typing
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, ValidationError

from reality.classification import contracts, schemas
from reality.classification.schemas import (
    CandidateAttribute,
    CandidateSubjectDescriptor,
    ClassificationObservation,
    DerivationMetadata,
    MetadataEntry,
    SemanticProposal,
    TemporalMarker,
)

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)
MUTABLE_CONTAINERS = (dict, list, set, bytearray)


def contains_mutable_container(annotation: object) -> bool:
    if annotation in MUTABLE_CONTAINERS:
        return True
    if typing.get_origin(annotation) in MUTABLE_CONTAINERS:
        return True
    return any(contains_mutable_container(arg) for arg in typing.get_args(annotation))


def models_defined_in(module) -> list[type[BaseModel]]:
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if issubclass(cls, BaseModel)
        and cls is not BaseModel
        and cls.__module__ == module.__name__
    ]


ALL_MODELS = models_defined_in(schemas) + models_defined_in(contracts)


def test_the_guard_actually_finds_the_models():
    names = {m.__name__ for m in ALL_MODELS}
    assert {
        "SemanticProposal",
        "ClassificationObservation",
        "DroppedProposal",
        "ClassificationResult",
        "TemporalMarker",
    } <= names


def test_the_guard_detects_mutable_containers():
    assert contains_mutable_container(dict[str, str])
    assert contains_mutable_container(tuple[list[int], ...])
    assert contains_mutable_container(dict[str, str] | None)
    assert not contains_mutable_container(tuple[str, ...])
    assert not contains_mutable_container(tuple[str | int, ...])


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_no_model_field_holds_a_mutable_container(model: type[BaseModel]):
    offenders = [
        name
        for name, field in model.model_fields.items()
        if contains_mutable_container(field.annotation)
    ]
    assert offenders == [], f"{model.__name__} has mutable fields: {offenders}"


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_every_model_is_frozen_strict_and_forbids_extras(model: type[BaseModel]):
    config = model.model_config
    assert config.get("frozen") is True
    assert config.get("strict") is True
    assert config.get("extra") == "forbid"


@pytest.fixture
def observation() -> ClassificationObservation:
    return ClassificationObservation(
        observation_id="obs_123",
        raw_content="text",
        timestamp=FIXED,
        modality_metadata=(
            MetadataEntry(key="channel", value="voice"),
            MetadataEntry(key="lang", value="fa"),
        ),
    )


class TestObservationMetadata:
    def test_metadata_is_a_tuple_of_frozen_entries(self, observation):
        assert isinstance(observation.modality_metadata, tuple)
        with pytest.raises(ValidationError):
            observation.modality_metadata[0].value = "evil"  # type: ignore[misc]

    def test_metadata_cannot_be_mutated_in_place(self, observation):
        with pytest.raises(TypeError):
            observation.modality_metadata[0] = MetadataEntry(key="x", value="y")  # type: ignore[index]

    def test_metadata_attribute_cannot_be_reassigned(self, observation):
        with pytest.raises(ValidationError):
            observation.modality_metadata = ()  # type: ignore[misc]

    def test_as_dict_returns_a_detached_copy(self, observation):
        copy_ = observation.metadata_as_dict()
        copy_["channel"] = "evil"

        assert copy_ is not observation.metadata_as_dict()
        assert observation.metadata_as_dict()["channel"] == "voice"
        assert observation.modality_metadata[0].value == "voice"

    def test_duplicate_keys_are_rejected(self):
        with pytest.raises(ValidationError):
            ClassificationObservation(
                observation_id="obs_123",
                raw_content="text",
                timestamp=FIXED,
                modality_metadata=(
                    MetadataEntry(key="a", value="1"),
                    MetadataEntry(key="a", value="2"),
                ),
            )

    def test_metadata_defaults_to_empty_tuple(self):
        obs = ClassificationObservation(
            observation_id="obs_123", raw_content="t", timestamp=FIXED
        )
        assert obs.modality_metadata == ()


class TestProposalIsDeeplyImmutable:
    @pytest.fixture
    def proposal(self) -> SemanticProposal:
        return SemanticProposal(
            source_observation_id="obs_123",
            semantic_type="Fact",
            candidate_subject_descriptor=CandidateSubjectDescriptor(
                label="Sara",
                attributes=(CandidateAttribute(key="role", value="coworker"),),
            ),
            predicate="likes",
            object_text="cats",
            temporal_markers=(TemporalMarker(label="at", value="2026-01-01"),),
            classification_confidence=0.85,
            derivation_metadata=DerivationMetadata(
                derivation_type="explicit", engine="classifier_v1"
            ),
        )

    def test_nested_model_cannot_be_assigned(self, proposal):
        with pytest.raises(ValidationError):
            proposal.derivation_metadata.engine = "evil"  # type: ignore[misc]

    def test_descriptor_cannot_be_assigned(self, proposal):
        assert proposal.candidate_subject_descriptor is not None
        with pytest.raises(ValidationError):
            proposal.candidate_subject_descriptor.label = "evil"  # type: ignore[misc]

    def test_tuples_cannot_be_mutated(self, proposal):
        assert proposal.candidate_subject_descriptor is not None
        with pytest.raises(TypeError):
            proposal.temporal_markers[0] = TemporalMarker(label="before", value="now")  # type: ignore[index]
        with pytest.raises(TypeError):
            proposal.candidate_subject_descriptor.attributes[0] = CandidateAttribute(  # type: ignore[index]
                key="x", value="y"
            )

    def test_tuple_items_are_frozen_models(self, proposal):
        with pytest.raises(ValidationError):
            proposal.temporal_markers[0].value = "evil"  # type: ignore[misc]
