"""
reality/provider_errors.py

Neutral failure taxonomy for provider capabilities (RFC-004 section 13, A10).

A ProviderError means "a provider capability failed". It is deliberately not
part of any pipeline's own error family: ClassificationError means "the
classification subsystem failed", ExtractionError means "the extraction
subsystem failed", and a provider failure belongs to neither. Both pipelines
let these propagate unchanged so the caller (the orchestrator) can decide
about retry, failover or alerting.

A provider either returns a value (however wrong: the firewall audits it) or
raises one of these. It must never turn a failure into an empty result.

This module imports nothing from the rest of the package, so every layer can
depend on it without depending on another layer.
"""

__all__ = [
    "ProviderError",
    "ProviderUnavailable",
    "ProviderTimeout",
    "ProviderInvalidResponse",
]


class ProviderError(Exception):
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