import pytest
from unittest.mock import MagicMock, patch

from reality.schemas import Observation, Assertion
from reality.extraction.pipeline import extract
from reality.extraction.errors import (
    ExtractionError,
    ExtractionMalformedOutput,
    ExtractionInternalError,
    ExtractionProviderUnavailable
)
from reality.extraction.contracts import (
    NormalizedClaim,
    DroppedClaim,
    NormalizationMalformed,
    NormalizationSuccess,
    ValidationSuccess,
    ValidationRejected
)


@pytest.fixture
def valid_observation():
    # Use real constructor bypass, providing properties upfront (no post-creation mutation)
    return Observation.model_construct(id="obs_123")


@pytest.fixture
def unpersisted_observation():
    return Observation.model_construct(id=None)


@patch("reality.extraction.pipeline.get_provider")
@patch("reality.extraction.pipeline.get_audit_sink")
class TestPipelineOrchestration:

    def test_precondition_missing_id_raises_value_error(self, mock_get_audit, mock_get_prov, unpersisted_observation):
        """1. observation.id is None raises ValueError, provider/audit NOT called."""
        with pytest.raises(ValueError, match="Observation.id must not be None"):
            extract(unpersisted_observation)
            
        mock_get_audit.assert_not_called()
        mock_get_prov.assert_not_called()

    @patch("reality.extraction.pipeline.normalize")
    def test_provider_resolved_once_per_call(self, mock_normalize, mock_get_audit, mock_get_prov, valid_observation):
        """2. provider resolved exactly once per extract call."""
        mock_provider = MagicMock()
        mock_get_prov.return_value = mock_provider
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[])
        
        extract(valid_observation)
        
        mock_get_prov.assert_called_once()
        mock_provider.extract.assert_called_once_with(valid_observation)

    @patch("reality.extraction.pipeline.normalize")
    def test_two_calls_resolve_provider_independently(self, mock_normalize, mock_get_audit, mock_get_prov, valid_observation):
        """3. two extract() calls resolve provider independently (no global state)."""
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[])
        
        # Setup two distinct provider references
        mock_provider_a = MagicMock()
        mock_provider_b = MagicMock()
        mock_get_prov.side_effect = [mock_provider_a, mock_provider_b]
        
        # Execute two consecutive calls
        extract(valid_observation)
        extract(valid_observation)
        
        # Verify provider resolution is independent and stateless
        assert mock_get_prov.call_count == 2
        mock_provider_a.extract.assert_called_once_with(valid_observation)
        mock_provider_b.extract.assert_called_once_with(valid_observation)

    @patch("reality.extraction.pipeline.normalize")
    def test_normalization_drops_audited_immediately(self, mock_normalize, mock_get_audit, mock_get_prov, valid_observation):
        """4. normalization drops are audited immediately."""
        mock_sink = MagicMock()
        mock_get_audit.return_value = mock_sink
        
        drop = DroppedClaim(stage="normalization", reason="test", payload_projection={})
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[drop])
        
        extract(valid_observation)
        
        mock_sink.record.assert_called_once_with(drop)

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_validation_failures_become_audit_drops(self, mock_normalize, mock_validate, mock_get_audit, mock_get_prov, valid_observation):
        """5. validation failures become audit drops."""
        mock_sink = MagicMock()
        mock_get_audit.return_value = mock_sink
        
        claim = NormalizedClaim(subject_text="Alice", predicate="knows", object_text="Bob")
        mock_normalize.return_value = NormalizationSuccess(claims=[claim], dropped=[])
        mock_validate.return_value = ValidationRejected(reason="semantic failure")
        
        extract(valid_observation)
        
        mock_sink.record.assert_called_once()
        recorded_drop = mock_sink.record.call_args[0][0]
        assert isinstance(recorded_drop, DroppedClaim)
        assert recorded_drop.stage == "validation"
        assert recorded_drop.reason == "semantic failure"
        assert recorded_drop.payload_projection["subject_text"] == "Alice"
        assert recorded_drop.payload_projection["predicate"] == "knows"
        assert recorded_drop.payload_projection["object_text"] == "Bob"

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_successful_validation_returns_assertion_list(self, mock_normalize, mock_validate, mock_get_audit, mock_get_prov, valid_observation):
        """6. successful validation returns Assertion list."""
        claim = NormalizedClaim()
        mock_normalize.return_value = NormalizationSuccess(claims=[claim], dropped=[])
        
        mock_assertion = Assertion.model_construct()
        mock_validate.return_value = ValidationSuccess(assertion=mock_assertion)
        
        result = extract(valid_observation)
        
        assert len(result) == 1
        assert result[0] is mock_assertion

    @patch("reality.extraction.pipeline.normalize")
    def test_audit_record_failure_during_normalization_raises_internal_error(self, mock_normalize, mock_get_audit, mock_get_prov, valid_observation):
        """7a. audit record failure during normalization raises ExtractionInternalError."""
        mock_sink = MagicMock()
        mock_sink.record.side_effect = RuntimeError("Audit system disk full")
        mock_get_audit.return_value = mock_sink
        
        drop = DroppedClaim(stage="normalization", reason="test", payload_projection={})
        mock_normalize.return_value = NormalizationSuccess(claims=[], dropped=[drop])
        
        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred"):
            extract(valid_observation)

    @patch("reality.extraction.pipeline.validate")
    @patch("reality.extraction.pipeline.normalize")
    def test_audit_record_failure_during_validation_raises_internal_error(self, mock_normalize, mock_validate, mock_get_audit, mock_get_prov, valid_observation):
        """7b. audit record failure during validation raises ExtractionInternalError."""
        mock_sink = MagicMock()
        mock_sink.record.side_effect = RuntimeError("Audit connection lost")
        mock_get_audit.return_value = mock_sink
        
        claim = NormalizedClaim(subject_text="Alice", predicate="knows", object_text="Bob")
        mock_normalize.return_value = NormalizationSuccess(claims=[claim], dropped=[])
        mock_validate.return_value = ValidationRejected(reason="semantic failure")
        
        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred"):
            extract(valid_observation)

    def test_provider_execution_unexpected_error_wrapped(self, mock_get_audit, mock_get_prov, valid_observation):
        """8. unexpected KeyError/TypeError/AttributeError from provider execution are wrapped."""
        mock_provider = MagicMock()
        mock_provider.extract.side_effect = KeyError("missing_key")
        mock_get_prov.return_value = mock_provider
        
        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred.*missing_key"):
            extract(valid_observation)

    def test_unexpected_exceptions_wrapped(self, mock_get_audit, mock_get_prov, valid_observation):
        """9. unexpected provider resolution exceptions are wrapped."""
        mock_get_prov.side_effect = AttributeError("Missing configuration")
        
        with pytest.raises(ExtractionInternalError, match="An unexpected internal error occurred.*Missing configuration"):
            extract(valid_observation)

    def test_existing_extraction_errors_propagate_unchanged(self, mock_get_audit, mock_get_prov, valid_observation):
        """10. existing ExtractionError subclasses propagate unchanged."""
        mock_get_prov.side_effect = ExtractionProviderUnavailable("No provider configured")
        
        with pytest.raises(ExtractionProviderUnavailable, match="No provider configured"):
            extract(valid_observation)

    @patch("reality.extraction.pipeline.normalize")
    def test_malformed_normalization_raises_class_3_error(self, mock_normalize, mock_get_audit, mock_get_prov, valid_observation):
        """11. NormalizationMalformed properly maps to ExtractionMalformedOutput (Class 3)."""
        mock_normalize.return_value = NormalizationMalformed(reason="Payload is entirely invalid")
        
        with pytest.raises(ExtractionMalformedOutput, match="Payload is entirely invalid"):
            extract(valid_observation)