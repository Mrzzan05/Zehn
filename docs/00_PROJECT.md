# Zehn

## Project Identity

Zehn is a personal reality management system designed to help humans externalize, organize, and evolve their personal knowledge, commitments, memories, and intentions over long periods of time.

Zehn is not a simple note-taking application, task manager, calendar, or chatbot.

It is an evolving model of a person's reality built from observations, decisions, relationships, goals, and experiences.

The system transforms unstructured human input into structured knowledge while preserving uncertainty, history, and context.

---

# Vision

## Purpose

Humans continuously generate information:

- ideas
- plans
- commitments
- memories
- decisions
- personal preferences
- relationships
- unfinished thoughts

Most of this information is lost because traditional tools require users to manually organize it.

Zehn aims to remove this cognitive burden by creating a system that can understand, organize, and maintain a long-term representation of a person's reality.

---

## Long-Term Vision

The long-term vision of Zehn is to become a personal cognitive infrastructure.

A system that:

- remembers meaningful information across years
- understands changes over time
- connects related concepts automatically
- helps users make better decisions
- reduces cognitive overload
- acts as a reliable external memory layer

Zehn should not replace human thinking.

It should amplify it.

---

# Mission

The mission of Zehn is:

> Build a trustworthy personal reality model that converts human experiences and intentions into structured, evolving knowledge while maintaining accuracy, transparency, and user control.

---

# Core Problem

Current digital tools separate human life into isolated systems:

- Notes store information without understanding.
- Calendars store events without context.
- Task managers store actions without meaning.
- Chatbots answer questions without persistent reality.
- Memory systems store data without reliability.

The missing layer is a system that understands relationships between information over time.

Zehn exists to solve this missing layer.

---

# Goals

## Primary Goals

### 1. Cognitive Offloading

Allow users to express thoughts naturally without requiring manual organization.

Example:

A user describes their day through voice or text.

Zehn identifies:

- tasks
- ideas
- commitments
- important facts
- possible reminders
- relationships

---

### 2. Reality Modeling

Represent user information as connected entities and relationships instead of isolated documents.

The system should understand:

- what exists
- what happened
- what changed
- what is planned
- what is uncertain

---

### 3. Long-Term Memory

Maintain useful information across months and years.

Memory should include:

- historical context
- changes
- decisions
- user preferences
- important relationships

---

### 4. Trustworthy AI Integration

AI should assist understanding, not control reality.

The AI layer proposes interpretations.

The Reality Engine decides what becomes reality.

---

### 5. Human-Centered Interaction

The user should interact naturally.

Primary interaction methods:

- voice
- conversation
- lightweight text input

The user should not need to manually maintain complex structures.

---

# Non Goals

The following are explicitly not goals of Zehn.

## Generic Chatbot

Zehn is not designed to be another general AI assistant.

Conversation is an interface, not the core product.

---

## Simple Note Application

Zehn does not aim to compete with traditional note-taking applications.

Raw notes are inputs, not the final representation.

---

## Automatic Truth Generation

Zehn does not assume AI output is correct.

AI-generated information must pass through validation and reality rules.

---

## Full Human Replacement

Zehn should assist human decisions.

It should not independently make important decisions on behalf of users.

---

## Feature Quantity Competition

The goal is not maximum features.

The goal is a reliable core system.

---

# Philosophy

## Reality Before Convenience

A wrong memory is worse than missing memory.

The system must prefer:

- uncertainty over false certainty
- rejection over corruption
- explicit conflicts over silent overwrites

---

## Structure Before Intelligence

Better architecture is more valuable than bigger models.

The quality of the reality model determines the quality of intelligence built on top of it.

---

## AI As Interpreter, Not Authority

Large language models are powerful semantic interpreters.

They are not trusted sources of truth.

The system separates:

Input understanding

from

Reality modification.

---

## Evolution Over Snapshots

Human reality changes.

The system must preserve:

- history
- transitions
- previous states
- reasoning behind changes

---

## Minimal Manual Management

The user should provide information.

The system should handle organization.

---

# Target Users

## Primary User

Individuals who:

- have many ideas
- manage complex goals
- want long-term memory
- need cognitive organization
- prefer natural communication

---

## Future Users

Potential future users:

- students
- researchers
- creators
- entrepreneurs
- professionals managing complex information

---

# Project Scope

## Current Scope

The current development scope includes:

- personal reality modeling
- observation storage
- semantic extraction
- proposal generation
- validation pipeline
- reality assertions
- entity and relationship management
- persistent storage
- context generation for AI collaboration

---

## Future Scope

Potential future capabilities:

- voice-first interaction
- calendar integration
- personal analytics
- advanced graph reasoning
- proactive assistance
- multi-device synchronization

---

# Success Criteria

Zehn is successful when:

1. Users can capture information naturally.
2. Important information is not lost.
3. The system maintains a reliable reality model.
4. AI collaboration becomes more efficient through generated context.
5. The system remains understandable and maintainable after years of evolution.

---

# Repository Layout

Current repository structure:

```
.
├── reality/
│   ├── extraction/
│   ├── classification/
│   ├── engine/
│   ├── repository/
│   └── storage/
│
├── tests/
│
├── docs/
│   ├── adr/
│   ├── rfc/
│   ├── milestones/
│   ├── knowledge/
│   └── templates/
│
├── scripts/
│
└── context/
```

---

# Development Principles

## Documentation Driven Development

Important architectural decisions must be documented before implementation.

---

## RFC Before Major Changes

Major changes require an RFC describing:

- problem
- motivation
- proposed design
- alternatives
- risks

---

## ADR For Permanent Decisions

Architectural decisions that become part of the system identity must be recorded as ADRs.

---

## Tests As Contracts

Tests represent system expectations.

Breaking tests requires understanding why the contract changed.

---

## Stable Foundations First

The project prioritizes:

1. correctness
2. architecture quality
3. maintainability
4. performance optimization

---

# Current Project State

Zehn is currently in foundational architecture development.

Completed foundations include:

- Reality Model concept
- Semantic Firewall concept
- Extraction pipeline boundaries
- Classification contracts
- Strict validation approach
- Repository and storage foundations
- Test-driven milestone progression

---

# Final Definition

Zehn is:

> A personal reality engine that transforms human experiences into a structured, evolving, and trustworthy model of reality.

The system is built around one principle:

**AI may interpret reality, but it must never silently define reality.**