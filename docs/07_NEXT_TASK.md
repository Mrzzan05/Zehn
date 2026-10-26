# Zehn Next Task

## Purpose

This document defines the current active development task.

It provides a focused execution context for developers and AI assistants.

Only the active objective should be described here.

Large architectural plans belong in:

- ROADMAP
- RFC
- ADR

---

# Current Objective

## Title

Reality Core Stabilization

---

## Description

Improve and stabilize the current Reality Core architecture while preserving all existing contracts.

The goal is not adding new features.

The goal is increasing reliability, correctness, and maintainability of the existing foundation.

---

# Scope

## Included

The current work may include:

- improving extraction reliability
- improving validation behavior
- improving audit correctness
- strengthening contracts
- adding missing tests
- improving error handling

---

## Excluded

The current work must not include:

- redesigning the Reality Model
- changing frozen architectural decisions
- replacing storage architecture
- introducing UI layers
- adding unnecessary abstractions
- implementing future product features

---

# Allowed Files

Files allowed to change during current task:

```
reality/
tests/
docs/
```

Specific files should be listed before implementation.

Example:

```
reality/extraction/*
tests/extraction/*
```

---

# Forbidden Files

The following areas require explicit architectural review before modification:

```
Reality Engine core contracts

Database schema

Frozen ADR decisions

Public interfaces

Project architecture documents
```

---

# Required Understanding

Before changing code, understand:

- current architecture
- existing contracts
- related RFCs
- existing tests
- module boundaries

---

# Acceptance Criteria

A task is complete only when:

## Functional

- Required behavior exists.
- Existing behavior remains correct.

---

## Architectural

- Boundaries remain respected.
- No hidden dependencies are introduced.
- Existing principles remain valid.

---

## Testing

Required tests:

- existing tests pass
- new behavior has coverage
- failure cases are tested

---

## Documentation

Update documentation if:

- architecture changes
- decisions change
- new concepts are introduced

---

# Expected Tests

Before completion:

Run:

```
pytest
```

Expected result:

```
All tests passing
```

Additional tests should cover:

- success cases
- invalid input
- boundary conditions
- failure behavior

---

# Implementation Rules

## Prefer

- small changes
- explicit code
- existing patterns
- backward compatibility

---

## Avoid

- large rewrites
- premature optimization
- speculative features
- unnecessary dependencies

---

# AI Instructions

When assisting with this task:

1. Read relevant documentation first.

2. Explain architectural impact before major changes.

3. Do not modify unrelated files.

4. Preserve existing contracts.

5. If requirements conflict, stop and request clarification.

---

# Completion Checklist

Before marking task complete:

[ ] Objective achieved

[ ] Tests passing

[ ] No forbidden files modified

[ ] Architecture preserved

[ ] Documentation updated if necessary

[ ] Changes committed with clear message

---

# Notes

Current task notes:

```
No active notes.
```