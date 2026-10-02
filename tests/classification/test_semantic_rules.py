import json
from datetime import datetime, timezone
from typing import Any

import pytest

from reality.classification.contracts import ClassificationResult
from reality.classification.schemas import (
    CandidateAttribute,
    CandidateSubjectDescriptor,
    DerivationMetadata,
    SemanticProposal,
    TemporalMarker,
)
from reality.classification.semantic_rules import apply_semantic_rules, check_proposal

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def clock() -> datetime:
    return FIXED


def make(**overrides: Any) -> SemanticProposal:
    fields: dict[str, Any] = dict(
        source_observation_id="obs_123",
        semantic_type="Fact",
        predicate="likes",
        object_text="cats",
        classification_confidence=0.9,
        derivation_metadata=DerivationMetadata(derivation_type="explicit", engine="e"),
    )
    fields.update(overrides)
    return SemanticProposal(**fields)


def rule_ids(proposal: SemanticProposal) -> list[str]:
    return [v.type for v in check_proposal(proposal)]


class TestObjectText:
    def test_fact_may_omit_the_object(self):
        assert rule_ids(make(semantic_type="Fact", object_text=None)) == []

    @pytest.mark.parametrize("semantic_type", ["Goal", "Preference"])
    def test_goal_and_preference_require_an_object(self, semantic_type):
        assert rule_ids(make(semantic_type=semantic_type, object_text=None)) == [
            "rule.object_required"
        ]

    @pytest.mark.parametrize("semantic_type", ["Goal", "Preference"])
    def test_goal_and_preference_pass_with_an_object(self, semantic_type):
        assert rule_ids(make(semantic_type=semantic_type, object_text="run a marathon")) == []

    @pytest.mark.parametrize("semantic_type", ["Fact", "Belief", "Memory", "Goal"])
    def test_blank_object_is_rejected_for_every_type(self, semantic_type):
        assert rule_ids(make(semantic_type=semantic_type, object_text="   ")) == [
            "rule.object_blank"
        ]

    @pytest.mark.parametrize("semantic_type", ["Belief", "Memory", "Commitment"])
    def test_other_types_do_not_require_an_object(self, semantic_type):
        assert rule_ids(make(semantic_type=semantic_type, object_text=None)) == []


class TestPredicate:
    def test_schema_lets_a_blank_predicate_through_and_the_rule_catches_it(self):
        proposal = make(predicate="   ")  # min_length=1 counts spaces

        assert rule_ids(proposal) == ["rule.predicate_blank"]

    def test_normal_predicate_passes(self):
        assert rule_ids(make(predicate="likes")) == []


class TestDescriptor:
    def descriptor(self, label="Sara", attributes=()):
        return CandidateSubjectDescriptor(label=label, attributes=attributes)

    def test_blank_label(self):
        proposal = make(candidate_subject_descriptor=self.descriptor(label="  "))
        assert rule_ids(proposal) == ["rule.label_blank"]

    def test_blank_attribute_value(self):
        proposal = make(
            candidate_subject_descriptor=self.descriptor(
                attributes=(CandidateAttribute(key="role", value="  "),)
            )
        )
        assert rule_ids(proposal) == ["rule.attribute_blank"]

    def test_duplicate_attribute_keys(self):
        proposal = make(
            candidate_subject_descriptor=self.descriptor(
                attributes=(
                    CandidateAttribute(key="role", value="coworker"),
                    CandidateAttribute(key="role", value="friend"),
                )
            )
        )
        assert rule_ids(proposal) == ["rule.attribute_duplicate"]

    def test_clean_descriptor_passes(self):
        proposal = make(
            candidate_subject_descriptor=self.descriptor(
                attributes=(
                    CandidateAttribute(key="role", value="coworker"),
                    CandidateAttribute(key="team", value="data"),
                )
            )
        )
        assert rule_ids(proposal) == []


class TestTemporalMarkers:
    def test_duplicate_labels(self):
        proposal = make(
            temporal_markers=(
                TemporalMarker(label="at", value="2026-01-01"),
                TemporalMarker(label="at", value="2026-02-01"),
            )
        )
        assert rule_ids(proposal) == ["rule.temporal_label_duplicate"]

    def test_blank_value(self):
        proposal = make(temporal_markers=(TemporalMarker(label="at", value="  "),))
        assert rule_ids(proposal) == ["rule.temporal_value_blank"]

    def test_distinct_labels_pass(self):
        proposal = make(
            temporal_markers=(
                TemporalMarker(label="after", value="2026-01-01"),
                TemporalMarker(label="before", value="2026-02-01"),
            )
        )
        assert rule_ids(proposal) == []


class TestScopeBoundaries:
    def test_low_classifier_confidence_is_not_a_semantic_rule(self):
        """A cut-off on classification_confidence is caller policy, not an invariant."""
        assert rule_ids(make(semantic_type="Belief", classification_confidence=0.1)) == []

    def test_commitment_without_a_time_is_allowed(self):
        assert rule_ids(make(semantic_type="Commitment", temporal_markers=())) == []

    def test_all_violations_are_reported_not_just_the_first(self):
        proposal = make(
            semantic_type="Goal",
            predicate="  ",
            object_text=None,
            temporal_markers=(
                TemporalMarker(label="at", value="x"),
                TemporalMarker(label="at", value="y"),
            ),
        )
        assert rule_ids(proposal) == [
            "rule.predicate_blank",
            "rule.object_required",
            "rule.temporal_label_duplicate",
        ]


class TestApplySemanticRules:
    def test_passing_proposals_are_returned_unchanged(self):
        good = make()
        result = ClassificationResult(accepted=(good,), dropped=())

        out = apply_semantic_rules(result, clock=clock)

        assert out.accepted == (good,)
        assert out.accepted[0] is good
        assert out.dropped == ()

    def test_violating_proposal_moves_to_dropped_with_details(self):
        bad = make(semantic_type="Goal", object_text=None)
        good = make()
        result = ClassificationResult(accepted=(bad, good), dropped=())

        out = apply_semantic_rules(result, clock=clock)

        assert out.accepted == (good,)
        assert len(out.dropped) == 1
        drop = out.dropped[0]
        assert drop.reason_code == "SEMANTIC_RULE_VIOLATION"
        assert drop.error_type == "SemanticRejection"
        assert [d.type for d in drop.details] == ["rule.object_required"]
        assert drop.details[0].loc == ("object_text",)
        assert drop.created_at == FIXED
        assert json.loads(drop.payload_preview)["semantic_type"] == "Goal"

    def test_existing_firewall_drops_are_kept_first(self):
        from reality.classification.normalization import normalize_classification

        earlier = normalize_classification("junk", "obs_123", clock=clock)
        bad = make(semantic_type="Goal", object_text=None)
        result = ClassificationResult(accepted=(bad,), dropped=earlier.dropped)

        out = apply_semantic_rules(result, clock=clock)

        assert [d.reason_code for d in out.dropped] == [
            "INVALID_ROOT_TYPE",
            "SEMANTIC_RULE_VIOLATION",
        ]

    def test_input_result_is_not_modified(self):
        bad = make(semantic_type="Goal", object_text=None)
        result = ClassificationResult(accepted=(bad,), dropped=())

        apply_semantic_rules(result, clock=clock)

        assert result.accepted == (bad,)
        assert result.dropped == ()

    def test_same_input_gives_the_same_output(self):
        result = ClassificationResult(
            accepted=(make(semantic_type="Goal", object_text=None), make()), dropped=()
        )
        assert apply_semantic_rules(result, clock=clock) == apply_semantic_rules(result, clock=clock)
