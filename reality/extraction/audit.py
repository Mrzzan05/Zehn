"""
reality/extraction/audit.py

Owns audit sink lifecycle for the extraction pipeline: which
``AuditSink`` instance is currently active, how it is registered, and how
it is cleared.

``reality.extraction.pipeline.extract()`` consumes this module's
``get_audit_sink()`` function to resolve a sink at the start of each
extraction call, and calls ``sink.record(drop)`` for every dropped claim
produced during normalization or validation. The pipeline must always
receive a usable sink object; it must never receive ``None``. To
guarantee this, ``get_audit_sink()`` returns a built-in no-op sink
(``NullAuditSink``) whenever no sink has been explicitly registered.

This module is responsible for exactly one concern: holding and returning
a reference to the currently active audit sink. It performs no logging
configuration, no persistence, and no dependency injection.
"""

from typing import Optional, Protocol

from reality.extraction.contracts import DroppedClaim

__all__ = [
    "AuditSink",
    "NullAuditSink",
    "get_audit_sink",
    "set_audit_sink",
    "clear_audit_sink",
]


class AuditSink(Protocol):
    """
    Structural interface every audit sink must implement.

    An audit sink receives ``DroppedClaim`` records produced when a claim
    is dropped during normalization or validation. A sink's ``record()``
    method is expected to return ``None`` and, if it raises, the
    exception propagates to the pipeline, which wraps it as an
    ``ExtractionInternalError``.
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

    ``record()`` silently ignores every ``DroppedClaim`` it receives and
    performs no observable work. This is the sink returned by
    ``get_audit_sink()`` whenever no sink has been explicitly registered,
    guaranteeing that the pipeline always has a usable sink to call.
    """

    def record(self, drop: DroppedClaim) -> None:
        """
        Silently ignore the given ``DroppedClaim``.

        Args:
            drop: The ``DroppedClaim`` to ignore.
        """
        pass


_default_sink: AuditSink = NullAuditSink()
_sink: Optional[AuditSink] = None


def get_audit_sink() -> AuditSink:
    """
    Return the currently active audit sink.

    Returns:
        The ``AuditSink`` instance most recently passed to
        ``set_audit_sink()``, or a shared ``NullAuditSink`` instance if
        no sink has been registered. This function never returns
        ``None``.
    """
    if _sink is None:
        return _default_sink
    return _sink


def set_audit_sink(sink: AuditSink) -> None:
    """
    Register ``sink`` as the currently active audit sink.

    Args:
        sink: An ``AuditSink``-conforming instance to register. This
            function does not validate, call, or otherwise inspect the
            sink; it only stores the reference.

    Replaces any previously registered sink.
    """
    global _sink
    _sink = sink


def clear_audit_sink() -> None:
    """
    Clear the currently registered audit sink, if any.

    After this call, ``get_audit_sink()`` reverts to returning the
    default ``NullAuditSink`` instance.
    """
    global _sink
    _sink = None