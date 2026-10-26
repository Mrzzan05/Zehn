# ADR Directory

## Purpose

This directory contains Architectural Decision Records.

ADR documents preserve important architectural decisions and their reasoning.

An ADR explains:

- what decision was made
- why it was made
- what consequences it creates

---

# When To Create An ADR

Create an ADR when a decision affects:

- system architecture
- module boundaries
- core principles
- long-term maintenance
- technology direction

---

# Examples Of ADR Topics

Examples:

- Reality Engine authority model
- Database selection
- AI provider strategy
- Graph architecture
- Storage approach
- Security model
- Synchronization strategy

---

# ADR Structure

Each ADR should contain:

```
Title

Status

Context

Decision

Consequences

Alternatives
```

---

# Naming Convention

Format:

```
ADR-XXX-title.md
```

Examples:

```
ADR-001-reality-engine-authority.md

ADR-002-storage-strategy.md
```

---

# ADR Lifecycle

Typical lifecycle:

```
Proposed

↓

Accepted

↓

Implemented

↓

Superseded
```

---

# Status Definitions

## Proposed

The decision is under discussion.

---

## Accepted

The decision has been approved.

---

## Implemented

The decision exists in the system.

---

## Superseded

A newer ADR replaced this decision.

---

# Rules

## ADRs Are Historical Records

Do not rewrite history.

If a decision changes:

Create a new ADR.

Example:

```
ADR-001-old-storage.md

ADR-010-new-storage.md
```

---

## Frozen Decisions

Some ADRs become architectural foundations.

Changing them requires:

- explicit review
- impact analysis
- replacement ADR

---

# Relationship With RFC

Typical flow:

```
Problem

↓

RFC

↓

Decision

↓

ADR

↓

Implementation
```

---

# AI Usage Rule

AI assistants working on Zehn must read relevant ADRs before modifying architecture.

An ADR represents intentional design choices, not optional suggestions.