# Zehn AI Context

## Purpose

This document provides the required context for AI systems working on the Zehn project.

The goal is to prevent unnecessary repository exploration and provide only relevant project knowledge.

This document is not a replacement for architecture documentation.

It is a navigation and context layer.

---

# Context Rules

Any AI working on Zehn must understand:

1. Zehn is a long-term architecture project.
2. Existing contracts are intentional.
3. Simplicity does not justify breaking architectural boundaries.
4. Tests represent system contracts.
5. Decisions documented as Frozen must not be changed casually.

---

# Manual Context

The following sections are maintained by humans.

---

# Project Summary

Zehn is a personal reality management system.

The system transforms unstructured human input into structured reality information.

The core idea:

```
Human Input

↓

Semantic Understanding

↓

Validated Proposal

↓

Controlled Reality Update
```

The system separates:

- understanding information
- deciding reality
- storing history

AI helps understand.

The Reality Engine controls change.

---

# Current Development Philosophy

The project prioritizes:

1. Correctness
2. Architectural integrity
3. Long-term maintainability
4. Testability
5. Performance optimization

Performance improvements must not weaken correctness.

---

# Coding Rules

## Architecture Rules

- Do not bypass module boundaries.
- Do not introduce hidden dependencies.
- Do not allow AI output to directly mutate reality.
- Do not move business logic into repositories.
- Do not duplicate existing concepts.

---

## Code Quality Rules

New code should:

- have clear responsibility
- respect existing contracts
- include tests
- avoid unnecessary abstractions

---

## Change Rules

Before changing architecture:

1. Check existing ADRs.
2. Check related RFCs.
3. Understand current contracts.
4. Verify test impact.

---

# Testing Rules

Tests are architectural documentation.

A passing test means:

- expected behavior exists
- a contract is protected

A failing test requires investigation.

Do not remove tests only because implementation becomes inconvenient.

---

# AI Behavior Rules

AI assistants working on Zehn must:

## Do

- inspect existing architecture first
- explain architectural impact
- preserve frozen decisions
- prefer minimal correct changes

---

## Do Not

- rewrite large sections without necessity
- simplify away important boundaries
- introduce shortcuts
- assume AI output is correct
- optimize before correctness

---

# Current Human Focus

Current development focus:

Stabilizing the Reality Core.

Priority order:

1. Extraction reliability
2. Semantic Firewall
3. Reality Engine
4. Persistence integrity
5. Context generation

---

# Generated Context

The following sections are generated automatically.

Do not manually edit below this line.

---

# Current Architecture

Generated from:

- docs/01_ARCHITECTURE.md
- active RFC documents
- ADR documents

---

# Frozen Decisions

Generated from:

- docs/02_DECISIONS.md
- docs/adr/

---

# Current Milestone

Generated from:

- docs/03_STATUS.md
- docs/04_ROADMAP.md

---

# Active Modules

Generated from repository analysis.

Expected sources:

```
reality/
tests/
scripts/
```

---

# Relevant RFCs

Generated based on:

- current task
- changed modules
- architecture dependencies

---

# Relevant ADRs

Generated based on:

- affected components
- architectural decisions

---

# Required Reading Order

Generated recommendation.

Default order:

```
1. docs/00_PROJECT.md

2. docs/01_ARCHITECTURE.md

3. docs/02_DECISIONS.md

4. docs/05_GLOSSARY.md

5. Relevant RFC

6. Relevant ADR

7. Target source files

8. Related tests
```

---

# Current Repository Snapshot

Generated information:

```
Branch:

Commit:

Modified Files:

Test Status:

Python Version:
```

---

# Context Generation Metadata

Generated:

```
Last Updated:

Generator Version:

Source Files:

```

---

# AI Task Execution Checklist

Before modifying code:

[ ] Understand the goal.

[ ] Identify affected architecture boundaries.

[ ] Read related documentation.

[ ] Check frozen decisions.

[ ] Identify required tests.

[ ] Make the smallest correct change.

---

After modification:

[ ] Run tests.

[ ] Verify contracts.

[ ] Update documentation if needed.

[ ] Record architectural decisions if required.

---

# Final AI Principle

For Zehn:

The goal is not to produce code quickly.

The goal is to preserve and evolve a reliable reality system.