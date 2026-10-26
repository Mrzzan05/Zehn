# Architectural Decisions

## Purpose

This document provides a high-level index of important architectural decisions made during Zehn development.

Detailed explanations of individual decisions are stored as ADR documents.

This file should answer:

- What decisions define the architecture?
- Which decisions are frozen?
- Which decisions are still open?
- Which approaches were rejected?

---

# Decision Status Definitions

## Frozen

A decision is considered part of the architecture and should not change without strong justification and an ADR.

---

## Accepted

A decision is approved but may evolve with future requirements.

---

## Proposed

A possible direction currently under discussion.

---

## Rejected

A considered approach that was intentionally not selected.

---

# Decision Index

| ID | Decision | Status |
|----|----------|--------|
| ADR-001 | Reality Engine as the only authority | Frozen |
| ADR-002 | AI models cannot directly modify reality | Frozen |
| ADR-003 | Semantic Firewall architecture | Frozen |
| ADR-004 | Observation → Proposal → Assertion → Reality flow | Frozen |
| ADR-005 | Strict contract-based module boundaries | Frozen |
| ADR-006 | SQLite as initial persistence layer | Accepted |
| ADR-007 | RFC/ADR driven development process | Accepted |
| ADR-008 | Graph-based reality representation | Proposed |
| ADR-009 | Local AI model support | Proposed |

---

# Frozen Decisions

These decisions define the current identity of Zehn.

---

# ADR-001

## Reality Engine Authority

Status:

Frozen

Decision:

The Reality Engine is the only component allowed to modify the Reality State.

Reason:

AI systems and external inputs are probabilistic and cannot be trusted as direct sources of truth.

All changes must pass through controlled logic.

---

# ADR-002

## AI Is Not Reality Authority

Status:

Frozen

Decision:

Large Language Models are semantic interpreters, not truth sources.

AI output can:

- extract information
- classify information
- suggest changes

AI output cannot:

- directly write reality
- silently update entities
- override conflicts

---

# ADR-003

## Semantic Firewall

Status:

Frozen

Decision:

All AI-generated semantic output must pass through a validation boundary before entering the reality system.

The firewall protects against:

- malformed output
- unexpected structures
- invalid assumptions
- unreliable interpretation

---

# ADR-004

## Reality Transformation Pipeline

Status:

Frozen

Decision:

The official information flow is:

```
Observation

↓

Semantic Proposal

↓

Validation

↓

Reality Assertion

↓

Reality Engine

↓

Reality State
```

Each stage has a separate responsibility.

---

# ADR-005

## Strict Module Boundaries

Status:

Frozen

Decision:

Modules communicate through explicit contracts.

Examples:

Extraction cannot:

- modify database
- call Reality Engine
- create entities

Classification cannot:

- mutate state
- bypass validation

Repository cannot:

- contain business decisions

---

# ADR-006

## SQLite Initial Storage

Status:

Accepted

Decision:

SQLite is used as the initial persistence layer.

Reasons:

- simple deployment
- reliability
- local-first compatibility
- sufficient performance for early development

Future storage technologies may be considered if requirements change.

---

# ADR-007

## RFC and ADR Workflow

Status:

Accepted

Decision:

Major architectural changes require documentation before implementation.

RFCs describe:

- problems
- proposed solutions
- alternatives

ADRs record:

- final decisions
- reasoning
- consequences

---

# ADR-008

## Reality Graph Model

Status:

Proposed

Decision:

The long-term reality representation should be graph-oriented.

Reason:

Human reality consists of interconnected entities and relationships.

A graph model naturally represents:

- people
- projects
- events
- memories
- concepts
- dependencies

---

# ADR-009

## Local AI Support

Status:

Proposed

Decision:

Zehn should support local AI models where practical.

Potential technologies:

- local LLM inference
- local embeddings
- private processing

Reasons:

- privacy
- independence
- reduced external dependency

---

# Pending Decisions

The following decisions are intentionally not finalized.

---

## Memory Storage Strategy

Questions:

- relational database only?
- graph database?
- hybrid model?

---

## Embedding Strategy

Questions:

- local embeddings?
- external embedding providers?
- hybrid approach?

---

## Synchronization Model

Questions:

- single-device first?
- cloud synchronization?
- peer-to-peer?

---

## User Confirmation Model

Questions:

- when should the system ask confirmation?
- which changes require approval?

---

## Proactive Assistance Rules

Questions:

- when should Zehn initiate suggestions?
- how much autonomy is acceptable?

---

# Rejected Approaches

---

# Direct LLM Database Writing

Status:

Rejected

Reason:

A language model output is probabilistic and cannot be trusted as a direct state mutation mechanism.

---

# Pure Chatbot Architecture

Status:

Rejected

Reason:

Conversation alone does not create a persistent reality model.

---

# Traditional Note-Based Architecture

Status:

Rejected

Reason:

Notes store information but do not represent relationships and evolving state.

---

# Feature-First Development

Status:

Rejected

Reason:

Adding features before stabilizing the reality model would create technical debt and architectural instability.

---

# Decision Evolution Rule

A frozen decision can only change when:

1. The current decision creates a proven limitation.
2. A replacement provides clear improvement.
3. Existing contracts and consequences are analyzed.
4. A new ADR documents the change.

---

# Current Architectural Principle

The current decision foundation of Zehn is:

```
Human provides observations.

AI proposes meaning.

Validation protects integrity.

Reality Engine controls change.

Storage preserves history.
```