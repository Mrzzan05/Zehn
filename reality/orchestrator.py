"""
reality/orchestrator.py

Sequencing of one Observation through the structural path (RFC-004 section
10, R1):

    intake -> provider -> extraction -> Engine

The orchestrator is a sequencer, not a semantic authority. It makes no
semantic decision and has no storage access: it imports only the public entry
points of the Engine and of extraction, never the repository or the
database. It never owns a transaction spanning provider execution: intake and
every Assertion run in the Engine's own transactions, and the provider is
called while none is open (I-17, I-18).

Contract
--------
* Intake: the Observation is persisted first, in its own transaction, so
  history exists whatever happens downstream.
* Retry: ONLY ProviderTimeout and ProviderUnavailable (and subclasses) are
  retried, immediately, up to ``max_attempts`` attempts in total (default 2).
  Every other failure is terminal and propagates unchanged. When the attempts
  run out, the last provider error is raised unchanged (I-25).
* Ordering: extract() completes in full before the first process_assertion
  call. No interleaving, no streaming, no incremental Engine writes.
* Batch: Assertions are processed one at a time, in provider order, each in
  its own Engine transaction. Validation rejections never reach the Engine
  (they are audited drops), so they do not interrupt the batch. ANY exception
  from the Engine aborts the remaining batch and propagates unchanged.
* Result: a returned OrchestrationResult always represents a COMPLETED
  orchestration (RFC-004 section 6, R1 decision D8). There is no partial-
  success object and no failure field. After a failure, whatever the Engine
  already applied is durable in Reality and is inspected by querying it.

Known limitations (RFC-004 Appendix B / R1 plan section 8): a failed run
leaves its Observation persisted and the caller does not receive its id, so
re-submitting the same text creates a new Observation; and the outcomes hold
the Engine's own, mutable AssertionResult objects, so the result is
immutable only at its own level.
"""

from dataclasses import dataclass

from reality.engine import AssertionResult, process_assertion, process_observation
from reality.extraction.audit import AuditSink
from reality.extraction.contracts import DroppedClaim
from reality.extraction.pipeline import extract
from reality.extraction.provider import Provider
from reality.provider_errors import ProviderTimeout, ProviderUnavailable
from reality.schemas import Observation

__all__ = ["DEFAULT_MAX_ATTEMPTS", "OrchestrationResult", "ingest_observation"]

DEFAULT_MAX_ATTEMPTS = 2

# Retry is expressed positively: exactly these failure kinds are transient.
# Anything else, including every other ProviderError, is terminal.
_RETRYABLE = (ProviderTimeout, ProviderUnavailable)


@dataclass(frozen=True)
class OrchestrationResult:
    """The outcome of a COMPLETED orchestration."""

    observation: Observation
    outcomes: tuple[AssertionResult, ...]
    normalization_drops: int
    validation_drops: int
    provider_attempts: int


class _CountingSink:
    """
    Forwards every drop, unchanged and in order, to the injected sink, and
    counts it by stage. Counting happens only after the inner sink accepted
    the record, so a failing sink never produces a count.

    Retried attempts cannot inflate the counts: a retryable failure is raised
    by the provider call itself, before normalization produces any drop.
    """

    def __init__(self, inner: AuditSink) -> None:
        self._inner = inner
        self.normalization_drops = 0
        self.validation_drops = 0

    def record(self, drop: DroppedClaim) -> None:
        self._inner.record(drop)
        if drop.stage == "normalization":
            self.normalization_drops += 1
        elif drop.stage == "validation":
            self.validation_drops += 1


def ingest_observation(
    observation: Observation,
    *,
    provider: Provider,
    audit_sink: AuditSink,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> OrchestrationResult:
    """
    Run one UNPERSISTED Observation through intake, provider, extraction and
    the Engine. The provider and the audit sink are required and keyword-only
    (RFC-004 A8, A11); ``max_attempts`` is the TOTAL number of provider
    attempts, not the number of retries.
    """
    # Preconditions: checked before any side effect.
    if observation.id is not None:
        raise ValueError(
            "Observation is already persisted; the orchestrator persists it "
            "itself and requires an unpersisted Observation."
        )
    if provider is None:
        raise ValueError("provider must be injected explicitly (got None).")
    if audit_sink is None:
        raise ValueError("audit_sink must be injected explicitly (got None).")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    # 1. Intake: its own transaction, before the provider is ever called.
    persisted = process_observation(observation)

    # 2. Extraction, with bounded retry of transient provider failures only.
    counting_sink = _CountingSink(audit_sink)
    attempts = 0
    while True:
        attempts += 1
        try:
            assertions = extract(persisted, provider=provider, audit_sink=counting_sink)
            break
        except _RETRYABLE:
            if attempts >= max_attempts:
                raise  # the last provider error, unchanged

    # 3. Engine: only now, and one Assertion per transaction. Any exception
    #    propagates unchanged and aborts the rest of the batch.
    outcomes: list[AssertionResult] = []
    for assertion in assertions:
        outcomes.append(process_assertion(assertion))

    return OrchestrationResult(
        observation=persisted,
        outcomes=tuple(outcomes),
        normalization_drops=counting_sink.normalization_drops,
        validation_drops=counting_sink.validation_drops,
        provider_attempts=attempts,
    )