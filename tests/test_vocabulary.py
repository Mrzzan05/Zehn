from dataclasses import FrozenInstanceError

import pytest

from reality import engine, vocabulary


def test_closed_vocabulary_is_exactly_attribute_and_relationship():
    # Literals on purpose: this pins the vocabulary independently of the module.
    assert vocabulary.SUPPORTED_ASSERTION_TYPES == frozenset({"attribute", "relationship"})
    assert isinstance(vocabulary.SUPPORTED_ASSERTION_TYPES, frozenset)


def test_type_field_rules_cover_every_supported_type_and_encode_section_9():
    rules = vocabulary.TYPE_FIELD_RULES

    assert set(rules) == set(vocabulary.SUPPORTED_ASSERTION_TYPES)

    assert rules["relationship"].required == {"subject_type", "object_type"}
    assert rules["relationship"].forbidden == frozenset()
    assert rules["attribute"].required == {"subject_type"}
    assert rules["attribute"].forbidden == {"object_type"}

    with pytest.raises(TypeError):
        rules["extra"] = rules["attribute"]  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        rules["attribute"].required = frozenset()  # type: ignore[misc]


def test_engine_uses_the_shared_vocabulary_not_a_copy():
    assert engine.SUPPORTED_ASSERTION_TYPES is vocabulary.SUPPORTED_ASSERTION_TYPES
    assert engine.RELATIONSHIP_ASSERTION_TYPE == vocabulary.RELATIONSHIP_ASSERTION_TYPE