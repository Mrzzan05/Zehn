# Knowledge Directory

## Purpose

This directory contains technical and conceptual knowledge related to Zehn.

Knowledge documents store information that helps future development but does not represent:

- architectural decisions
- active tasks
- project status

---

# What Belongs Here

Examples:

## Technical Knowledge

- SQLite behavior
- Python patterns
- Pydantic concepts
- Testing strategies

---

## Research Notes

- AI architecture research
- Graph concepts
- Memory systems
- Human-computer interaction

---

## Learning Documents

- concepts learned during development
- experiments
- comparisons

---

# What Does Not Belong Here

Do not store:

## Decisions

Use:

```
docs/adr/
```

---

## Proposed Architecture Changes

Use:

```
docs/rfc/
```

---

## Current Progress

Use:

```
docs/03_STATUS.md
```

---

## Active Tasks

Use:

```
docs/07_NEXT_TASK.md
```

---

# Naming Convention

Use descriptive names:

Examples:

```
sqlite-transaction-notes.md

graph-model-research.md

llm-context-strategy.md
```

---

# Knowledge Rules

Knowledge documents should:

- explain concepts clearly
- include references when needed
- avoid undocumented assumptions
- remain independent from temporary implementation details

---

# Long-Term Purpose

The knowledge directory acts as the accumulated technical memory of Zehn development.