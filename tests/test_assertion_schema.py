import pytest
from pydantic import ValidationError

from reality.schemas import Assertion


def _fields(**overrides):
    fields = dict(
        observation_id=1, assertion_type="attribute",
        subject="Sara", predicate="likes", object="cats",
    )
    fields.update(overrides)
    return fields


def test_types_default_to_not_declared_and_a_declared_type_is_never_blank():
    a = Assertion(**_fields())
    assert a.subject_type is None and a.object_type is None

    for field in ("subject_type", "object_type"):
        for blank in ("", "   "):
            with pytest.raises(ValidationError):
                Assertion(**_fields(**{field: blank}))