"""
reality/engine.py

The Reality Engine: the ONLY place in Zehn where semantic decisions are
made: resolving entity identity, deciding when to reuse vs. create an
Entity, and turning Assertions into Relationships.

It owns the transaction boundary (one Assertion = one atomic unit of work)
and never writes SQL itself. Repository functions are building blocks that
never commit.

Boundary contract (RFC-004 sections 1, 4, 6): an Assertion entering the
Engine must carry a supported assertion_type and the type fields that kind
requires. Violations raise BEFORE any write. The Engine never defaults,
guesses or reads behavior from free-form metadata.
"""

from dataclasses import dataclass
from typing import Optional

from reality import repository as repo
from reality.db import transaction
from reality.schemas import Assertion, Entity, Observation, Relationship
from reality.vocabulary import (
    OBJECT_TYPE_FIELD,
    RELATIONSHIP_ASSERTION_TYPE,
    SUBJECT_TYPE_FIELD,
    SUPPORTED_ASSERTION_TYPES,
    TYPE_FIELD_RULES,
)


class AssertionContractViolation(ValueError):
    """
    An Assertion handed to the Engine breaks the boundary contract.

    This is a caller bug, not a data error: a correctly assembled pipeline
    rejects such claims upstream as audited drops (RFC-004 section 6).
    Messages carry only the assertion type and field NAMES, never payload.
    """


class UnsupportedAssertionType(AssertionContractViolation):
    """assertion_type is outside the closed vocabulary."""


class MissingTypeField(AssertionContractViolation):
    """A type field required by this assertion type is not declared."""


class ContradictoryTypeField(AssertionContractViolation):
    """A type field forbidden for this assertion type is declared."""


@dataclass
class AssertionResult:
    """What processing an Assertion produced, for callers, tests and the demo."""

    assertion: Assertion
    subject_entity: Entity
    object_entity: Optional[Entity] = None
    relationship: Optional[Relationship] = None


def process_observation(observation: Observation) -> Observation:
    """Persist a raw Observation exactly as given, in its own transaction."""
    with transaction() as conn:
        return repo.create_observation(conn, observation)


def process_assertion(assertion: Assertion) -> AssertionResult:
    """
    Atomic: the assertion, its entities and its attribute/relationship effect
    are ALL persisted, or none are. The contract is checked before any write.
    Replay of an already-processed assertion applies nothing and returns the
    originally applied effects.
    """
    _check_contract(assertion)

    with transaction() as conn:
        existing = repo.find_assertion(conn, assertion)
        if existing is not None:
            return _rebuild_result(conn, existing)

        saved = repo.create_assertion(conn, assertion)
        subject_entity = _resolve_or_create_entity(conn, saved.subject, saved.subject_type)

        if saved.assertion_type == RELATIONSHIP_ASSERTION_TYPE:
            object_entity = _resolve_or_create_entity(conn, saved.object, saved.object_type)
            relationship = repo.create_relationship(
                conn,
                Relationship(
                    source_entity_id=subject_entity.id,
                    target_entity_id=object_entity.id,
                    relation_type=saved.predicate,
                    assertion_id=saved.id,
                ),
            )
            # Reload from storage so callers never see stale copies.
            subject_entity = repo.get_entity_by_id(conn, subject_entity.id)
            object_entity = repo.get_entity_by_id(conn, object_entity.id)
            return AssertionResult(saved, subject_entity, object_entity, relationship)

        # _check_contract guarantees this is an attribute assertion.
        updated = _apply_attribute(conn, subject_entity, saved.predicate, saved.object)
        return AssertionResult(saved, updated)


def get_full_trace(relationship_id: int):
    """Read-only passthrough to the Relationship -> Assertion -> Observation trace."""
    with transaction() as conn:
        return repo.trace_relationship_to_observation(conn, relationship_id)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _check_contract(assertion: Assertion) -> None:
    """
    Enforce the boundary contract from the shared vocabulary rules.

    One violation is raised, in this fixed order: unsupported type, missing
    required field, contradictory field. Nothing is repaired or defaulted.
    """
    kind = assertion.assertion_type
    if kind not in SUPPORTED_ASSERTION_TYPES:
        raise UnsupportedAssertionType(
            f"Unsupported assertion_type {kind!r}; "
            f"supported: {sorted(SUPPORTED_ASSERTION_TYPES)}"
        )

    rule = TYPE_FIELD_RULES[kind]
    declared = {
        name
        for name in (SUBJECT_TYPE_FIELD, OBJECT_TYPE_FIELD)
        if getattr(assertion, name) is not None
    }

    missing = rule.required - declared
    if missing:
        raise MissingTypeField(f"{kind!r} assertion requires: {sorted(missing)}")

    contradictory = rule.forbidden & declared
    if contradictory:
        raise ContradictoryTypeField(
            f"{kind!r} assertion must not declare: {sorted(contradictory)}"
        )


def _rebuild_result(conn, saved: Assertion) -> AssertionResult:
    """Return the effects of an already-processed assertion without re-applying them."""
    subject = repo.find_entity_by_name_and_type(conn, saved.subject, saved.subject_type)
    if saved.assertion_type == RELATIONSHIP_ASSERTION_TYPE:
        obj = repo.find_entity_by_name_and_type(conn, saved.object, saved.object_type)
        rel = repo.get_relationship_by_assertion(conn, saved.id)
        return AssertionResult(saved, subject, obj, rel)
    return AssertionResult(saved, subject)


def _resolve_or_create_entity(conn, name: str, entity_type: str) -> Entity:
    """Exact-match resolution on (name, entity_type); create on miss (RFC-004 section 4)."""
    existing = repo.find_entity_by_name_and_type(conn, name, entity_type)
    if existing is not None:
        return existing
    return repo.create_entity(conn, Entity(name=name, entity_type=entity_type))


def _apply_attribute(conn, entity: Entity, key: str, value: str) -> Entity:
    """Overwrite-by-key on the entity's attributes; the newest assertion wins for that key."""
    updated = repo.update_entity_attributes(
        conn, entity.id, {**entity.attributes, key: value}
    )
    if updated is None:
        raise RuntimeError(f"Entity {entity.id} disappeared during attribute update")
    return updated