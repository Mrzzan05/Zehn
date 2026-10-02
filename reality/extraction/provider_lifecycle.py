"""
reality/extraction/provider_lifecycle.py

Owns provider lifecycle for the extraction pipeline: which ``Provider``
instance is currently active, how it is registered, and how it is
cleared.

This module is responsible for exactly one concern: holding and returning
a reference to the currently active provider. It performs no provider
creation, no provider discovery, and no dependency injection; the only
state it maintains is the single, currently registered provider
reference.

``reality.extraction.pipeline.extract()`` consumes this module's
``get_provider()`` function to resolve a provider at the start of each
extraction call. It never constructs, defaults, or caches a provider
itself.
"""

from typing import Optional

from reality.extraction.errors import ExtractionProviderUnavailable
from reality.extraction.provider import Provider

__all__ = ["set_provider", "get_provider", "clear_provider"]

_provider: Optional[Provider] = None


def set_provider(provider: Provider) -> None:
    """
    Register ``provider`` as the currently active provider.

    Args:
        provider: A ``Provider``-conforming instance to register. This
            function does not validate, call, or otherwise inspect the
            provider; it only stores the reference.

    Replaces any previously registered provider.
    """
    global _provider
    _provider = provider


def clear_provider() -> None:
    """
    Clear the currently registered provider, if any.

    After this call, ``get_provider()`` will raise
    ``ExtractionProviderUnavailable`` until ``set_provider()`` is called
    again.
    """
    global _provider
    _provider = None


def get_provider() -> Provider:
    """
    Return the currently active provider.

    Returns:
        The ``Provider`` instance most recently passed to
        ``set_provider()``.

    Raises:
        ExtractionProviderUnavailable: If no provider has been registered
            (i.e. no ``set_provider()`` call has occurred, or the
            registered provider was subsequently cleared via
            ``clear_provider()``).
    """
    if _provider is None:
        raise ExtractionProviderUnavailable("No provider has been registered.")
    return _provider