# RFC-002 Semantic Assertion Model - Generation Prompt

## Role

You are a senior software architect helping document the architecture of Zehn.

Your task is to write RFC-002: Semantic Assertion Model.

This RFC is a foundational architectural document.

It is not:
- a product description
- an implementation guide
- an LLM prompt design document
- a database specification
- an extraction pipeline specification

The goal is to define the semantic mechanism through which observations can produce accepted changes in the Reality Model.

---

# Source Constraint

Use only the provided Zehn source materials.

Do not invent missing architecture.

Do not replace existing terminology with your own terminology.

If a concept is not explicitly defined in the sources, do not introduce it as an architectural decision.

Do not describe implementation technologies unless explicitly required by the source material.

---

# Authority Order

When multiple source materials are provided, apply this priority order:

1. Explicit architectural RFCs
2. Constitutional design documents
3. Product requirements and vision documents
4. Implementation notes and experiments

If lower-priority material conflicts with higher-priority material, preserve the higher-priority architectural decision.

---

# Primary Objective

Explain how Zehn transforms observed information into changes in the Reality Model.

The reader should understand:

- why an Observation cannot directly modify Reality
- why interpretation must be separated from accepted change
- why proposals and assertions are different concepts
- how semantic understanding evolves without corrupting historical evidence

---

# Dependency on RFC-001

This RFC extends RFC-001.

It must preserve the definitions established there:

- Reality Model
- Entity
- Observation
- Relationship
- Observation versus Reality
- Proposal versus Assertion
- Projection versus Primitive

This RFC may refine these concepts but must not redefine them.

---

# Core Concepts To Define

The RFC must define:

## Semantic Proposal

Explain:

- A proposal is a possible interpretation of an Observation.
- A proposal represents what the system thinks the Observation may mean.
- A proposal is not an accepted change.
- Multiple proposals may exist for the same Observation.

The RFC must make clear:

Proposal = interpretation

not:

Proposal = reality change

---

## Assertion

Explain:

- An Assertion represents an accepted change to the Reality Model.
- An Assertion is produced only after evaluation of a proposal.
- Assertions are the mechanism through which Reality Model state changes.

The RFC must preserve:

Observation → Proposal → Assertion → Reality State

---

# Required Architectural Distinctions

## Observation vs Proposal

The RFC must explain:

An Observation records what was communicated.

A Proposal represents a possible meaning extracted from that communication.

They are different because the same Observation may have multiple possible interpretations.

---

## Proposal vs Assertion

The RFC must explain:

A Proposal does not mutate the model.

Only an accepted Assertion can change the model.

This separation exists to prevent:

- incorrect interpretation
- ambiguity becoming fact
- direct LLM authority over reality

---

# Semantic Decomposition

Explain that one Observation may produce multiple semantic consequences.

Example:

A single statement may contain:

- relationship information
- commitment information
- temporal information
- emotional context

The RFC must avoid reducing an Observation into a single category.

---

# Assertion Lifecycle

Describe conceptually:

1. Observation is captured.
2. Possible meanings are proposed.
3. Proposals are evaluated against existing Reality Model state.
4. Accepted changes become Assertions.
5. Assertions update the derived Reality Model state.

Do not define implementation algorithms.

---

# Assertion Operations

If supported by source material, describe possible categories of assertions.

Examples:

- creating new understanding
- modifying existing understanding
- superseding previous understanding
- withdrawing a previous interpretation

Do not introduce deletion semantics that conflict with immutable history.

---

# Provenance Requirement

The RFC must preserve:

Every accepted Assertion must remain traceable back to the Observation(s) that support it.

The system must always be able to answer:

"Why does the Reality Model currently believe this?"

---

# Rejected Alternatives

Include only alternatives supported by source material.

Possible examples:

## Direct Observation-to-Reality mutation

Explain why:

Observation is evidence, not truth.

---

## Direct LLM-controlled state mutation

Explain why:

LLM output is interpretation, not authority.

---

## Single-category extraction

Explain why:

Human communication is multi-dimensional and cannot be reduced to one meaning.

---

# Required Sections

The final RFC should contain:

1. Abstract
2. Motivation
3. Problem Statement
4. Semantic Model Definition
5. Observation Input
6. Semantic Proposal Model
7. Assertion Model
8. Proposal Evaluation
9. Assertion Lifecycle
10. Provenance and Traceability
11. Invariants
12. Rejected Alternatives
13. Relationship With Other RFCs
14. Current Implementation Status

---

# Invariants To Preserve

The RFC must explicitly state:

- Observations never directly mutate Reality.
- Proposals never directly mutate Reality.
- Only accepted Assertions change Reality Model state.
- Every Assertion must preserve provenance.
- LLM-generated output is always a proposal, never an authority.
- Historical observations remain immutable.
- Reality changes must remain explainable from evidence.

---

# Writing Style

Use:

- precise architectural language
- RFC/documentation style
- clear conceptual boundaries

Avoid:

- marketing language
- generic AI assistant terminology
- implementation-specific details
- unsupported architectural claims

The RFC should remain valid regardless of future technologies.

---

# Final Validation Checklist

Before finalizing:

[ ] RFC-002 does not redefine RFC-001 concepts.
[ ] Assertion is not introduced as a new Reality Model primitive.
[ ] Proposal and Assertion are clearly separated.
[ ] Observation remains immutable evidence.
[ ] LLM output is not treated as truth.
[ ] No database or implementation assumptions were introduced.
[ ] Every Reality change remains traceable to evidence.