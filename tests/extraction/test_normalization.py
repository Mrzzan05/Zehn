import json
from reality.extraction.normalization import normalize
from reality.extraction.contracts import (
    NormalizationMalformed,
    NormalizationSuccess,
    NormalizedClaim
)


class TestNormalizationDiscovery:
    def test_unmappable_payload_returns_malformed(self):
        """Test Class 3 failures: Provider output must be a direct list."""
        result_str = normalize("Just a plain string response")
        result_dict = normalize({"claims": [{"predicate": "is"}]}) 
        result_none = normalize(None)

        for result in [result_str, result_dict, result_none]:
            assert isinstance(result, NormalizationMalformed)
            assert result.reason

    def test_zero_signal_returns_empty_success(self):
        """Test Class 1 behavior: Recognizable empty list returns zero claims/drops."""
        result = normalize([])
        assert isinstance(result, NormalizationSuccess)
        assert len(result.claims) == 0
        assert len(result.dropped) == 0


class TestStructuralMapping:
    def test_mappable_incomplete_claims_pass(self):
        """Test that missing semantic fields (e.g., subject) map cleanly without rejection."""
        result = normalize([{"predicate": "is_a"}])  # No subject, no object
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.claims) == 1
        assert len(result.dropped) == 0
        
        claim = result.claims[0]
        assert claim.predicate == "is_a"
        assert claim.subject_text is None  # Pass-through for Validation (Class 5)

    def test_semantically_empty_values_pass(self):
        """Test Class 4 boundary: Semantically empty strings map cleanly without rejection."""
        result = normalize([{"subject_text": "", "predicate": "is_a"}])
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.claims) == 1
        assert len(result.dropped) == 0
        
        claim = result.claims[0]
        assert claim.subject_text == ""
        assert claim.predicate == "is_a"
        
    def test_extra_fields_cause_structural_drop(self):
        """Test Class 4 boundary: Extra fields violate structure and are dropped."""
        result = normalize([
            {"predicate": "is_a", "confidence": 0.9} # confidence is an extra field
        ])
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.claims) == 0
        assert len(result.dropped) == 1
        
        drop = result.dropped[0]
        assert drop.stage == "normalization"
        assert "confidence" in drop.payload_projection

    def test_type_hints_passed_through_not_generated(self):
        """Test that type hints are mapped strictly if provided, never inferred."""
        result1 = normalize([{"subject_text": "A", "type_hints": {"A": "Person"}}])
        assert isinstance(result1, NormalizationSuccess)
        assert result1.claims[0].type_hints == {"A": "Person"}

        result2 = normalize([{"subject_text": "B"}])
        assert isinstance(result2, NormalizationSuccess)
        assert result2.claims[0].type_hints is None

    def test_invalid_type_hints_cause_structural_drop(self):
        """Test Class 4 boundary: Nested/invalid type hints violate dict[str,str]."""
        result = normalize([
            {"subject_text": "A", "type_hints": {"A": {"nested": "value"}}}
        ])
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.dropped) == 1
        assert "type_hints" in result.dropped[0].reason

    def test_non_dict_fragments_dropped(self):
        """Test that fragments that aren't dictionaries are safely caught and dropped."""
        result = normalize([42, "not a dictionary"])
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.claims) == 0
        assert len(result.dropped) == 2
        
        # Uses the stable "value" wrapper
        assert result.dropped[0].payload_projection == {"value": 42}
        assert result.dropped[1].payload_projection == {"value": "not a dictionary"}
        
    def test_unserializable_fragments_dropped_safely(self):
        """Test that unserializable items produce a deterministic fallback payload."""
        class CustomObj:
            pass
            
        result = normalize([CustomObj(), {"invalid": CustomObj()}])
        
        assert isinstance(result, NormalizationSuccess)
        assert len(result.dropped) == 2
        
        # Assert structural properties only: contains error field and is JSON serializable
        for drop in result.dropped:
            assert "error" in drop.payload_projection
            serialized = json.dumps(drop.payload_projection)
            assert isinstance(serialized, str)