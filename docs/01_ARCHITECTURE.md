# Zehn Architecture

## Purpose

This document defines the architectural principles, boundaries, components, and data flow of Zehn.

The purpose of this architecture is to create a reliable foundation for a long-lived personal reality management system.

The architecture prioritizes:

- correctness over convenience
- explicit decisions over hidden behavior
- stable contracts over rapid changes
- explainability over black-box intelligence

---

# Architectural Vision

Zehn is built around the idea that human reality cannot be represented as isolated notes or conversations.

Reality is a continuously evolving network of:

- observations
- entities
- relationships
- events
- commitments
- decisions
- memories
- intentions

The system therefore models reality as a structured state that evolves through controlled transitions.

---

# Core Architectural Model

The central pipeline:

```
Human Input

      ↓

Observation

      ↓

Semantic Extraction

      ↓

Semantic Proposal

      ↓

Validation / Semantic Firewall

      ↓

Reality Assertion

      ↓

Reality Engine

      ↓

Reality State

      ↓

Projections / User Interfaces
```

---

# Fundamental Principles

## 1. Reality Engine Is The Authority

No external component can directly modify reality.

The Reality Engine is the only authority capable of creating or changing reality state.

AI models, extraction systems, and user interfaces can only propose changes.

---

## 2. AI Is A Semantic Layer

Large Language Models are used for:

- interpretation
- extraction
- classification
- suggestion

They are not trusted as:

- databases
- decision makers
- reality modifiers

---

## 3. Read Before Write

Before creating new information, the system must understand existing reality.

The system should:

- search existing entities
- detect possible duplicates
- identify conflicts
- preserve history

---

## 4. Explicit State Transitions

Reality changes must happen through defined transitions.

Example:

```
Proposal

    ↓

Validation

    ↓

Assertion

    ↓

State Change
```

No silent mutation is allowed.

---

## 5. Information Preservation

The system should avoid destructive operations.

Important information should preserve:

- origin
- timestamp
- previous state
- reasoning
- confidence
- relationships

---

# High-Level Architecture

Zehn consists of several logical layers.

```
┌──────────────────────────────┐
│          Interfaces           │
│ Voice / Text / Applications   │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│       Semantic Layer          │
│ Extraction + Classification   │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│       Reality Layer           │
│ Firewall + Engine             │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│       Persistence Layer       │
│ Repository + Database         │
└──────────────────────────────┘
```

---

# System Components

---

# Observation Layer

## Responsibility

Represents raw human input.

Examples:

- voice transcript
- typed message
- imported information

An observation is a record of what was received.

It does not represent truth.

---

## Rules

Observations:

- are immutable
- keep original content
- have timestamps
- provide historical evidence

---

# Extraction Layer

## Responsibility

Transforms raw observations into semantic candidates.

Example:

Input:

"I should finish the database module next week."

Output:

Possible extracted information:

- task
- deadline
- related project

---

## Rules

Extraction:

- does not modify reality
- does not access database authority
- does not decide final meaning

---

# Classification Layer

## Responsibility

Determines the semantic category of extracted information.

Examples:

- task
- person
- event
- preference
- relationship

---

## Rules

Classification produces proposals.

It does not create reality.

---

# Semantic Firewall

## Responsibility

The Semantic Firewall protects reality from unreliable AI output.

It validates:

- structure
- contracts
- allowed values
- consistency requirements

---

## Principles

The firewall prefers:

- rejection over corruption
- explicit failure over hidden correction

---

# Reality Assertion Layer

## Responsibility

Represents validated statements that are candidates for reality modification.

An assertion contains:

- source observation
- semantic meaning
- validation information
- creation metadata

---

# Reality Engine

## Responsibility

The Reality Engine controls all reality changes.

It handles:

- entity creation
- entity matching
- relationship management
- conflict resolution
- state transitions

---

## Authority Rules

Only Reality Engine can:

- create entities
- update reality
- resolve conflicts
- apply assertions

---

# Repository Layer

## Responsibility

Provides controlled access to persistent data.

Repository hides storage implementation details.

---

## Rules

Repositories:

- do not contain business decisions
- do not interpret AI output
- do not bypass Reality Engine

---

# Storage Layer

## Current Storage

Primary storage:

SQLite

---

## Responsibilities

Storage handles:

- persistence
- indexing
- transactions
- data retrieval

---

# Data Flow

## Normal Flow

```
Input

 ↓

Observation Created

 ↓

Extraction

 ↓

Classification

 ↓

Proposal Validation

 ↓

Assertion Creation

 ↓

Reality Engine Processing

 ↓

Database Update

 ↓

Projection
```

---

# Error Flow

Errors must remain explicit.

Categories:

## Expected Rejection

Example:

Invalid proposal.

Result:

- reject
- record reason
- continue processing

---

## System Failure

Example:

Database failure.

Result:

- abort operation
- preserve consistency

---

# Module Boundaries

## Extraction Boundary

Extraction must not:

- import Reality Engine
- modify database
- create entities

---

## Classification Boundary

Classification must not:

- mutate reality
- access persistence authority

---

## Engine Boundary

Reality Engine must not:

- depend on LLM behavior
- trust external semantic output

---

# Architectural Invariants

The following rules must always remain true.

---

## Invariant 1

No AI output directly changes reality.

---

## Invariant 2

Every reality change has a traceable origin.

---

## Invariant 3

Invalid semantic data cannot enter the reality state.

---

## Invariant 4

Historical information is preserved.

---

## Invariant 5

Contracts between modules are explicit.

---

# Testing Philosophy

Tests represent architectural contracts.

Testing priorities:

1. Boundary correctness
2. Contract enforcement
3. Failure behavior
4. Data integrity
5. Feature behavior

---

# Future Evolution

Possible future extensions:

## Graph Intelligence

Advanced reasoning over reality graph.

---

## Personal Analytics

Understanding patterns over time.

---

## Proactive Assistance

Suggesting actions based on reality state.

---

## Multi-Agent Architecture

Specialized agents operating on controlled interfaces.

---

## Distributed Storage

Synchronization between devices.

---

# Final Architectural Principle

Zehn separates understanding from reality.

The system follows:

```
AI understands.

Validation protects.

Reality Engine decides.

Storage remembers.
```

This separation is the foundation of Zehn's reliability.