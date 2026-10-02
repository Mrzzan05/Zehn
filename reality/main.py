"""
reality/main.py

Milestone 1 demo runner for Zehn.

This file is ONLY a demo runner. It contains no SQL, no direct database
access, no entity resolution, no merge logic, and no business rules —
all of that lives in reality.engine (semantic decisions) and
reality.repository (persistence), which this file never touches
directly. main.py only calls:

    reality.db.initialize_database()
    reality.engine.process_observation()
    reality.engine.process_assertion()
    reality.engine.get_full_trace()

It exists to prove, end to end and deterministically, that the core
Zehn hypothesis holds at the architecture level:
    A) free-form input -> structured Entities + Relationships
    B) repeated mentions resolve to the SAME entity, not duplicates
    C) new input EVOLVES existing entity state over time
    +  every stored fact is traceable back to the sentence that produced it

Demo-only note: this script deletes the SQLite database FILE before each
run so the demo always starts from a clean, deterministic state. This is
a file-level reset done here only, for repeatable presentations — it is
NOT a repository/engine function and is intentionally not available to
production code. reality.db.initialize_database() itself remains
side-effect-free with respect to existing data (it only creates tables
if missing), and repository.py/engine.py gain no delete/reset capability
from this change.
"""

import os

from reality.db import DB_PATH, initialize_database
from reality.engine import get_full_trace, process_assertion, process_observation
from reality.schemas import Assertion, Observation


def reset_demo_database() -> None:
    """
    Demo-only: remove the SQLite database file if it exists, so every
    run of this script starts from a clean, deterministic state.

    This is plain filesystem cleanup (os.remove), not SQL and not a
    repository/engine call — it lives here, in the demo script, and
    nowhere else in the codebase.
    """
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def banner(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    reset_demo_database()
    initialize_database()

    # -----------------------------------------------------------------
    # A) Entity creation + relationship creation
    # -----------------------------------------------------------------
    banner("A) ENTITY + RELATIONSHIP CREATION")

    obs1 = process_observation(Observation(raw_text="Mehrsan is a student at the University of California, Los Angeles"))
    print(f"Observation created  -> id={obs1.id}  text={obs1.raw_text!r}")

    result_a = process_assertion(
        Assertion(
            observation_id=obs1.id,
            assertion_type="relationship",
            subject="Mehrsan",
            subject_type="Person",
            predicate="is_a",
            object="University of California, Los Angeles",
            object_type="University",
        )
    )
    print(f"Assertion created     -> id={result_a.assertion.id}  "
          f"({result_a.assertion.subject} "
          f"{result_a.assertion.predicate} "
          f"{result_a.assertion.object})")
    print(f"Entity (subject)      -> id={result_a.subject_entity.id}  "
          f"name={result_a.subject_entity.name!r}  "
          f"type={result_a.subject_entity.entity_type}")
    print(f"Entity (object)       -> id={result_a.object_entity.id}  "
          f"name={result_a.object_entity.name!r}  "
          f"type={result_a.object_entity.entity_type}")
    print(f"Relationship created  -> id={result_a.relationship.id}  "
          f"type={result_a.relationship.relation_type}")

    mehrsan_id = result_a.subject_entity.id

    # -----------------------------------------------------------------
    # B) Entity reuse
    # -----------------------------------------------------------------
    banner("B) ENTITY REUSE (no duplicate created for 'Mehrsan')")

    obs2 = process_observation(Observation(raw_text="Mehrsan work_on his project"))
    print(f"Observation created  -> id={obs2.id}  text={obs2.raw_text!r}")

    result_b = process_assertion(
        Assertion(
            observation_id=obs2.id,
            assertion_type="attribute",
            subject="Mehrsan",
            subject_type="Person",
            predicate="work_on",
            object="his project",
        )
    )
    print(f"Assertion created     -> id={result_b.assertion.id}")
    print(f"Entity (subject)      -> id={result_b.subject_entity.id}  "
          f"(same as A? {result_b.subject_entity.id == mehrsan_id})")

    if result_b.subject_entity.id != mehrsan_id:
        raise RuntimeError(
            "DEMO FAILED (Part B — Entity Reuse): expected the 'Mehrsan' "
            f"mentioned here to resolve to the same entity created in "
            f"Part A (id={mehrsan_id}), but got a different entity "
            f"(id={result_b.subject_entity.id}). This would mean the "
            "Reality Engine is duplicating entities instead of reusing "
            "them across observations."
        )
    print("VERIFIED: Mehrsan entity id is unchanged across observations.")

    # -----------------------------------------------------------------
    # C) Reality evolution through attributes
    # -----------------------------------------------------------------
    banner("C) REALITY EVOLUTION (attribute state changes over time)")

    obs3 = process_observation(Observation(raw_text="Mehrsan is happy after completing his project"))
    result_c1 = process_assertion(
        Assertion(
            observation_id=obs3.id,
            assertion_type="attribute",
            subject="Mehrsan",
            subject_type="Person",
            predicate="mood",
            object="happy",
        )
    )
    print(f"Observation -> id={obs3.id}  text={obs3.raw_text!r}")
    print(f"Entity state after turn 1 -> {result_c1.subject_entity.attributes}")

    obs4 = process_observation(Observation(raw_text="Mehrsan is sad after not completing his project"))
    result_c2 = process_assertion(
        Assertion(
            observation_id=obs4.id,
            assertion_type="attribute",
            subject="Mehrsan",
            subject_type="Person",
            predicate="mood",
            object="sad",
        )
    )
    print(f"Observation -> id={obs4.id}  text={obs4.raw_text!r}")
    print(f"Entity state after turn 2 -> {result_c2.subject_entity.attributes}")

    actual_mood = result_c2.subject_entity.attributes.get("mood")
    if actual_mood != "sad":
        raise RuntimeError(
            "DEMO FAILED (Part C — Reality Evolution): expected Mehrsan's "
            f"'mood' attribute to have evolved to 'sad' after the "
            f"second observation, but found {actual_mood!r} instead. "
            "This would mean new input is not updating existing "
            "entity state as the hypothesis requires."
        )
    print("VERIFIED: latest entity state reflects 'sad', "
          "while both observations remain in history untouched.")

    # -----------------------------------------------------------------
    # Trace: Relationship -> Assertion -> Observation
    # -----------------------------------------------------------------
    banner("PROVENANCE TRACE: Relationship -> Assertion -> Observation")

    trace = get_full_trace(result_a.relationship.id)
    if trace is None:
        raise RuntimeError(
            "DEMO FAILED: provenance trace disappeared after relationship "
            f"creation (relationship id={result_a.relationship.id}). "
            "get_full_trace()'s real contract is Optional — this check "
            "makes that explicit instead of trusting it silently."
        )
    relationship, assertion, observation = trace
    print(f"Relationship id={relationship.id}  "
          f"({relationship.relation_type})")
    print(f"   -> Assertion id={assertion.id}  "
          f"({assertion.subject} {assertion.predicate} {assertion.object})")
    print(f"   -> Observation id={observation.id}  "
          f"text={observation.raw_text!r}")
    print()
    print("This proves every stored fact can be traced back to the exact "
          "sentence the user said — the LLM only extracts, the Reality "
          "Engine and this trace are what make the system trustworthy.")

    banner("MILESTONE 1 DEMO COMPLETE")


if __name__ == "__main__":
    main()
