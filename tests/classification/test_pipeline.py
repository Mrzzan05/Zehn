from datetime import datetime, timezone

import pytest

from reality.classification.exceptions import (
    ClassificationError,
    ClassificationInternalError,
    ProviderError,
    ProviderInvalidResponse,
    ProviderTimeout,
    ProviderUnavailable,
)
from reality.classification.pipeline import classify_observation
from reality.classification.schemas import ClassificationObservation, MetadataEntry

FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def clock() -> datetime:
    return FIXED


def make_observation(observation_id: str = "obs_123") -> ClassificationObservation:
    return ClassificationObservation(
        observation_id=observation_id,
        raw_content="Sara likes cats",
        timestamp=FIXED,
        modality_metadata=(MetadataEntry(key="channel", value="text"),),
    )


def payload(source_observation_id: str) -> dict:
    return {
        "source_observation_id": source_observation_id,
        "semantic_type": "Fact",
        "predicate": "likes",
        "classification_confidence": 0.9,
        "derivation_metadata": {"derivation_type": "explicit", "engine": "fake"},
    }


class FakeProvider:
    def __init__(self, output: object):
        self.output = output
        self.seen: list[ClassificationObservation] = []

    def classify(self, observation: ClassificationObservation) -> object:
        self.seen.append(observation)
        return self.output


class RaisingProvider:
    def __init__(self, exc: BaseException):
        self.exc = exc

    def classify(self, observation: ClassificationObservation) -> object:
        raise self.exc


class TestOutputHandling:
    def test_provider_receives_the_observation_and_result_is_normalized(self):
        observation = make_observation()
        provider = FakeProvider([payload("obs_123")])

        result = classify_observation(observation, provider, clock=clock)

        assert provider.seen == [observation]
        assert len(result.accepted) == 1
        assert result.dropped == ()

    def test_provenance_is_anchored_to_the_observation_not_the_provider(self):
        provider = FakeProvider([payload("obs_999")])

        result = classify_observation(make_observation("obs_123"), provider, clock=clock)

        assert result.accepted == ()
        assert result.dropped[0].reason_code == "PROVENANCE_MISMATCH"

    def test_broken_provider_output_becomes_an_audited_drop_not_an_exception(self):
        result = classify_observation(make_observation(), FakeProvider(None), clock=clock)

        assert result.accepted == ()
        assert result.dropped[0].reason_code == "NULL_OUTPUT"
        assert result.dropped[0].created_at == FIXED

    def test_empty_successful_output_is_distinct_from_a_failure(self):
        result = classify_observation(make_observation(), FakeProvider([]), clock=clock)

        assert result.accepted == ()
        assert result.dropped == ()


class TestFailureModel:
    @pytest.mark.parametrize(
        "exc",
        [
            ProviderUnavailable("down"),
            ProviderTimeout("slow"),
            ProviderInvalidResponse("garbled envelope"),
        ],
    )
    def test_declared_provider_errors_propagate_unchanged(self, exc):
        with pytest.raises(type(exc)) as caught:
            classify_observation(make_observation(), RaisingProvider(exc), clock=clock)

        assert caught.value is exc

    def test_unexpected_exception_is_wrapped_without_leaking_its_message(self):
        original = RuntimeError("api-key=SECRET-123 out of memory")

        with pytest.raises(ClassificationInternalError) as caught:
            classify_observation(make_observation(), RaisingProvider(original), clock=clock)

        assert "SECRET-123" not in str(caught.value)
        assert "RuntimeError" in str(caught.value)
        assert caught.value.__cause__ is original

    def test_provider_failure_is_never_converted_into_a_result(self):
        with pytest.raises(ClassificationError):
            classify_observation(
                make_observation(), RaisingProvider(RuntimeError("boom")), clock=clock
            )

    def test_hierarchy(self):
        assert issubclass(ProviderUnavailable, ProviderError)
        assert issubclass(ProviderTimeout, ProviderError)
        assert issubclass(ProviderInvalidResponse, ProviderError)
        assert issubclass(ProviderError, ClassificationError)
        assert issubclass(ClassificationInternalError, ClassificationError)
        assert not issubclass(ClassificationInternalError, ProviderError)


class TestSemanticStage:
    def test_rule_violating_proposal_is_dropped_after_passing_the_schema_firewall(self):
        goal_without_object = payload("obs_123") | {"semantic_type": "Goal"}
        provider = FakeProvider([goal_without_object, payload("obs_123")])

        result = classify_observation(make_observation(), provider, clock=clock)

        assert len(result.accepted) == 1
        assert result.accepted[0].semantic_type == "Fact"
        assert len(result.dropped) == 1
        drop = result.dropped[0]
        assert drop.reason_code == "SEMANTIC_RULE_VIOLATION"
        assert drop.error_type == "SemanticRejection"
        assert drop.details[0].type == "rule.object_required"
        assert drop.created_at == FIXED
