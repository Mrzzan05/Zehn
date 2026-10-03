"""
reality/extraction/errors.py

Canonical exception hierarchy for the Zehn extraction pipeline.

This module defines every exception type that ``reality.extraction.pipeline``
raises as part of its own contract. The hierarchy is intentionally closed:
no additional exception types exist, and none may be introduced without
amending the frozen extraction architecture. Every public exception here
corresponds to a reachable execution path.

Exception semantics, as consumed by ``pipeline.extract()``:

- ``ExtractionMalformedOutput``: raised when ``normalize()`` returns a
  ``NormalizationMalformed`` result, i.e. the provider's raw output could
  not structurally be interpreted as a fragment batch at all.
- ``ExtractionInternalError``: raised to wrap any unexpected, non-domain
  exception encountered during orchestration (undeclared provider execution
  errors, audit sink failures, or any other exception that is neither an
  ``ExtractionError`` nor a declared provider failure). Declared provider
  failures (``reality.provider_errors.ProviderError`` and its subclasses)
  are NOT wrapped: they propagate unchanged so a caller can tell an
  unavailable or slow provider from a bug (RFC-004 section 13, A7, A10).
- ``ExtractionError``: the common base class. Callers that wish to catch
  any extraction-domain failure without distinguishing its specific cause
  should catch this class.

The provider is injected into ``extract()``; there is no provider lookup and
therefore no lookup failure (RFC-004 A8, A11).

This module has no dependencies beyond the standard library and defines no
behavior beyond the exception classes themselves.
"""

__all__ = [
    "ExtractionError",
    "ExtractionMalformedOutput",
    "ExtractionInternalError",
]


class ExtractionError(Exception):
    """
    Base class for all extraction-domain exceptions raised by
    ``reality.extraction.pipeline.extract()``.

    Besides this family, ``extract()`` lets exactly two other things
    through: declared provider failures (the ``ProviderError`` family,
    RFC-004 A7) and the ``ValueError`` raised by its preconditions
    (``Observation.id`` is ``None``, or a required collaborator was not
    injected). Callers that need to handle any extraction-domain failure
    uniformly should catch ``ExtractionError``.
    """


class ExtractionMalformedOutput(ExtractionError):
    """
    Raised when a provider's raw output cannot structurally be interpreted
    as a fragment batch at all.

    This corresponds to ``normalize()`` returning a ``NormalizationMalformed``
    result. It is distinct from a single fragment within an otherwise
    recognizable batch failing to normalize, which is not an exception but
    is instead represented as a dropped claim.
    """


class ExtractionInternalError(ExtractionError):
    """
    Raised to wrap any unexpected exception encountered during pipeline
    orchestration that is not already an ``ExtractionError`` and not a
    declared provider failure.

    This includes, but is not limited to: undeclared exceptions raised by a
    provider's ``extract()`` call and exceptions raised by an audit sink's
    ``record()`` call. Wrapping guarantees that no UNDECLARED exception type
    escapes the pipeline; the only non-``ExtractionError`` exceptions a
    caller can observe are the declared ones listed on ``ExtractionError``.
    """