"""
reality/classification/exceptions.py

Closed exception hierarchy of the classification pipeline.

Two different things can go wrong, and they are kept apart on purpose:

* The provider's OUTPUT is bad (wrong shape, wrong types, forged fields).
  That is a normal outcome of the Semantic Firewall: the payload becomes a
  DroppedProposal in ClassificationResult.dropped. No exception.

* The provider itself FAILED (could not be reached, timed out, ...).
  There is no payload to audit. That is an exception, so it can never be
  confused with "the provider found nothing" (an empty, successful result).
  Retrying, failing over or alerting is a decision for the caller
  (orchestration), not for this layer.

The provider-failure family lives in the neutral module
reality.provider_errors (RFC-004 A10) and is re-exported here, as the same
objects, for compatibility. It is NOT a ClassificationError: a provider
capability failing is not the classification subsystem failing.

Everything the pipeline raises is a ClassificationError or a ProviderError.
"""

from reality.provider_errors import (
    ProviderError,
    ProviderInvalidResponse,
    ProviderTimeout,
    ProviderUnavailable,
)

__all__ = [
    "ClassificationError",
    "ProviderError",
    "ProviderUnavailable",
    "ProviderTimeout",
    "ProviderInvalidResponse",
    "ClassificationInternalError",
]


class ClassificationError(Exception):
    """Base class of every exception raised by the classification subsystem."""


class ClassificationInternalError(ClassificationError):
    """
    Wraps any unexpected exception that is neither a ClassificationError nor
    a declared ProviderError (a bug in a provider, in the normalizer, ...).
    The original exception is chained as ``__cause__``; its message is
    deliberately NOT copied into this one.
    """