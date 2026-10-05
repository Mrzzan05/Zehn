import importlib.util
import ast
from pathlib import Path

from reality.extraction.normalization import normalize as real_normalize

from unittest.mock import MagicMock, patch

import pytest

from reality.classification.exceptions import ClassificationInternalError
from reality.extraction import audit, errors
from reality.extraction import pipeline as extraction_pipeline
from reality.extraction.audit import NullAuditSink
from reality.extraction.contracts import (
    DroppedClaim,
    NormalizationMalformed,
    NormalizationSuccess,
    NormalizedClaim,
    ValidationRejected,
    ValidationSuccess,
)
from reality.extraction.errors import ExtractionInternalError, ExtractionMalformedOutput
from reality.extraction.pipeline import extract
from reality.provider_errors import (
    ProviderInvalidResponse,
    ProviderTimeout,
    ProviderUnavailable,
)
from reality.schemas import Assertion, Observation


@pytest.fixture
def valid_observation():
    # Constructor bypass with properties given upfront (no post-creation mutation)
    return Observation.model_construct(id=123)


@pytest.fixture
def unpersisted_observation():
    return Observation.model_construct(id=None)


@pytest.fixture
def provider():
    return MagicMock()


@pytest.fixture
def sink():
    return MagicMock()


class TestPipelineOrchestration:

    def test_precondition_missing_id_raises_value_error(self, unpersisted_observation, provider, sink):
        """1. observation.id is None raises ValueError, provider/audit NOT touched."""
        with pytest.raises(ValueError, match="Observation.id must not be None"):
            extract(unpersisted_observation, provider=provider, audit_sink=sink)

        provider.extract.assert_not_called()
        sink.record.assert_not_called()

    @patch("reality.extraction.pipeline.normalize")
    def test_provider_is_invoked_exactly_once_per_call(self, mock_normalize, valid_observation, provider, sink):
        """2. the injected provider is invoked exactly once per extract call."""
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[])

        extract(valid_observation, provider=provider, audit_sink=sink)

        provider.extract.assert_called_once_with(valid_observation)

    @patch("reality.extraction.pipeline.normalize")
    def test_two_calls_use_their_own_providers(self, mock_normalize, valid_observation, sink):
        """3. two extract() calls use exactly the provider each was given (no global state)."""
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[])
        provider_a, provider_b = MagicMock(), MagicMock()

        extract(valid_observation, provider=provider_a, audit_sink=sink)
        extract(valid_observation, provider=provider_b, audit_sink=sink)

        provider_a.extract.assert_called_once_with(valid_observation)
        provider_b.extract.assert_called_once_with(valid_observation)

    @patch("reality.extraction.pipeline.normalize")
    def test_normalization_drops_audited_immediately(self, mock_normalize, valid_observation, provider, sink):
        """4. normalization drops are audited immediately."""
        drop = DroppedClaim(stage="normalization", reason="test", payload_projection={})
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[drop])

        extract(valid_observation, provider=provider, audit_sink=sink)

        sink.record.assert_called_once_with(drop.model_copy(update={"observation_id": 123}))

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_validation_failures_become_audit_drops(self, mock_normalize, mock_validate, valid_observation, provider, sink):
        """5. validation failures become audit drops."""
        claim = NormalizedClaim(subject_text="Alice", predicate="knows", object_text="Bob")
        mock_normalize.return_value = NormalizationSuccess(claims=[claim], dropped=[])
        mock_validate.return_value = ValidationRejected(reason="semantic failure")

        extract(valid_observation, provider=provider, audit_sink=sink)

        sink.record.assert_called_once()
        recorded_drop = sink.record.call_args[0][0]
        assert isinstance(recorded_drop, DroppedClaim)
        assert recorded_drop.stage == "validation"
        assert recorded_drop.reason == "semantic failure"
        assert recorded_drop.payload_projection["subject_text"] == "Alice"
        assert recorded_drop.payload_projection["predicate"] == "knows"
        assert recorded_drop.payload_projection["object_text"] == "Bob"

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_successful_validation_returns_assertion_list(self, mock_normalize, mock_validate, valid_observation, provider, sink):
        """6. successful validation returns Assertion list."""
        mock_normalize.return_value = NormalizationSuccess(claims=[NormalizedClaim()], dropped=[])
        mock_assertion = Assertion.model_construct()
        mock_validate.return_value = ValidationSuccess(assertion=mock_assertion)

        result = extract(valid_observation, provider=provider, audit_sink=sink)

        assert len(result) == 1
        assert result[0] is mock_assertion

    @patch("reality.extraction.pipeline.normalize")
    def test_audit_record_failure_during_normalization_raises_internal_error(self, mock_normalize, valid_observation, provider, sink):
        """7a. audit record failure during normalization raises ExtractionInternalError."""
        sink.record.side_effect = RuntimeError("Audit system disk full")
        drop = DroppedClaim(stage="normalization", reason="test", payload_projection={})
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[drop])

        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred"):
            extract(valid_observation, provider=provider, audit_sink=sink)

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_audit_record_failure_during_validation_raises_internal_error(self, mock_normalize, mock_validate, valid_observation, provider, sink):
        """7b. audit record failure during validation raises ExtractionInternalError."""
        sink.record.side_effect = RuntimeError("Audit connection lost")
        claim = NormalizedClaim(subject_text="Alice", predicate="knows", object_text="Bob")
        mock_normalize.return_value = NormalizationSuccess(claims=[claim], dropped=[])
        mock_validate.return_value = ValidationRejected(reason="semantic failure")

        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred"):
            extract(valid_observation, provider=provider, audit_sink=sink)

    def test_provider_execution_unexpected_error_wrapped(self, valid_observation, provider, sink):
        """8. unexpected KeyError/TypeError/AttributeError from provider execution are wrapped."""
        provider.extract.side_effect = KeyError("missing_key")

        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred.*missing_key"):
            extract(valid_observation, provider=provider, audit_sink=sink)

    def test_existing_extraction_errors_propagate_unchanged(self, valid_observation, provider, sink):
        """10. an ExtractionError raised inside the call propagates as the SAME object, never re-wrapped."""
        exc = ExtractionInternalError("already wrapped")
        provider.extract.side_effect = exc

        with pytest.raises(ExtractionInternalError) as caught:
            extract(valid_observation, provider=provider, audit_sink=sink)

        assert caught.value is exc
        assert caught.value.__cause__ is None

    @patch("reality.extraction.pipeline.normalize")
    def test_malformed_normalization_raises_class_3_error(self, mock_normalize, valid_observation, provider, sink):
        """11. NormalizationMalformed properly maps to ExtractionMalformedOutput (Class 3)."""
        mock_normalize.return_value = NormalizationMalformed(reason="Payload is entirely invalid")

        with pytest.raises(ExtractionMalformedOutput, match="Payload is entirely invalid"):
            extract(valid_observation, provider=provider, audit_sink=sink)

    @pytest.mark.parametrize(
        "exc",
        [
            ProviderUnavailable("down"),
            ProviderTimeout("slow"),
            ProviderInvalidResponse("garbled envelope"),
        ],
        ids=["unavailable", "timeout", "invalid-response"],
    )
    def test_declared_provider_errors_propagate_unchanged(self, valid_observation, provider, sink, exc):
        """12. Declared ProviderError subclasses reach the caller as the SAME object (I-25)."""
        provider.extract.side_effect = exc

        with pytest.raises(type(exc)) as caught:
            extract(valid_observation, provider=provider, audit_sink=sink)

        assert caught.value is exc
        sink.record.assert_not_called()

    def test_non_provider_classification_errors_are_still_wrapped(self, valid_observation, provider, sink):
        """13. Only the declared provider family is exempt; other errors are still Class 6."""
        provider.extract.side_effect = ClassificationInternalError("not a provider failure")

        with pytest.raises(ExtractionInternalError):
            extract(valid_observation, provider=provider, audit_sink=sink)


class TestInjectionContract:

    def test_provider_and_sink_are_required_keyword_only(self, valid_observation, provider, sink):
        """A forgotten or swapped collaborator is impossible, not silent (RFC-004 A8, C3)."""
        with pytest.raises(TypeError):
            extract(valid_observation)
        with pytest.raises(TypeError):
            extract(valid_observation, provider, sink)
        with pytest.raises(TypeError):
            extract(valid_observation, provider=provider)
        with pytest.raises(TypeError):
            extract(valid_observation, audit_sink=sink)

        provider.extract.assert_not_called()
        sink.record.assert_not_called()

    @pytest.mark.parametrize("which", ["provider", "audit_sink"])
    def test_none_collaborator_is_rejected_before_any_action(self, valid_observation, provider, sink, which):
        collaborators = {"provider": provider, "audit_sink": sink}
        collaborators[which] = None

        with pytest.raises(ValueError, match=which):
            extract(valid_observation, **collaborators)

        provider.extract.assert_not_called()
        sink.record.assert_not_called()

    def test_global_registries_are_gone(self):
        assert importlib.util.find_spec("reality.extraction.provider_lifecycle") is None
        for name in ("get_provider", "set_provider", "clear_provider", "get_audit_sink"):
            assert not hasattr(extraction_pipeline, name), name
        for name in ("get_audit_sink", "set_audit_sink", "clear_audit_sink"):
            assert not hasattr(audit, name), name
        assert not hasattr(errors, "ExtractionProviderUnavailable")

    def test_null_audit_sink_works_when_passed_explicitly(self, valid_observation):
        provider = MagicMock()
        provider.extract.return_value = [{"unknown_field": 1}]  # extra field: a structural drop

        result = extract(valid_observation, provider=provider, audit_sink=NullAuditSink())

        assert result == []

PIPELINE_SOURCE = Path(__file__).resolve().parents[2] / "reality" / "extraction" / "pipeline.py"


class TestDropProvenance:
    """RFC-004 R2-D1: extract() is the provenance authority for every audited drop."""

    def test_normalization_drops_reach_the_sink_stamped_and_otherwise_unchanged(self, valid_observation, provider, sink):
        raw = ["junk", {"predicate": "p", "confidence": 0.9}]
        provider.extract.return_value = raw

        extract(valid_observation, provider=provider, audit_sink=sink)

        delivered = [call.args[0] for call in sink.record.call_args_list]
        expected = [d.model_copy(update={"observation_id": 123}) for d in real_normalize(raw).dropped]
        assert len(delivered) == 2
        assert delivered == expected
        assert all(d.stage == "normalization" for d in delivered)

    def test_validation_drops_reach_the_sink_stamped(self, valid_observation, provider, sink):
        provider.extract.return_value = [{
            "assertion_type": "banana",
            "subject_text": "Sara", "subject_type": "Person",
            "predicate": "p", "object_text": "o",
        }]

        result = extract(valid_observation, provider=provider, audit_sink=sink)

        assert result == []
        sink.record.assert_called_once()
        drop = sink.record.call_args[0][0]
        assert drop.stage == "validation"
        assert drop.observation_id == 123

    @patch("reality.extraction.pipeline.normalize")
    def test_an_existing_id_is_overwritten_and_the_original_is_not_mutated(self, mock_normalize, valid_observation, provider, sink):
        original = DroppedClaim(
            stage="normalization", reason="test", payload_projection={"k": "v"}, observation_id=999
        )
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[original])

        extract(valid_observation, provider=provider, audit_sink=sink)

        delivered = sink.record.call_args[0][0]
        assert delivered.observation_id == 123
        assert delivered is not original
        assert original.observation_id == 999
        # Nothing but the id differs.
        assert delivered.model_copy(update={"observation_id": 999}) == original

    def test_a_provider_supplied_observation_id_never_decides_provenance(self, valid_observation, provider, sink):
        provider.extract.return_value = [{"observation_id": 99, "predicate": "p"}]

        extract(valid_observation, provider=provider, audit_sink=sink)

        drop = sink.record.call_args[0][0]
        assert drop.observation_id == 123
        assert drop.payload_projection["observation_id"] == 99  # only ever data

    def test_every_sink_write_goes_through_the_stamping_helper(self):
        tree = ast.parse(PIPELINE_SOURCE.read_text(encoding="utf-8"))
        writes = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "record"
        ]

        assert len(writes) >= 2
        for call in writes:
            assert len(call.args) == 1 and not call.keywords
            arg = call.args[0]
            assert isinstance(arg, ast.Call)
            assert isinstance(arg.func, ast.Name) and arg.func.id == "_stamped"