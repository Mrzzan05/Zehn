# Zehn Glossary

## Purpose

This document defines the official terminology used throughout Zehn.

All architecture documents, RFCs, ADRs, code comments, and discussions should use these definitions.

When a term has multiple possible meanings, the definition in this document has priority.

---

# Core Concepts

---

# Observation

## Definition

An Observation is the raw representation of information received by Zehn.

It represents what was provided by the user or an external source.

An Observation does not represent truth.

---

## Examples

- voice transcript
- typed message
- imported text
- external information

---

## Important Properties

An Observation:

- preserves original input
- has a timestamp
- has a source
- is immutable

---

# Semantic Extraction

## Definition

Semantic Extraction is the process of transforming raw observations into structured semantic candidates.

---

## Purpose

Extraction answers:

"What information might exist inside this observation?"

---

## Example

Input:

"I need to finish the database module next week."

Possible extraction:

```
Type:
Task

Content:
Finish database module

Time:
Next week
```

---

## Important Rule

Extraction creates possibilities.

It does not create reality.

---

# Semantic Proposal

## Definition

A Semantic Proposal is a structured suggestion describing a possible meaning extracted from information.

---

## Purpose

It represents:

"The system believes this information might mean X."

---

## Important Properties

A Semantic Proposal:

- is not truth
- requires validation
- can be rejected

---

# Classification

## Definition

Classification is the process of assigning semantic categories to extracted information.

---

## Examples

Possible classifications:

- Task
- Person
- Event
- Preference
- Relationship
- Goal

---

## Important Rule

Classification describes information.

It does not modify reality.

---

# Semantic Firewall

## Definition

The Semantic Firewall is the protection boundary between AI-generated interpretations and the Reality System.

---

## Purpose

It prevents unreliable information from entering reality.

---

## Responsibilities

- validate structure
- enforce contracts
- reject invalid data
- preserve audit information

---

# Validation

## Definition

Validation determines whether a proposal satisfies system rules.

---

## Validation Types

### Structural Validation

Checks:

- schema
- required fields
- data types

---

### Semantic Validation

Checks:

- allowed meaning
- consistency
- logical constraints

---

# Reality Assertion

## Definition

A Reality Assertion is a validated statement that can be processed by the Reality Engine.

---

## Relationship

```
Observation

↓

Proposal

↓

Validation

↓

Assertion
```

---

## Important Rule

An Assertion is still a request to change reality.

It is not automatically applied.

---

# Reality

## Definition

Reality is the current structured state maintained by Zehn.

It represents what the system currently accepts as true.

---

## Reality Includes

- entities
- relationships
- properties
- historical information
- state transitions

---

# Reality Engine

## Definition

The Reality Engine is the authority responsible for changing Reality.

---

## Responsibilities

- process assertions
- create entities
- update entities
- manage relationships
- resolve conflicts

---

## Important Rule

No other component can directly modify Reality.

---

# Entity

## Definition

An Entity represents a distinct object or concept in the reality model.

---

## Examples

- Person
- Project
- Organization
- Place
- Idea

---

## Properties

Entities may have:

- attributes
- relationships
- history

---

# Relationship

## Definition

A Relationship represents a connection between entities.

---

## Examples

```
Person

works_on

Project
```

or

```
Person

knows

Person
```

---

## Purpose

Relationships allow Zehn to model context instead of isolated data.

---

# Attribute

## Definition

An Attribute is a property describing an entity.

---

## Examples

Person:

```
name = Sara
```

Project:

```
status = Active
```

---

# Projection

## Definition

A Projection is a representation of reality optimized for a specific use case.

---

## Examples

Reality can generate:

- task lists
- calendars
- summaries
- reminders

---

## Important Rule

A Projection is not the source of truth.

It is generated from Reality.

---

# Memory

## Definition

Memory in Zehn is not simple data storage.

Memory represents preserved information with context and history.

---

## Memory Includes

- origin
- relationships
- changes
- time
- meaning

---

# Context

## Definition

Context is the subset of information required to understand or perform a specific task.

---

## Example

An AI working on Extraction does not need the entire project.

It needs:

- extraction rules
- relevant RFCs
- contracts
- tests

---

# Context Generation

## Definition

Context Generation is the process of selecting and preparing relevant information for an AI or human.

---

## Sources

Possible sources:

- architecture documents
- ADRs
- RFCs
- source code
- graph data
- project status

---

# Graph

## Definition

A Graph is a representation of connected entities and relationships.

---

## Purpose

The graph represents how concepts relate over time.

---

# Graph Node

## Definition

A Graph Node represents an object or concept.

Usually corresponds to an entity or important information unit.

---

# Graph Edge

## Definition

A Graph Edge represents a relationship between nodes.

---

# Audit

## Definition

Audit information records important system events and decisions.

---

## Purpose

Audit provides:

- traceability
- debugging capability
- historical understanding

---

# Contract

## Definition

A Contract defines the expected behavior and structure between system components.

---

## Examples

- data schemas
- interfaces
- module boundaries

---

# Frozen Decision

## Definition

A Frozen Decision is an architectural choice that should not change without explicit review.

---

# RFC

## Definition

Request For Comments.

A document proposing a significant architectural or technical change.

---

# ADR

## Definition

Architectural Decision Record.

A document recording why a specific architectural decision was made.

---

# Milestone

## Definition

A milestone represents a development stage with clear goals and acceptance criteria.

---

# Provider

## Definition

A Provider is an external or replaceable implementation that supplies a capability.

---

## Examples

- LLM provider
- Speech-to-text provider
- Embedding provider

---

# Reality State

## Definition

The current persisted condition of the Reality Model.

---

## Important Rule

Reality State is the result of controlled transitions, not direct edits.

---

# Semantic Reliability Principle

The following distinction must always remain:

```
AI Confidence

is not equal to

Reality Reliability
```

A model can be confident and wrong.

---

# Final Terminology Rule

When designing Zehn:

Use:

"proposal" before acceptance.

Use:

"assertion" before mutation.

Use:

"projection" instead of duplicate truth.

Use:

"reality" only for controlled state.