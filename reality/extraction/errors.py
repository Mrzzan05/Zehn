"""
reality/extraction/errors.py

Canonical exception hierarchy for the Zehn extraction pipeline.

This module defines every exception type that ``reality.extraction.pipeline``
is permitted to raise as part of its orchestration contract. The hierarchy
is intentionally closed: no additional exception types exist, and none may
be introduced without amending the frozen extraction architecture.

Exception semantics, as consumed by ``pipeline.extract()``:

- ``ExtractionProviderUnavailable``: raised when no usable provider can be
  resolved (either no provider has been registered, or provider resolution
  itself fails).
- ``ExtractionMalformedOutput``: raised when ``normalize()`` returns a
  ``NormalizationMalformed`` result, i.e. the provider's raw output could
  not structurally be interpreted as a fragment batch at all.
- ``ExtractionInternalError``: raised to wrap any unexpected, non-domain
  exception encountered during orchestration (provider execution errors,
  audit sink failures, or any other exception not already an
  ``ExtractionError``), so that callers of ``extract()`` only ever observe
  a member of this hierarchy.
- ``ExtractionError``: the common base class. Callers that wish to catch
  any extraction-domain failure without distinguishing its specific cause
  should catch this class.

This module has no dependencies beyond the standard library and defines no
behavior beyond the exception classes themselves.
"""

__all__ = [
    "ExtractionError",
    "ExtractionProviderUnavailable",
    "ExtractionMalformedOutput",
    "ExtractionInternalError",
]


class ExtractionError(Exception):
    """
    Base class for all exceptions raised by the extraction pipeline.

    Every exception raised by ``reality.extraction.pipeline.extract()`` is
    an instance of this class. Callers that need to handle any extraction
    failure uniformly, without branching on its specific cause, should
    catch ``ExtractionError``.
    """


class ExtractionProviderUnavailable(ExtractionError):
    """
    Raised when no usable provider is available to service an extraction
    request.

    This covers both of the following situations, which are treated
    identically by the pipeline:

    - No provider has ever been registered via
      ``reality.extraction.provider_lifecycle.set_provider``.
    - Provider resolution was attempted but could not produce a usable
      provider instance.
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
    orchestration that is not already an ``ExtractionError``.

    This includes, but is not limited to: exceptions raised by a
    provider's ``extract()`` call, exceptions raised while resolving a
    provider, and exceptions raised by an audit sink's ``record()`` call.
    Wrapping guarantees that callers of ``extract()`` never observe a
    non-``ExtractionError`` exception type escaping the pipeline.
    """