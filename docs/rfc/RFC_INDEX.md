# Zehn RFC Index

This directory contains architectural decisions and system contracts for Zehn.

RFCs are not implementation notes.
They describe the reasoning, constraints, and invariants that must remain stable.

---

## RFC List

| RFC | Title | Status |
|---|---|---|
| RFC-001 | Reality Model | Active |
| RFC-002 | Semantic Firewall | Active |
| RFC-003 | Extraction Pipeline | Active |
| RFC-004 | Assertion Engine | Active |
| RFC-005 | Context Generation | Draft |

---

## Architectural Order

Zehn follows this conceptual pipeline:

Observation
↓
Semantic Extraction
↓
Semantic Proposal
↓
Reality Assertion
↓
Reality State
↓
Context Projection

---

## Important Rule

LLM output is never the source of truth.

The Reality Engine owns state mutation.

LLM components can propose changes but cannot directly modify reality.