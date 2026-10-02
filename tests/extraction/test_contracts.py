import json
import pytest
from pydantic import ValidationError

from reality.extraction.contracts import (
    NormalizedClaim,
    DroppedClaim,
    NormalizationMalformed,
    ValidationRejected,
    ValidationSuccess
)
from reality.schemas import Assertion


class TestNormalizedClaim:
    def test_nullable_behavior_defaults(self):
        """Test that all fields can legitimately be None/missing."""
        claim = NormalizedClaim()
        assert claim.subject_text is None
        assert claim.object_text is None
        assert claim.predicate is None
        assert claim.type_hints is None

    def test_extra_field_rejection(self):
        """Test that extra fields are strictly forbidden."""
        with pytest.raises(ValidationError):
            NormalizedClaim(subject_text="Subject", unknown_field="invalid")

    def test_type_hints_accepts_valid_dict(self):
        """Test that a valid dict[str, str] is accepted."""
        claim = NormalizedClaim(type_hints={"entity": "person", "confidence": "high"})
        assert claim.type_hints == {"entity": "person", "confidence": "high"}

    def test_type_hints_rejects_internal_nulls(self):
        """Test that type_hints rejects internal None values."""
        with pytest.raises(ValidationError):
            NormalizedClaim(type_hints={"entity": None})
            
    def test_declared_fields_default_to_none(self):
        claim = NormalizedClaim()
        assert (claim.assertion_type, claim.subject_type, claim.object_type) == (None, None, None)

    def test_declared_fields_accept_any_string_unjudged_and_reject_non_strings(self):
        claim = NormalizedClaim(assertion_type="anything", subject_type="", object_type="X")
        assert (claim.assertion_type, claim.subject_type, claim.object_type) == ("anything", "", "X")

        for field in ("assertion_type", "subject_type", "object_type"):
            for bad in (1, True, ["a"], {"a": "b"}):
                with pytest.raises(ValidationError):
                    NormalizedClaim(**{field: bad})

class TestDroppedClaim:
    def test_stage_restriction(self):
        """Test that only 'normalization' and 'validation' are permitted."""
        # Valid cases
        DroppedClaim(stage="normalization", reason="failed", payload_projection={})
        DroppedClaim(stage="validation", reason="failed", payload_projection={})

        # Invalid case
        with pytest.raises(ValidationError):
            DroppedClaim(stage="execution", reason="failed", payload_projection={})

    def test_reason_validation_rejects_whitespace(self):
        """Test that reason rejects empty and whitespace-only strings."""
        with pytest.raises(ValidationError):
            DroppedClaim(stage="normalization", reason="", payload_projection={})
            
        with pytest.raises(ValidationError):
            DroppedClaim(stage="normalization", reason="   ", payload_projection={})

    def test_json_compatible_projection_allows_valid_types(self):
        """Test that standard JSON types are accepted in payload_projection."""
        payload = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, "two", False, None],
            "object": {"nested": "value"}
        }
        claim = DroppedClaim(stage="normalization", reason="failed", payload_projection=payload)
        assert claim.payload_projection == payload
        
        # Explicit json.dumps verification to prove true JSON serialization compatibility
        serialized = json.dumps(claim.model_dump()["payload_projection"])
        assert isinstance(serialized, str)

    def test_json_compatible_projection_rejects_invalid_types(self):
        """Test that Python-specific/complex objects are rejected."""
        class CustomProviderObject:
            pass
            
        with pytest.raises(ValidationError):
            DroppedClaim(
                stage="normalization", 
                reason="failed", 
                payload_projection={"raw": CustomProviderObject()}
            )
            
        # Sets are not JSON-compatible arrays
        with pytest.raises(ValidationError):
            DroppedClaim(
                stage="normalization", 
                reason="failed", 
                payload_projection={"tags": {"a", "b", "c"}}
            )

    def test_extra_field_rejection(self):
        """Test that DroppedClaim strictly forbids extra fields."""
        with pytest.raises(ValidationError):
            DroppedClaim(
                stage="normalization",
                reason="failed",
                payload_projection={},
                extra_metadata="not allowed"
            )


class TestResultTypes:
    @pytest.mark.parametrize("model", [NormalizationMalformed, ValidationRejected])
    def test_reason_validation_for_results(self, model):
        """Test reason field constraints on result wrappers."""
        # Valid
        assert model(reason="Structural failure").reason == "Structural failure"
        
        # Invalid: empty
        with pytest.raises(ValidationError):
            model(reason="")
            
        # Invalid: whitespace only
        with pytest.raises(ValidationError):
            model(reason="   ")

    @pytest.mark.parametrize("model", [NormalizationMalformed, ValidationRejected])
    def test_extra_field_rejection_for_results(self, model):
        """Test that result wrappers forbid extra fields."""
        with pytest.raises(ValidationError):
            model(reason="failed", extra_field="not allowed")

    def test_validation_success_extra_field_rejection(self):
        """Test that ValidationSuccess forbids extra fields."""
        # Use model_construct to bypass Assertion's internal validation,
        # ensuring the test isolates ValidationSuccess's extra field rejection.
        dummy_assertion = Assertion.model_construct()
        
        with pytest.raises(ValidationError):
            ValidationSuccess(assertion=dummy_assertion, extra_field="not allowed")