# RFC-001: Reality Model

**Status:** Foundational — binding on all subsequent architectural and implementation work
**Derives from:** Zehn Vision (Personal Reality Model, v1.0), Zehn Product Requirements Document v1.0
**Authority:** This document defines the conceptual vocabulary of the Zehn system. No later document may introduce a concept that contradicts it; later documents may only refine, constrain, or implement what is defined here.
**Scope:** This document is architectural. It defines what the system models and why, and the primitive types that structure that model. It does not define storage, databases, query languages, APIs, or model architectures. Every statement below must remain true regardless of what technology eventually implements it.

---

## 1. Abstract

Zehn maintains a structured, evolving model of one person's reality — the people, places, projects, commitments, and ideas that make up their life, and the relationships between them — built incrementally from things the person says. This document, RFC-001, defines that model: what it represents, why it takes the form it does, and the primitive types (Entity, Observation, Relationship) from which every other concept in the system is composed. It establishes the distinction between what was observed and what the system accepts as its current understanding of reality, and the related distinction between an interpretation proposed by the system and an actual change to that understanding. It is the foundational document of the Zehn architecture; subsequent RFCs refine, constrain, or implement the concepts defined here, but none may redefine them.

---

## 2. Motivation

Zehn's founding correction, stated in the Vision document, is that a system built around capturing and classifying things a person says — however automatic or invisible that classification becomes — is still, architecturally, a document store with a smart librarian. A note-taking app answers *where did I put that?* A task manager answers *what do I need to do?* Zehn exists to answer a different question: *what do I currently understand about my own life, and how did that understanding just change?*

This motivates a system whose unit of value is not the note, the task, or the memory, but the world model itself — a living structure of entities and the relationships between them, built incrementally from everything the person has said. Tasks, reminders, and calendar events are not primary objects in this system; they are projections, generated from the model when it implies an obligation or a moment in time, and capable of disappearing once rendered, while the underlying knowledge they were drawn from persists.

The Reality Model is the architectural response to this motivation.

---

## 3. Problem Statement

A document-oriented system — a notes app, a flat task list, a chat history treated as memory — stores things a person produced. Its central operation is filing and retrieval: where is this, and how do I get it back. That problem is well-solved by decades of prior art, and solving it better does not produce the thing Zehn needs to be.

The problem Zehn exists to solve is different and harder: a person's own memory does not reliably maintain the relationships between things over time — who is connected to what project, what a decision made months ago implied for a decision being made today, what a scattered set of remarks about the same person actually adds up to. This is a relational problem, not a retrieval problem. A document store, however well-indexed, can only return what was put into it; it has no way to represent what follows from what was put into it. Zehn's bet is that this relational structure — not raw recall — is the thing worth externalizing, and that solving it requires a different underlying model than any document-oriented system can provide, because a document has no claim about the world independent of its own text: it can be replaced or annotated, but it cannot be reinterpreted.

This also means raw input cannot be treated as settled truth. What a person says is evidence about their world, not the world itself. A system that treats "the user said it" as equivalent to "it is true" will misrepresent their life back to them the first time they misspeak, misremember, or change their mind — and will have no mechanism for correcting that misrepresentation without discarding the historical record of what was actually said. The architecture must therefore separate what was observed from what is currently accepted as the system's best understanding of reality, and must allow that understanding to be revised — including retroactively reinterpreted — without destroying the evidentiary record that revision is based on.

---

## 4. Design Philosophy

**Reality Model, not Document Model.** The system does not store documents that happen to be made searchable. It maintains a structured, queryable representation of the user's actual world — who and what exists in it, and how those things relate. A voice recording is not a file to be stored; it is an observation that either confirms, extends, or contradicts what the model currently believes. This is the single architectural decision everything else in this document follows from.

**The model is a graph, not a collection.** Entities and the relationships between them are the atomic unit of the system — not notes, not folders, not tags. A thought about a person is not filed under a note bearing their name; it becomes a connection that touches that person and whatever else the thought concerns. A collection (a folder, a tag, a list) only ever encodes one dimension of organization at a time. A relationship is a claim about how two things in the world actually relate, and nothing restricts an entity to participating in only one such claim — a person can simultaneously be a colleague, a friend, and a stakeholder in a project, and none of those framings excludes the others. A system that organizes by collection will always be one dimension behind a system that organizes by relationship, because reality is not one-dimensional.

**Every thought is multi-dimensional by default.** No utterance is assumed to belong to a single category. A single remark can simultaneously carry an emotional state, a fact about a relationship, an implicit obligation, and a data point in the ongoing history of a project. Forcing this into one bucket destroys information at the moment of capture. The system must be able to represent one thing said as contributing to several parts of the model at once.

**Observation is not truth.** The system's job is to maintain its best current understanding, not to treat what was said as settled fact. This governs the relationship between the Observation primitive (Section 8) and the derived state of the model: an observation proposes, it does not unilaterally decide.

**Interpretation is not mutation.** A possible reading of something a person said must not, by itself, directly change what the system believes. Between raw observation and accepted understanding there is an interpretive step — a proposal — and that proposal is evaluated against, and combined with, everything else the system already holds before it is allowed to change the model's derived state.

**Knowledge evolves, and may be reinterpreted, not merely appended to.** Human understanding is not append-only. People change their minds, relationships end, plans are reversed. The system must be able to revise the meaning of old information in light of new information — not just add a growing timeline of facts bolted onto one another, but genuinely update what it currently believes while keeping an accurate record of what it believed before and when that belief changed.

**Tasks, reminders, and calendar entries are projections, not primitives.** They are generated views, rendered from the model when it implies an obligation or a moment in time. They are not independently stored objects with their own lifecycle, and the model does not treat their completion or dismissal as itself an act of understanding — it is a rendering decision downstream of what the model already holds.

**LLM output is not the source of truth.** Whatever process interprets raw input and proposes structure over it does not get to decide, by its own authority, what the system now believes. Its proposals are subject to the same evaluation as any other evidence. The system's record of understanding must remain something a person can trust was derived from what they actually said, not from what an interpreting process merely inferred and asserted unchallenged.

---

## 5. Reality Model Definition

The Reality Model is the structured, queryable representation of the user's world that Zehn maintains and continuously updates. It is composed of Entities and Relationships (Sections 7, 9), whose current, derived state is built from the accumulated body of Observations (Section 8) the system has received.

The Reality Model is not a store of things the user said. It is the system's current best understanding of what those things mean about the user's world — an understanding that is always re-derivable from the full history of Observations, always revisable by new ones, and never flatly equivalent to any single Observation taken on its own.

Two distinctions are foundational to this definition and must never collapse into one another:

**Observation versus Reality.** What a person says is not automatically accepted as fact. The system must separate *what was observed* from *what is currently accepted as the system's understanding of reality.* A statement is evidence bearing on the model; it is not, merely by having been said, equivalent to the model's current belief.

**Proposal versus Assertion.** An interpretation of what was said — a candidate reading, a possible extracted meaning — is a proposal. It does not, by existing, change the model. Only once a proposal has been evaluated against the model's existing state does it become (or fail to become) an accepted change to what the system currently holds to be true. This separation is what allows the system to absorb ambiguous, contradictory, or mistaken input without corrupting its own understanding on the strength of a single, possibly wrong, interpretation.

---

## 6. Core Primitive Types

Three primitives compose the Reality Model: Entity, Observation, and Relationship. Every other concept the system uses — tasks, reminders, confidence, evolving belief — is a pattern of composition over these three, not an additional primitive in disguise. A new primitive is admitted only when representing something genuinely requires one that cannot be expressed through composition of the existing three; the default assumption is that it can.

---

## 7. Entity Model

**What an Entity represents.** An Entity is a persistent point of reference in the user's world — a person, a place, a project, an organization, an idea, a commitment, an event — something the model needs to be able to recognize as "the same one" across many separate observations, potentially separated by arbitrary time. An Entity is not defined by what kind of thing it is; it is defined by the fact that it can be pointed at consistently over time. It holds no facts about itself directly — everything actually known about it lives in the Observations and Relationships that reference it, not inside the Entity itself.

**Why entities have identity.** Without a stable anchor, every mention of a person or project would be a disconnected reference, and nothing in the system could recognize that two separate things said at two separate times were about the same subject. The Entity exists specifically to carry that recognition forward, so that what is learned at one moment can be combined with what is learned at another.

**Why identity continuity matters.** An Entity's identity is opaque and independent of its current properties. A person who changes names, roles, and relationship to the user entirely must remain the same Entity, because identity tracks "this is the same point of reference," not any particular description of it at a given moment. If identity were derived from current properties, the model would lose the ability to recognize continuity through change — which is precisely the kind of evolution a person's real relationships, projects, and circumstances undergo constantly. An Entity, once created, is not deleted as a consequence of the world changing around it; it simply accumulates no further Observations, and the relationships touching it may be revised or superseded.

---

## 8. Observation Model

**Observation as raw evidence, not truth.** An Observation is a record of something communicated — in the current version, spoken — at a specific point in time. It is the sole entry point through which new information enters the model; there is no other way for the model to change. An Observation proposes; it does not, by itself, decide what the system now believes. A single Observation is one data point, evaluated alongside everything else the system already holds, not an authoritative instruction to update the model however it says.

**Why observations are immutable.** An Observation, once captured, is never edited. If it could be, the system would lose the ability to distinguish what was actually said from what is currently believed — the exact distinction the Reality Model depends on (Section 5). Correction works by adding new Observations that outweigh or supersede earlier ones in the model's derived understanding, never by rewriting the record of what was previously said. This preserves the system's ability to reconstruct, at any point, both what the person actually communicated and how the system's understanding of it changed over time.

**Why observation is not equal to truth.** Treating a spoken statement as automatically true would mean the system inherits every misstatement, misremembering, or change of mind as a permanent fact rather than as evidence to be weighed. The Reality Model's entire capacity to hold a confidence-weighted, revisable understanding — rather than a flat transcript treated as a ledger of facts — depends on Observation being evidence first, and only becoming part of the system's accepted understanding once evaluated.

---

## 9. Relationship Model

**Relationships as first-class citizens.** A Relationship is a claim that two Entities are connected in some specific way. It is not a container for arbitrary unrelated facts; it holds one claim about how its two endpoints relate. Relationships are not an auxiliary structure layered on top of a more fundamental list of entities — they are as important as the entities themselves, because the connective tissue between things is what distinguishes a model of the user's world from a mere inventory of things in it.

**Why connections between entities matter.** The value of the model compounds specifically because observations connect to shared structure rather than accumulating as isolated entries. An isolated fact about one entity, with no connection to anything else, is close to what a note-taking app already handles adequately. A fact that touches an existing person, project, or place — and is retrievable through that connection later, in a context nobody explicitly asked to preserve — is what a Reality Model is for. Nothing in this model restricts a given pair of Entities to a single connecting claim: an Entity can simultaneously be connected to others through several distinct, concurrently true Relationships, because that is how the user's actual world is shaped.

**Why a graph representation is necessary.** A collection-based organization (folders, tags, lists) can only place a thing in one grouping at a time, imposed after the fact. A graph representation allows an Entity to participate in an unbounded number of Relationships simultaneously, and allows traversal from one Entity to another through those Relationships — which is the mechanism by which the system can answer a question that requires connecting two things the person never explicitly connected themselves. This is the specific capability a document or collection model cannot provide, and it is why Relationship is admitted as a primitive in its own right rather than treated as a property of an Entity.

---

## 10. Knowledge Evolution

Reality is not append-only, and the system's understanding of it is not either — but the record of Observations the system has received *is* append-only (Section 8). These two statements work together, not against each other.

**Reinterpretation.** When a new Observation changes what a set of prior Observations is understood to mean, the system updates its current derived understanding while every prior Observation remains exactly as it was recorded. The historical fact that the system once believed something remains true and reconstructable; only the present understanding changes. This is distinct from simply adding a new fact — it is the mechanism by which the system can genuinely revise what it believes, not merely accumulate an ever-growing list of statements.

**Contradiction.** Two Observations that assert incompatible things about the same subject are an ordinary, expected condition, not an error state. The system holds both and lets its current derived understanding reflect the tension, rather than silently discarding one side or forcing a resolution the evidence does not actually support.

**Superseding.** A later Observation that directly indicates an earlier claim no longer holds does not delete the earlier Relationship or fact — it closes its currency and, where applicable, establishes a new state. "This used to be true" remains a real, retained fact about the model's history, not an absence of fact.

**Confidence.** Every accepted understanding and Relationship the system holds carries a confidence level, reflecting how sure the system currently is, and that confidence is not discarded once a fact is stored — it persists, moves as corroborating or contradicting Observations arrive, and remains inspectable. A fact the system is only weakly sure of must never be presented, stored, or acted upon identically to one confirmed repeatedly by the person themselves. This is required precisely because Observation is not truth (Section 8): without uncertainty and confidence must remain representable in the model and must not be lost when evidence changes, the system would have no way to represent the difference between a single uncorroborated remark and a repeatedly confirmed understanding.

**Historical evidence remains distinguishable from current state.** The system's present understanding of something and the full history of Observations and belief-states that produced it are two different things, and the architecture must keep both available: what the system currently believes, and the complete, reconstructable trail of what it believed before and why it changed. Losing either breaks a different part of the system — losing the former leaves nothing to act on; losing the latter makes reinterpretation indistinguishable from arbitrary, untraceable change.

---

## 11. Identity and Continuity

Identity and continuity are properties of Entities, not of Observations or Relationships, and they are governed entirely by Section 7's account of what an Entity is: an opaque, stable point of reference, independent of its current properties.

This has a direct consequence for how the model absorbs new information about something it already knows. Because identity does not derive from current properties, a change to a person's role, a project's scope, or an organization's structure never requires creating a new Entity merely because the description of it changed. What changes is the content of the Observations and Relationships attached to that Entity — the underlying anchor persists. Continuity, in this model, is the default; replacing an Entity's identity entirely is the exception, reserved for correcting a case where the system's own prior anchoring was mistaken, not for representing that the real-world referent has changed.

---

## 12. Invariants

The following must hold in any implementation of this architecture, regardless of underlying technology:

1. **Observations are immutable.** Once captured, an Observation is never edited. Correction occurs through new Observations, never by rewriting history.
2. **Reality changes through accepted assertions, not raw observation.** A statement entering the system is evidence; it becomes part of the model's accepted understanding only once evaluated against what the system already holds, never automatically on arrival.
3. **LLM output is not the source of truth.** Interpretations proposed by whatever process extracts meaning from an Observation are proposals, subject to evaluation, not unilateral authority to change the model.
4. **Relationships are as important as entities.** The graph of connections between Entities is not a secondary structure; it is, together with Entities, the composition of the Reality Model itself.
5. **The system models reality; it does not store conversations.** Raw transcripts or chat history are not the system's memory. What the system retains as its memory is the structured, derived understanding built from Observations — Observations themselves are retained as the evidentiary record behind that understanding, not as a conversational log to be replayed.
6. **Historical evidence must remain distinguishable from current state.** The system's present belief and the record of how that belief was formed and has changed over time are both retained, and are never collapsed into a single undifferentiated store.
7. **Every Entity has a stable, opaque identity**, independent of its current properties, established once and preserved through change (Sections 7, 11).
8. **Tasks and similar projections are not primitives.** They are generated from the model's current state and are not themselves the system's fundamental representation of anything.

---

## 13. Rejected Alternatives

**Simple note storage.** A system that stores what a person says as discrete, filed entries solves a retrieval problem, not the relational problem Zehn exists to solve (Section 3). It has no mechanism for recognizing that two notes concern the same underlying subject unless a person manually connects them, which reintroduces exactly the manual categorization burden the system exists to remove.

**Chat history as memory.** Treating a conversational log as the system's memory conflates the raw record of what was said with the system's understanding of what it means. It provides no derived, queryable model of the user's world — only a transcript a person or process would have to re-read and re-interpret every time a question is asked. This also makes reinterpretation (Section 10) effectively impossible: a transcript has no current belief to revise, only a sequence of past statements.

**Direct LLM-controlled state mutation.** Allowing an interpreting process to write directly to the model's accepted state, without the proposal-versus-assertion separation (Section 5), would make the system's understanding only as reliable as a single inference pass, with no mechanism for weighing that inference against corroborating or contradicting evidence, and no way to distinguish a correct update from a confidently wrong one. This directly contradicts the invariant that LLM output is not the source of truth (Section 12).

**Flat task lists as the main model.** Representing the system primarily as a list of obligations collapses the multi-dimensional nature of what a person actually communicates (Section 4) down to a single category — actionable items — and discards everything else a statement might carry: an emotional state, a fact about a relationship, a piece of an evolving idea. It also reintroduces tasks as a primary, independently maintained object rather than a projection, which this architecture explicitly rejects (Section 12, Invariant 8).

---

## 14. Relationship With Other RFCs

This document establishes the three core primitives — Entity, Observation, Relationship — and the distinctions (Observation versus Reality, Proposal versus Assertion, Projection versus primitive) that govern how they behave. It does not itself define the detailed semantic rules of how interpretation decomposes an Observation into evaluable claims, how those claims earn or lose confidence over time, how provenance and attribution are preserved, or the full lifecycle rules governing Entity creation, identity resolution, merging, and splitting. Those are the subject of the semantic, evidentiary, and identity-focused constitutional documents that build directly on this one, and which do not redefine any primitive established here.

Later architectural work has also produced a more detailed constitutional treatment of the Entity and Relationship primitives specifically — including stricter rules on Entity attribute ownership, Relationship identity and minimality, and the mechanics by which a model generates a deterministic, context-scoped view of itself for querying. That work operates entirely within the vocabulary this document establishes: an Entity remains a persistent, opaque anchor holding no facts of its own; a Relationship remains a connective structure whose meaning is carried by what is asserted about it, not by properties of its own; and a generated, queryable rendering of the model's current state remains a projection, never an independently authoritative object. Where later documents introduce additional terms for concepts already defined here, those terms name the same underlying concepts this document establishes and do not alter them.

---

## 15. Current Implementation Status

This document defines the foundational conceptual model of Zehn.

Subsequent RFCs may refine the semantics, evidence model, identity rules, assertion lifecycle, and implementation constraints while preserving the primitives and invariants established here.

This document remains the architectural foundation of the system.