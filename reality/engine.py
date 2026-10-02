"""
reality/engine.py

The Reality Engine: the ONLY place in Zehn where semantic decisions are
made — resolving entity identity, deciding when to reuse vs. create an
Entity, and turning Assertions into Relationships.

This file orchestrates reality.repository functions. It never writes
SQL directly and never opens a database connection itself.

Scope for Milestone 1/2 (deliberately excluded per project constraints):
    - fuzzy entity matching
    - embeddings-based similarity
    - LLM calls
    - confidence scoring / evolution
    - contradiction resolution
    - memory decay
Entity resolution here is EXACT-MATCH ONLY (name + entity_type), via
reality.repository.find_entity_by_name_and_type.
"""

from dataclasses import dataclass
from typing import Optional

from reality import repository as repo
from reality.db import transaction
from reality.schemas import Assertion, Entity, Observation, Relationship

DEFAULT_ENTITY_TYPE = "Unknown"

RELATIONSHIP_ASSERTION_TYPE = "relationship"
ATTRIBUTE_ASSERTION_TYPE = "attribute"
SUPPORTED_ASSERTION_TYPES = frozenset(
    {RELATIONSHIP_ASSERTION_TYPE, ATTRIBUTE_ASSERTION_TYPE}
)


class UnsupportedAssertionType(ValueError):
    """The engine only resolves 'relationship' and 'attribute' assertions."""


@dataclass
class AssertionResult:
    assertion: Assertion
    subject_entity: Entity
    object_entity: Optional[Entity] = None
    relationship: Optional[Relationship] = None


def process_observation(observation: Observation) -> Observation:
    with transaction() as conn:
        return repo.create_observation(conn, observation)


def process_assertion(assertion: Assertion) -> AssertionResult:
    """
    Atomic: either the assertion, its entities and its relationship/attribute
    effect are ALL persisted, or none are. The type is validated before any
    write.
    """
    if assertion.assertion_type not in SUPPORTED_ASSERTION_TYPES:
        raise UnsupportedAssertionType(
            f"Unsupported assertion_type {assertion.assertion_type!r}; "
            f"supported: {sorted(SUPPORTED_ASSERTION_TYPES)}"
        )

    with transaction() as conn:
        # Idempotency check: if exactly the same assertion is processed again, 
        # return its previous effects without rewriting them.
        existing = repo.find_assertion(conn, assertion)
        if existing is not None:
            return _rebuild_result(conn, existing)

        saved = repo.create_assertion(conn, assertion)

        subject_type = saved.metadata.get("subject_type", DEFAULT_ENTITY_TYPE)
        subject_entity = _resolve_or_create_entity(conn, saved.subject, subject_type)

        if saved.assertion_type == RELATIONSHIP_ASSERTION_TYPE:
            object_type = saved.metadata.get("object_type", DEFAULT_ENTITY_TYPE)
            object_entity = _resolve_or_create_entity(conn, saved.object, object_type)

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

        updated = _apply_attribute(conn, subject_entity, saved.predicate, saved.object)
        return AssertionResult(saved, updated)


def get_full_trace(relationship_id: int):
    with transaction() as conn:
        return repo.trace_relationship_to_observation(conn, relationship_id)


def _rebuild_result(conn, saved: Assertion) -> AssertionResult:
    """Return the effects of an already-processed assertion without re-applying them."""
    subject_type = saved.metadata.get("subject_type", DEFAULT_ENTITY_TYPE)
    subject = repo.find_entity_by_name_and_type(conn, saved.subject, subject_type)
    
    if saved.assertion_type == RELATIONSHIP_ASSERTION_TYPE:
        object_type = saved.metadata.get("object_type", DEFAULT_ENTITY_TYPE)
        obj = repo.find_entity_by_name_and_type(conn, saved.object, object_type)
        rel = repo.get_relationship_by_assertion(conn, saved.id)
        return AssertionResult(saved, subject, obj, rel)
        
    return AssertionResult(saved, subject)


def _resolve_or_create_entity(conn, name: str, entity_type: str) -> Entity:
    existing = repo.find_entity_by_name_and_type(conn, name, entity_type)
    if existing is not None:
        return existing
    return repo.create_entity(conn, Entity(name=name, entity_type=entity_type))


def _apply_attribute(conn, entity: Entity, key: str, value: str) -> Entity:
    updated = repo.update_entity_attributes(
        conn, entity.id, {**entity.attributes, key: value}
    )
    if updated is None:
        raise RuntimeError(f"Entity {entity.id} disappeared during attribute update")
    return updated