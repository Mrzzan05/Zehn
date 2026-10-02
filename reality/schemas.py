"""
reality/schemas.py
 
Pydantic models defining the SHAPE of Zehn's core concepts.
This file has no database logic and no business logic — it only
defines what each concept looks like and validates its fields.
 
This is the frozen data-layer contract for Milestone 1. These models
will also validate LLM-produced JSON in Phase 2, so field constraints
here double as the first line of defense against malformed extraction
output (empty strings, missing required fields, wrong types).
 
Concepts:
    Observation  -> raw record of what the user said
    Assertion    -> structured claim extracted from an Observation
    Entity       -> persistent object in the reality model
    Relationship -> typed connection between two Entities
"""
 
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field
 
 
def utc_now() -> datetime:
    """Single source of truth for 'current time' across all models."""
    return datetime.now(timezone.utc)
 
 
class ZehnBaseModel(BaseModel):
    """
    Shared config for all Zehn schemas:
    - strips leading/trailing whitespace from every string field
      (relevant once fields are populated from LLM JSON output)
    - forbids unexpected extra fields, so malformed LLM output fails
      validation loudly instead of silently passing through
    """
 
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
 
 
class Observation(ZehnBaseModel):
    """
    A permanent, immutable record of something the user said.
    This is the ground truth of the system — nothing here is ever
    edited or deleted, only added to.
    """
 
    id: Optional[int] = None  # None until saved; SQLite assigns the real id
    raw_text: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
 
 
class Assertion(ZehnBaseModel):
    """
    A structured claim extracted from an Observation, BEFORE it has
    been reconciled against existing Entities/Relationships.
 
    Modeled loosely as a subject-predicate-object triple so it can
    represent both "facts about an entity" (assertion_type="attribute")
    and "links between entities" (assertion_type="relationship").
 
    Examples:
        subject="Sarah", predicate="blocked_on", object="graph question"
        subject="Sarah", predicate="participated_in", object="Tuesday meeting"
    """
    # Entity types (RFC-004 section 9, A3): typed fields, not free-form
    # metadata. None means "not declared"; a declared type is never blank.
    # The model stays permissive about presence: enforcement belongs to
    # validation and the Engine, not to this schema.
    subject_type: Optional[str] = Field(default=None, min_length=1)
    object_type: Optional[str] = Field(default=None, min_length=1)
 
    id: Optional[int] = None
    observation_id: int  # which Observation this claim came from
    # The supported vocabulary is closed and defined once, in
    # reality/vocabulary.py (RFC-004 section 6). This model is deliberately
    # permissive about it: validation admits and the Engine enforces.
    # Adding a type requires an RFC amendment.
    assertion_type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    # Free-form extra data (e.g. confidence, raw LLM output, extraction notes).
    # Kept as a flexible dict instead of rigid columns — avoids premature
    # schema design before we know what metadata actually matters.
    # Inert: no Engine or validation behavior reads it (RFC-004, I-10).
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
 
 
class Entity(ZehnBaseModel):
    """
    A persistent object in the user's reality model (Person, Project,
    Place, Concept, Document, Event, ...). Mutable: attributes can be
    updated as new Assertions are resolved against it.
    """
 
    id: Optional[int] = None
    name: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    # Flexible attribute bag instead of per-type rigid columns — keeps
    # the schema simple while entity types vary widely.
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
 
 
class Relationship(ZehnBaseModel):
    """
    A typed, directed edge between two Entities, derived from a
    single originating Assertion. This link is what makes the
    Relationship -> Assertion -> Observation trace possible.
    """
 
    id: Optional[int] = None
    source_entity_id: int
    target_entity_id: int
    relation_type: str = Field(min_length=1)
    assertion_id: int  # the Assertion that produced this relationship
    created_at: datetime = Field(default_factory=utc_now)