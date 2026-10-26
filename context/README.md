# Zehn Context System

## Purpose

The context directory contains generated knowledge packages for AI assistants.

The purpose is reducing unnecessary repository exploration while preserving important project knowledge.

---

# Core Principle

Context is not the source of truth.

Source of truth:


Code

Documentation

Tests

Architectural Decisions


Context is only a compressed navigation layer.

---

# Structure


context/

├── generated/

│ ├── full_context.md

│ ├── architecture_context.md

│ ├── extraction_context.md

│ └── task_context.md


---

# Generated Files

All files inside:


context/generated/


are automatically generated.

Do not manually edit them.

---

# Context Types

## Full Context

General project understanding.

Used when:

- starting a new AI session
- explaining project identity

---

## Architecture Context

Contains:

- architecture principles
- decisions
- boundaries

Used for:

- architecture changes
- RFC review

---

## Extraction Context

Focused on:

- extraction pipeline
- semantic processing
- validation flow

---

## Task Context

Focused on:

- current objective
- allowed changes
- acceptance criteria

---

# Future Context Generation

Future versions will include:

- graph-based retrieval
- RFC selection
- ADR selection
- source code relevance
- test relevance

---

# Generation Pipeline

Current:


Documentation

↓

build_context.py

↓

Generated Context


Future:


Task

↓

Graph Analysis

↓

Relevant Knowledge

↓

Context Generation

↓

AI Assistant


---

# Rules

Generated context must:

- remain deterministic
- be traceable to sources
- never override architecture documents
- never contain undocumented decisions