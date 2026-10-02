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

Everything the pipeline raises is a ClassificationError.
"""

__all__ = [
    "ClassificationError",
    "ProviderError",
    "ProviderUnavailable",
    "ProviderTimeout",
    "ProviderInvalidResponse",
    "ClassificationInternalError",
]


class ClassificationError(Exception):
    """Base class of every exception raised by the classification pipeline."""


class ProviderError(ClassificationError):
    """Base class for failures a provider reports about itself."""


class ProviderUnavailable(ProviderError):
    """The provider could not be reached or refused to serve the request."""


class ProviderTimeout(ProviderError):
    """The provider did not answer within its deadline."""


class ProviderInvalidResponse(ProviderError):
    """
    The provider got a response but could not produce ANY output value from
    it (for example a transport-level envelope it cannot read).

    Do not use this for bad CONTENT. If the provider can hand over a value,
    however wrong, it must return it: the firewall audits it.
    """


class ClassificationInternalError(ClassificationError):
    """
    Wraps any unexpected, non-ClassificationError exception (a bug in a
    provider, in the normalizer, ...). The original exception is chained as
    ``__cause__``; its message is deliberately NOT copied into this one.
    """
