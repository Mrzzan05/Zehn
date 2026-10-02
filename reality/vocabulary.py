"""
reality/vocabulary.py

Single, neutral definition of the closed assertion vocabulary and of the
type-field rules that each assertion type implies.

Both the extraction layer (validation) and the Reality Engine import from
this module and from nowhere else for these facts. This module imports
nothing from the rest of the package, so neither layer has to depend on the
other to share the vocabulary.

This module only DEFINES the rules as data. It does not check anything:
enforcement belongs to validation (admission) and to the Engine
(boundary contract).

Changing the vocabulary requires an RFC amendment (RFC-004 section 6).
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping

__all__ = [
    "ATTRIBUTE_ASSERTION_TYPE",
    "RELATIONSHIP_ASSERTION_TYPE",
    "SUPPORTED_ASSERTION_TYPES",
    "SUBJECT_TYPE_FIELD",
    "OBJECT_TYPE_FIELD",
    "TypeFieldRule",
    "TYPE_FIELD_RULES",
]

ATTRIBUTE_ASSERTION_TYPE: Final = "attribute"
RELATIONSHIP_ASSERTION_TYPE: Final = "relationship"

SUPPORTED_ASSERTION_TYPES: Final = frozenset(
    {RELATIONSHIP_ASSERTION_TYPE, ATTRIBUTE_ASSERTION_TYPE}
)

# Names of the typed Assertion fields that carry entity types (RFC-004 section 9).
SUBJECT_TYPE_FIELD: Final = "subject_type"
OBJECT_TYPE_FIELD: Final = "object_type"


@dataclass(frozen=True)
class TypeFieldRule:
    """Which type fields an assertion type must carry and which it must not."""

    required: frozenset[str]
    forbidden: frozenset[str]


# RFC-004 section 9, "Required per kind":
#   relationship => subject_type and object_type
#   attribute    => subject_type, and no object_type
# Keys are exactly SUPPORTED_ASSERTION_TYPES (pinned by a test).
TYPE_FIELD_RULES: Final[Mapping[str, TypeFieldRule]] = MappingProxyType(
    {
        RELATIONSHIP_ASSERTION_TYPE: TypeFieldRule(
            required=frozenset({SUBJECT_TYPE_FIELD, OBJECT_TYPE_FIELD}),
            forbidden=frozenset(),
        ),
        ATTRIBUTE_ASSERTION_TYPE: TypeFieldRule(
            required=frozenset({SUBJECT_TYPE_FIELD}),
            forbidden=frozenset({OBJECT_TYPE_FIELD}),
        ),
    }
)