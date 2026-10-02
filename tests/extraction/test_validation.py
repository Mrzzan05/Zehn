import pytest

from reality.extraction.contracts import (
    NormalizedClaim,
    ValidationRejected,
    ValidationSuccess,
)
from reality.extraction.validation import validate


def _claim(**overrides) -> NormalizedClaim:
    """A fully valid relationship claim; tests override one thing at a time."""
    fields = dict(
        assertion_type="relationship",
        subject_text="Alice", subject_type="Person",
        predicate="knows",
        object_text="Bob", object_type="Person",
    )
    fields.update(overrides)
    return NormalizedClaim(**fields)


class TestValidationSemanticBoundary:
    def test_valid_claim_returns_success_and_preserves_meaning(self):
        """Test that a semantically complete claim is successfully mapped to an Assertion."""
        claim = _claim(type_hints={"confidence": "high", "subject_type": "Person"})

        result = validate(claim, observation_id=123)

        assert isinstance(result, ValidationSuccess)
        assert result.assertion.observation_id == 123
        assert result.assertion.assertion_type == "relationship"
        assert result.assertion.subject == "Alice"
        assert result.assertion.predicate == "knows"
        assert result.assertion.object == "Bob"
        assert result.assertion.metadata == {"confidence": "high", "subject_type": "Person"}

    def test_missing_required_fields_rejected(self):
        """Test Class 5 boundary: Incomplete claims allowed through Class 4 are rejected here."""
        result = validate(_claim(subject_text=None), observation_id=123)

        assert isinstance(result, ValidationRejected)
        assert "Semantic validation failed" in result.reason
        assert "schema violation" in result.reason  # rejected for the intended reason

    def test_empty_type_hints_maps_to_empty_metadata(self):
        """Test that explicit None in type_hints safely maps to an empty metadata dictionary."""
        result = validate(_claim(type_hints=None), observation_id=123)

        assert isinstance(result, ValidationSuccess)
        assert result.assertion.metadata == {}

    def test_missing_semantic_value_is_rejected_without_repair(self):
        """No inference: a missing predicate is rejected by the Assertion schema, not defaulted."""
        result = validate(_claim(predicate=None), observation_id=123)

        assert isinstance(result, ValidationRejected)
        assert "Semantic validation failed" in result.reason
        assert "schema violation" in result.reason


class TestDeclaredKindAndTypes:
    def test_relationship_declaration_is_transcribed_one_to_one(self):
        result = validate(
            _claim(subject_type="Person", object_text="Acme", object_type="Company"),
            observation_id=7,
        )

        assert isinstance(result, ValidationSuccess)
        a = result.assertion
        assert (a.assertion_type, a.subject_type, a.object_type) == ("relationship", "Person", "Company")
        assert (a.subject, a.predicate, a.object) == ("Alice", "knows", "Acme")

    def test_unsupported_kind_is_rejected_without_repair(self):
        for bad in ("banana", "Attribute", " attribute", ""):
            result = validate(_claim(assertion_type=bad), observation_id=1)

            assert isinstance(result, ValidationRejected), bad
            assert "assertion_type" in result.reason

    def test_missing_kind_is_rejected(self):
        result = validate(_claim(assertion_type=None), observation_id=1)

        assert isinstance(result, ValidationRejected)
        assert "assertion_type" in result.reason

    @pytest.mark.parametrize(
        "overrides, named",
        [
            ({"assertion_type": "attribute", "subject_type": None, "object_type": None},
             ("subject_type",)),
            ({"object_type": None}, ("object_type",)),
            ({"subject_type": None}, ("subject_type",)),
            ({"subject_type": None, "object_type": None}, ("subject_type", "object_type")),
        ],
        ids=["attribute-no-subject-type", "relationship-no-object-type",
             "relationship-no-subject-type", "relationship-no-types"],
    )
    def test_missing_required_type_fields_are_rejected(self, overrides, named):
        result = validate(_claim(**overrides), observation_id=1)

        assert isinstance(result, ValidationRejected)
        assert "missing required" in result.reason
        for name in named:
            assert name in result.reason

    def test_object_type_on_an_attribute_is_a_contradiction_and_is_rejected(self):
        result = validate(
            _claim(assertion_type="attribute", object_type="Company"), observation_id=1
        )

        assert isinstance(result, ValidationRejected)
        assert "contradictory" in result.reason
        assert "object_type" in result.reason

    def test_type_hints_can_never_supply_the_kind(self):
        """No inference: types are present and an annotation names a kind; still rejected."""
        result = validate(
            _claim(assertion_type=None, type_hints={"assertion_type": "relationship"}),
            observation_id=1,
        )

        assert isinstance(result, ValidationRejected)
        assert "assertion_type" in result.reason

    def test_type_hints_are_inert_annotation(self):
        hints = {"subject_type": "Planet", "object_type": "Company", "assertion_type": "relationship"}
        result = validate(
            _claim(assertion_type="attribute", predicate="mood", object_text="happy",
                   object_type=None, type_hints=hints),
            observation_id=1,
        )

        assert isinstance(result, ValidationSuccess)
        a = result.assertion
        assert a.assertion_type == "attribute"
        assert a.subject_type == "Person"      # the declared field, not the hint
        assert a.object_type is None
        assert a.metadata == hints             # stored, never interpreted

    def test_blank_declared_type_is_rejected_not_repaired(self):
        for blank in ("", "   "):
            result = validate(
                _claim(assertion_type="attribute", object_type=None, subject_type=blank),
                observation_id=1,
            )

            assert isinstance(result, ValidationRejected), repr(blank)
            assert "schema violation" in result.reason

    def test_rejection_reasons_never_contain_provider_content(self):
        result = validate(
            _claim(assertion_type="SECRET-KIND", subject_text="SECRET-SUBJECT"),
            observation_id=1,
        )

        assert isinstance(result, ValidationRejected)
        assert "SECRET" not in result.reason