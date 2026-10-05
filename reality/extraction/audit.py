"""
reality/extraction/audit.py

Defines the audit sink interface for the extraction pipeline.

``reality.extraction.pipeline.extract()`` receives a sink by explicit
injection and calls ``sink.record(drop)`` for every dropped claim produced
during normalization or validation. There is no module-level registration
and no default: the caller always chooses the sink (RFC-004 A8). Passing
``NullAuditSink`` is a deliberate decision to discard audit records, never
something that happens because a sink was forgotten (I-24).

A persistent sink belongs to a later milestone (R2) and owns the decision
about exactly what rejection payload is stored.
"""

from typing import Protocol

from reality.extraction.contracts import DroppedClaim

__all__ = [
    "AuditSink",
    "NullAuditSink",
]


class AuditSink(Protocol):
    """
    Structural interface every audit sink must implement.

    An audit sink receives ``DroppedClaim`` records produced when a claim
    is dropped during normalization or validation. A sink's ``record()``
    method is expected to return ``None`` and, if it raises, the
    exception propagates to the pipeline, which wraps it as an
    ``ExtractionInternalError``.

    Every ``DroppedClaim`` delivered by ``extract()`` carries the persisted
    Observation's id in ``observation_id`` (RFC-004 R2-D1); a sink may rely
    on it being set.
    """

    def record(self, drop: DroppedClaim) -> None:
        """
        Record that a claim was dropped.

        Args:
            drop: The ``DroppedClaim`` describing what was dropped, from
                which stage, and why.
        """
        ...


class NullAuditSink:
    """
    No-op ``AuditSink`` implementation.

    ``record()`` silently ignores every ``DroppedClaim`` it receives. It must
    be passed explicitly: nothing in the pipeline falls back to it.
    """

    def record(self, drop: DroppedClaim) -> None:
        """
        Silently ignore the given ``DroppedClaim``.

        Args:
            drop: The ``DroppedClaim`` to ignore.
        """
        pass