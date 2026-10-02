import json
from typing import Any

import pytest
from pydantic import ValidationError

from reality.classification.schemas import (
    CandidateAttribute,
    CandidateSubjectDescriptor,
    DerivationMetadata,
    SemanticProposal,
    TemporalMarker,
)


def error_types(exc: ValidationError) -> set[str]:
    return {e["type"] for e in exc.errors()}


@pytest.fixture
def valid_derivation() -> DerivationMetadata:
    return DerivationMetadata(derivation_type="explicit", engine="classifier_v1")


@pytest.fixture
def valid_descriptor() -> CandidateSubjectDescriptor:
    return CandidateSubjectDescriptor(
        label="Sara",
        attributes=(CandidateAttribute(key="role", value="coworker"),),
    )


@pytest.fixture
def valid_proposal(
    valid_derivation: DerivationMetadata,
    valid_descriptor: CandidateSubjectDescriptor,
) -> SemanticProposal:
    return SemanticProposal(
        source_observation_id="obs_123",
        semantic_type="Fact",
        candidate_subject_descriptor=valid_descriptor,
        predicate="likes",
        object_text="cats",
        classification_confidence=0.85,
        derivation_metadata=valid_derivation,
    )


def as_json_payload(proposal: SemanticProposal) -> dict[str, Any]:
    """Untrusted-payload form: plain dicts/lists, as a provider would send."""
    return json.loads(proposal.model_dump_json())


class TestSemanticFirewallBoundaries:
    def test_semantic_proposal_is_strictly_immutable(self, valid_proposal: SemanticProposal):
        with pytest.raises(ValidationError) as exc:
            valid_proposal.predicate = "hates"  # type: ignore[misc]
        assert "frozen_instance" in error_types(exc.value)

    def test_control_round_trip_payload_is_valid(self, valid_proposal: SemanticProposal):
        """Control: the payload used by the leak tests is valid without the leak."""
        parsed = SemanticProposal.model_validate_json(
            json.dumps(as_json_payload(valid_proposal))
        )
        assert parsed == valid_proposal

    def test_root_level_authority_leak_forbidden(self, valid_proposal: SemanticProposal):
        data = as_json_payload(valid_proposal)
        data["entity_uuid"] = "uuid-999"

        with pytest.raises(ValidationError) as exc:
            SemanticProposal.model_validate_json(json.dumps(data))
        assert error_types(exc.value) == {"extra_forbidden"}

    def test_nested_authority_leak_in_descriptor_forbidden(self):
        with pytest.raises(ValidationError) as exc:
            CandidateSubjectDescriptor.model_validate_json(
                json.dumps({"label": "Sara", "entity_uuid": "uuid-999"})
            )
        assert error_types(exc.value) == {"extra_forbidden"}

    def test_attribute_payload_cannot_carry_structural_authority(self):
        with pytest.raises(ValidationError) as exc:
            CandidateAttribute.model_validate_json(
                json.dumps({"key": "metadata", "value": {"entity_uuid": "uuid-999"}})
            )
        assert error_types(exc.value) == {"string_type"}

    def test_semantic_type_strictly_bounded(self, valid_proposal: SemanticProposal):
        data = as_json_payload(valid_proposal)
        data["semantic_type"] = "RealityFactConfirmedForever"

        with pytest.raises(ValidationError) as exc:
            SemanticProposal.model_validate_json(json.dumps(data))
        assert error_types(exc.value) == {"literal_error"}

    def test_derivation_metadata_strictly_bounded(self):
        with pytest.raises(ValidationError) as exc:
            DerivationMetadata.model_validate_json(
                json.dumps({"derivation_type": "absolute_truth", "engine": "classifier_v1"})
            )
        assert error_types(exc.value) == {"literal_error"}

    @pytest.mark.parametrize("bad", [1.5, -0.1])
    def test_confidence_out_of_range_rejected(
        self, valid_proposal: SemanticProposal, bad: float
    ):
        data = as_json_payload(valid_proposal)
        data["classification_confidence"] = bad

        with pytest.raises(ValidationError):
            SemanticProposal.model_validate_json(json.dumps(data))

    @pytest.mark.parametrize("edge", [0.0, 1.0])
    def test_confidence_bounds_are_inclusive(
        self, valid_proposal: SemanticProposal, edge: float
    ):
        data = as_json_payload(valid_proposal)
        data["classification_confidence"] = edge

        parsed = SemanticProposal.model_validate_json(json.dumps(data))
        assert parsed.classification_confidence == edge

    @pytest.mark.parametrize("not_a_float", [1, 0, True, "0.8"])
    def test_confidence_must_be_a_float_no_numeric_widening(
        self, valid_proposal: SemanticProposal, not_a_float: object
    ):
        """Decision: int / bool / str are rejected, not coerced to float."""
        data = as_json_payload(valid_proposal)
        data["classification_confidence"] = not_a_float

        with pytest.raises(ValidationError) as exc:
            SemanticProposal.model_validate_json(json.dumps(data))
        assert all(
            e["loc"] == ("classification_confidence",) for e in exc.value.errors()
        )


class TestDescriptorAndTemporalMarkers:
    def test_identity_cannot_be_smuggled_through_the_label(self):
        with pytest.raises(ValidationError) as exc:
            CandidateSubjectDescriptor.model_validate_json(
                json.dumps({"label": "Sara:person_123"})
            )
        assert error_types(exc.value) == {"string_pattern_mismatch"}

    def test_plain_label_is_accepted(self):
        parsed = CandidateSubjectDescriptor.model_validate_json(
            json.dumps({"label": "Sara"})
        )
        assert parsed.label == "Sara"

    @pytest.mark.parametrize(
        "label", ["before", "after", "during", "at", "starts", "ends"]
    )
    def test_every_allowed_temporal_label_is_accepted(self, label: str):
        marker = TemporalMarker.model_validate_json(
            json.dumps({"label": label, "value": "2026-01-01"})
        )
        assert marker.label == label

    def test_temporal_label_is_a_closed_vocabulary(self):
        with pytest.raises(ValidationError) as exc:
            TemporalMarker.model_validate_json(
                json.dumps({"label": "sometime", "value": "x"})
            )
        assert error_types(exc.value) == {"literal_error"}

    def test_temporal_value_is_length_bounded(self):
        with pytest.raises(ValidationError):
            TemporalMarker.model_validate_json(
                json.dumps({"label": "at", "value": "x" * 65})
            )

    def test_proposal_accepts_typed_temporal_markers(self, valid_proposal: SemanticProposal):
        data = as_json_payload(valid_proposal)
        data["temporal_markers"] = [{"label": "after", "value": "2026-01-01"}]

        parsed = SemanticProposal.model_validate_json(json.dumps(data))

        assert parsed.temporal_markers == (TemporalMarker(label="after", value="2026-01-01"),)
