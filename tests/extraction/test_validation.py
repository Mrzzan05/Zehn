from reality.extraction.contracts import (
    NormalizedClaim,
    ValidationSuccess,
    ValidationRejected
)
from reality.extraction.validation import validate


class TestValidationSemanticBoundary:
    def test_valid_claim_returns_success_and_preserves_meaning(self):
        """Test that a semantically complete claim is successfully mapped to an Assertion."""
        claim = NormalizedClaim(
            subject_text="Alice",
            predicate="knows",
            object_text="Bob",
            type_hints={"confidence": "high", "subject_type": "Person"}
        )
        
        result = validate(claim, observation_id=123)
        
        assert isinstance(result, ValidationSuccess)
        assert result.assertion.observation_id == 123
        assert result.assertion.subject == "Alice"
        assert result.assertion.predicate == "knows"
        assert result.assertion.object == "Bob"
        assert result.assertion.metadata == {"confidence": "high", "subject_type": "Person"}

    def test_missing_required_fields_rejected(self):
        """Test Class 5 boundary: Incomplete claims allowed through Class 4 are rejected here."""
        # A claim with no subject_text is structurally valid (NormalizedClaim) 
        # but semantically invalid (Assertion).
        claim = NormalizedClaim(
            subject_text=None,
            predicate="knows",
            object_text="Bob"
        )
        
        result = validate(claim, observation_id=123)
        
        assert isinstance(result, ValidationRejected)
        assert "Semantic validation failed" in result.reason

    def test_empty_type_hints_maps_to_empty_metadata(self):
        """Test that explicit None in type_hints safely maps to an empty metadata dictionary."""
        claim = NormalizedClaim(
            subject_text="Alice",
            predicate="knows",
            object_text="Bob",
            type_hints=None
        )
        
        result = validate(claim, observation_id=123)
        
        assert isinstance(result, ValidationSuccess)
        assert result.assertion.metadata == {}

    def test_missing_semantic_value_is_rejected_without_repair(self):
        """
        Prove that validation does not attempt to repair or infer missing values,
        and strictly relies on the Assertion schema for enforcement.
        """
        claim = NormalizedClaim(
            subject_text="Alice",
            predicate=None,  # Missing predicate, no inference should occur
            object_text="Bob",
            type_hints=None
        )
        
        result = validate(claim, observation_id=123)
        
        # Ensures that the pipeline did not inject a default (like "Unknown")
        # and allowed the Assertion schema to properly reject it.
        assert isinstance(result, ValidationRejected)
        assert "Semantic validation failed" in result.reason