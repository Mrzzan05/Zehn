"""
Validation and the Engine enforce the same declaration contract (RFC-004
section 9). Everything validation admits, the Engine accepts; every
declaration validation rejects, the Engine refuses as well.
"""

import pytest

from reality import engine
from reality.engine import AssertionContractViolation
from reality.extraction.contracts import NormalizedClaim, ValidationRejected, ValidationSuccess
from reality.extraction.validation import validate
from reality.schemas import Assertion, Observation

VALID = [
    pytest.param(
        dict(assertion_type="attribute", subject_text="Sara", subject_type="Person",
             predicate="mood", object_text="happy"),
        id="attribute"),
    pytest.param(
        dict(assertion_type="relationship", subject_text="Sara", subject_type="Person",
             predicate="works_at", object_text="Acme", object_type="Company"),
        id="relationship"),
]

INVALID_DECLARATION = [
    pytest.param(
        dict(assertion_type="attribute", subject_text="Sara",
             predicate="mood", object_text="happy"),
        id="attribute-no-subject-type"),
    pytest.param(
        dict(assertion_type="relationship", subject_text="Sara", subject_type="Person",
             predicate="works_at", object_text="Acme"),
        id="relationship-no-object-type"),
    pytest.param(
        dict(assertion_type="relationship", subject_text="Sara",
             predicate="works_at", object_text="Acme", object_type="Company"),
        id="relationship-no-subject-type"),
    pytest.param(
        dict(assertion_type="attribute", subject_text="Sara", subject_type="Person",
             predicate="mood", object_text="happy", object_type="Emotion"),
        id="attribute-with-object-type"),
    pytest.param(
        dict(assertion_type="banana", subject_text="Sara", subject_type="Person",
             predicate="mood", object_text="happy"),
        id="unsupported-kind"),
]


def _obs_id() -> int:
    return engine.process_observation(Observation(raw_text="x")).id


def _assertion_from(fields: dict, obs_id: int) -> Assertion:
    return Assertion(
        observation_id=obs_id,
        assertion_type=fields["assertion_type"],
        subject=fields["subject_text"], subject_type=fields.get("subject_type"),
        predicate=fields["predicate"],
        object=fields["object_text"], object_type=fields.get("object_type"),
    )


@pytest.mark.parametrize("fields", VALID)
def test_everything_validation_admits_the_engine_accepts(fields):
    obs_id = _obs_id()

    result = validate(NormalizedClaim(**fields), obs_id)

    assert isinstance(result, ValidationSuccess)
    engine.process_assertion(result.assertion)  # must not raise


@pytest.mark.parametrize("fields", INVALID_DECLARATION)
def test_every_declaration_validation_rejects_the_engine_also_refuses(fields):
    obs_id = _obs_id()

    assert isinstance(validate(NormalizedClaim(**fields), obs_id), ValidationRejected)
    with pytest.raises(AssertionContractViolation):
        engine.process_assertion(_assertion_from(fields, obs_id))