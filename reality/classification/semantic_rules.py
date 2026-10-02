"""
reality/classification/semantic_rules.py

Second stage of the firewall.

    Stage 1  normalization.py     SCHEMA firewall   - is the payload well-formed?
    Stage 2  semantic_rules.py    SEMANTIC firewall - does a well-formed proposal
                                                      make sense?

Rules inspect an already-valid SemanticProposal. They never repair, infer or
rewrite it: a proposal either passes untouched or is moved to `dropped` with
every violated rule listed (not just the first).

Scope. Only invariants that hold regardless of domain policy live here.
Thresholds on classifier confidence (e.g. "drop Beliefs under 0.5") are NOT
rules: classification_confidence is the classifier's mechanical certainty, not
the truth of the claim, so a cut-off on it is a policy decision for the
caller. Likewise "a Commitment must carry a time" is deliberately not
enforced, because many real commitments have no stated time.

Adding a rule: write a function `(SemanticProposal) -> tuple[ErrorDetail, ...]`,
give it a stable `rule.<name>` type id, add it to RULES, add a test.
"""

from collections import Counter
from typing import Callable, Final

from reality.classification.contracts import (
    MAX_ERROR_DETAILS,
    ClassificationResult,
    DroppedProposal,
    ErrorDetail,
)
from reality.classification.normalization import Clock, create_drop, utc_now
from reality.classification.schemas import SemanticProposal

__all__ = ["RULES", "check_proposal", "apply_semantic_rules"]

RuleCheck = Callable[[SemanticProposal], tuple[ErrorDetail, ...]]

# Types for which "what is it about?" is part of the meaning.
OBJECT_REQUIRED_TYPES: Final = frozenset({"Goal", "Preference"})


def _blank(text: str) -> bool:
    return not text.strip()


def _violation(rule: str, loc: tuple[str | int, ...], msg: str) -> ErrorDetail:
    return ErrorDetail(type=f"rule.{rule}", loc=loc, msg=msg)


def _rule_predicate(p: SemanticProposal) -> tuple[ErrorDetail, ...]:
    # Schema min_length counts whitespace, so "   " passes the firewall.
    if _blank(p.predicate):
        return (_violation("predicate_blank", ("predicate",), "predicate must not be blank"),)
    return ()


def _rule_object_text(p: SemanticProposal) -> tuple[ErrorDetail, ...]:
    if p.object_text is None:
        if p.semantic_type in OBJECT_REQUIRED_TYPES:
            return (
                _violation(
                    "object_required",
                    ("object_text",),
                    f"{p.semantic_type} proposals require object_text",
                ),
            )
        return ()
    if _blank(p.object_text):
        return (_violation("object_blank", ("object_text",), "object_text must not be blank"),)
    return ()


def _rule_descriptor(p: SemanticProposal) -> tuple[ErrorDetail, ...]:
    descriptor = p.candidate_subject_descriptor
    if descriptor is None:
        return ()

    base = ("candidate_subject_descriptor",)
    found: list[ErrorDetail] = []

    if _blank(descriptor.label):
        found.append(_violation("label_blank", base + ("label",), "label must not be blank"))

    attributes = ("candidate_subject_descriptor", "attributes")
    if any(_blank(a.key) or _blank(a.value) for a in descriptor.attributes):
        found.append(
            _violation("attribute_blank", attributes, "attribute key and value must not be blank")
        )
    keys = Counter(a.key for a in descriptor.attributes)
    if any(count > 1 for count in keys.values()):
        found.append(_violation("attribute_duplicate", attributes, "duplicate attribute key"))

    return tuple(found)


def _rule_temporal_markers(p: SemanticProposal) -> tuple[ErrorDetail, ...]:
    found: list[ErrorDetail] = []

    if any(_blank(m.value) for m in p.temporal_markers):
        found.append(
            _violation("temporal_value_blank", ("temporal_markers",), "temporal value must not be blank")
        )
    labels = Counter(m.label for m in p.temporal_markers)
    if any(count > 1 for count in labels.values()):
        found.append(
            _violation("temporal_label_duplicate", ("temporal_markers",), "duplicate temporal label")
        )

    return tuple(found)


RULES: Final[tuple[RuleCheck, ...]] = (
    _rule_predicate,
    _rule_object_text,
    _rule_descriptor,
    _rule_temporal_markers,
)


def check_proposal(proposal: SemanticProposal) -> tuple[ErrorDetail, ...]:
    """Every violated rule, in a stable order. Empty tuple means the proposal passes."""
    return tuple(v for rule in RULES for v in rule(proposal))


def apply_semantic_rules(
    result: ClassificationResult, *, clock: Clock = utc_now
) -> ClassificationResult:
    """
    Move proposals that violate a rule from `accepted` to `dropped`.

    Existing drops are kept first, in order. Accepted proposals that pass are
    returned unchanged (same objects). The input result is not modified.
    """
    accepted: list[SemanticProposal] = []
    dropped: list[DroppedProposal] = list(result.dropped)

    for proposal in result.accepted:
        violations = check_proposal(proposal)
        if not violations:
            accepted.append(proposal)
            continue

        kept = violations[:MAX_ERROR_DETAILS]
        dropped.append(
            create_drop(
                proposal.model_dump(mode="json"),
                "SEMANTIC_RULE_VIOLATION",
                clock,
                details=kept,
                details_omitted=len(violations) - len(kept),
            )
        )

    return ClassificationResult(accepted=tuple(accepted), dropped=tuple(dropped))
