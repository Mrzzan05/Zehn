# RFC-001 Reality Model - Generation Prompt

## Role

You are a senior software architect helping document the architecture of Zehn.

Your task is to write RFC-001: Reality Model.

This RFC is a permanent architectural document.
It is not a product description, marketing document, tutorial, or implementation summary.

The goal is to preserve architectural decisions, principles, constraints, and reasoning.

---

# Source Constraint

Use only the provided Zehn source materials.

Do not invent missing architecture.

Do not replace existing terminology with your own terminology.

If a concept is not explicitly defined in the sources, do not introduce it as an architectural decision.

---

# Primary Objective

Explain what Zehn's Reality Model is and why this model exists.

The reader should understand:

- why Zehn is not a note-taking system
- why Zehn is not a traditional task manager
- why reality is modeled as an evolving structure
- why raw input must be separated from accepted knowledge
- why entities and relationships are first-class concepts

---

# Required Concepts

The RFC must cover these concepts:

## Reality Model

Explain:

- Reality as an evolving model of the user's world
- Difference between stored information and accepted reality
- Why Zehn needs a model instead of a collection of notes


## Core Primitive Types

The RFC must define:

### Entity

Explain:

- What an Entity represents
- Why entities have identity
- Why identity continuity matters


### Observation

Explain:

- Observation as raw evidence/input
- Why observations are immutable
- Why observation is not equal to truth


### Relationship

Explain:

- Relationships as first-class citizens
- Why connections between entities matter
- Why a graph representation is necessary


---

# Important Architectural Distinctions

The RFC must preserve these distinctions:

## Observation vs Reality

A user statement is not automatically a fact.

The system must separate:

"What was observed"

from:

"What is accepted as reality."


## Proposal vs Assertion

Interpretation is not mutation.

A possible understanding of user input must not directly change system state.


## Task vs Primitive

Tasks are projections or views over reality.

Tasks should not become the fundamental representation of the system.


---

# Required Sections

The final RFC should contain:

1. Abstract
2. Motivation
3. Problem Statement
4. Design Philosophy
5. Reality Model Definition
6. Core Primitive Types
7. Entity Model
8. Observation Model
9. Relationship Model
10. Knowledge Evolution
11. Identity and Continuity
12. Invariants
13. Rejected Alternatives
14. Relationship With Other RFCs
15. Current Implementation Status

---

# Invariants To Preserve

The RFC must explicitly state:

- Observations are immutable.
- Reality changes through accepted assertions.
- LLM output is not the source of truth.
- Relationships are as important as entities.
- The system models reality; it does not store conversations.
- Historical evidence must remain distinguishable from current state.

---

# Rejected Ideas To Mention

Include rejected alternatives only if supported by source material.

Examples:

- Simple note storage
- Chat history as memory
- Direct LLM-controlled state mutation
- Flat task lists as the main model

Explain why they conflict with Zehn's architecture.

---

# Writing Style

Use:

- precise technical language
- architecture documentation style
- clear explanations

Avoid:

- marketing language
- exaggerated AI terminology
- generic "AI assistant" descriptions
- unnecessary implementation details

The RFC should remain valuable even if implementation technologies change.

---

# Final Validation Checklist

Before finalizing, verify:

[ ] No architectural decision was invented.
[ ] Core terminology matches Zehn terminology.
[ ] Reality Model is clearly distinguished from memory/chat/task systems.
[ ] Entity, Observation, and Relationship are clearly defined.
[ ] Rejected alternatives explain design choices.
[ ] The document can be used as long-term architecture reference.