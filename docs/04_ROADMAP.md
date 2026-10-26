# Zehn Roadmap

## Purpose

This document describes the planned evolution path of Zehn.

The roadmap focuses on building a reliable foundation before adding advanced capabilities.

Zehn development follows this principle:

> A smaller reliable system is more valuable than a larger unreliable system.

---

# Development Philosophy

Zehn is developed in layers.

Each layer must provide a stable foundation for the next layer.

The development order is:

```
Architecture Foundation

        ↓

Reality Model

        ↓

Semantic Understanding

        ↓

Context Intelligence

        ↓

Human Interaction

        ↓

Product Evolution
```

---

# Completed

## Project Foundation

Status:

Completed

Achievements:

- Initial repository structure created
- Documentation system established
- Development workflow defined
- RFC/ADR process introduced

---

## Reality Model Foundation

Status:

Completed

Achievements:

- Reality Model concept defined
- Observation concept introduced
- Assertion concept introduced
- Entity and Relationship concepts defined
- Reality Engine responsibility established

---

## Semantic Firewall Foundation

Status:

Completed

Achievements:

- Strict contracts created
- Semantic boundaries defined
- Validation approach established
- Invalid AI output rejection strategy implemented

---

## Extraction Foundation

Status:

Completed

Achievements:

- Extraction pipeline architecture created
- Provider boundary separated
- Normalization layer introduced
- Validation flow established
- Audit capability foundation created

---

## Classification Foundation

Status:

Completed

Achievements:

- Classification contracts defined
- Proposal validation implemented
- Classification tests established

---

# Current Phase

# Phase 1 — Reality Core Stabilization

Status:

Active

Goal:

Create a reliable foundation where every piece of information entering Zehn follows controlled and explainable rules.

---

## Objectives

### Complete Extraction Reliability

Tasks:

- finalize extraction contracts
- improve failure handling
- preserve audit information
- validate provider boundaries

---

### Complete Reality Engine Foundation

Tasks:

- entity lifecycle management
- relationship handling
- conflict resolution
- assertion processing

---

### Strengthen Persistence Layer

Tasks:

- stable repository contracts
- database integrity
- migration strategy
- historical state preservation

---

### Expand Testing Infrastructure

Tasks:

- architecture tests
- contract tests
- regression tests
- failure scenario testing

---

# Phase 2 — Knowledge Graph Foundation

Status:

Planned

Goal:

Transform the reality model into an interconnected knowledge structure.

---

## Objectives

### Reality Graph

Implement:

- entity graph
- relationship graph
- temporal connections
- dependency tracking

---

### Graph Analysis

Support:

- finding related information
- discovering patterns
- identifying missing connections

---

### Graph Documentation

Integrate:

- Graphify
- graph reports
- generated context

---

# Phase 3 — AI Context Intelligence

Status:

Planned

Goal:

Create efficient AI collaboration through dynamic context generation.

---

## Objectives

### Context Builder

Build a system that can generate focused AI context from:

- architecture documents
- ADRs
- RFCs
- current status
- graph state
- relevant modules

---

### Context Optimization

The system should provide:

- only relevant information
- current architectural constraints
- required files
- active decisions

Avoid:

- unnecessary repository dumping
- outdated information
- irrelevant files

---

### Multi-Agent Support

Future possibility:

Different AI agents can work on:

- architecture
- coding
- testing
- research

while sharing controlled context.

---

# Phase 4 — Human Interaction Layer

Status:

Future

Goal:

Allow natural interaction with Zehn.

---

## Voice Interface

Capabilities:

- speech input
- transcription
- semantic extraction
- conversational interaction

Possible technologies:

- Whisper-based transcription
- local speech processing

---

## Conversation Interface

Purpose:

Provide a natural way to interact with reality.

The conversation layer should be an interface above the reality system.

It should not become the source of truth.

---

## Calendar And Reminder Projection

Possible capabilities:

- task reminders
- deadlines
- schedules
- planning assistance

These should be projections of reality, not independent systems.

---

# Phase 5 — Personal Intelligence Layer

Status:

Long Term

Goal:

Move from passive organization to intelligent assistance.

---

## Pattern Recognition

Possible capabilities:

- identify recurring behaviors
- detect unfinished intentions
- recognize changes

---

## Decision Assistance

Possible capabilities:

- summarize relevant history
- provide context
- compare previous decisions

---

## Proactive Assistance

Potential capabilities:

- suggest actions
- detect conflicts
- remind about forgotten commitments

All proactive behavior must respect user control.

---

# Phase 6 — Product Evolution

Status:

Long Term

Goal:

Transform Zehn from a personal project into a usable product.

---

## Possible Areas

### Multi Device Support

- synchronization
- secure storage
- device continuity

---

### Privacy Architecture

- local-first processing
- encrypted storage
- user-owned data

---

### User Experience

- simple interaction
- minimal configuration
- invisible organization

---

# Deferred Ideas

The following ideas are intentionally postponed.

---

## Multimodal Understanding

Including:

- images
- documents
- external sensors

Reason:

The core reality model must mature first.

---

## Autonomous Agents

Reason:

Autonomy without a reliable reality model creates unsafe behavior.

---

## Complex UI Systems

Reason:

The primary challenge is the intelligence layer, not interface complexity.

---

## Cloud Infrastructure

Reason:

Local-first architecture provides better control during foundation development.

---

# Long-Term Vision

The final vision of Zehn is:

A personal reality engine that continuously understands, organizes, and evolves alongside a human life.

The system should become:

- a trusted memory layer
- a decision context layer
- an organization layer
- a personal knowledge infrastructure

---

# Roadmap Principle

The order of development is intentional:

```
Trust

↓

Structure

↓

Understanding

↓

Interaction

↓

Intelligence
```

Zehn must earn the ability to assist before attempting to act.