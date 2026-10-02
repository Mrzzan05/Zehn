"""
reality/extraction/provider.py

Defines the structural interface (``Protocol``) that every extraction
provider must satisfy.

``reality.extraction.pipeline.extract()`` resolves a provider via
``reality.extraction.provider_lifecycle.get_provider()`` and then calls::

    raw_output = provider.extract(observation)

Accordingly, the ``Provider`` protocol below exposes exactly one method,
``extract(self, observation)``, matching that call site precisely. The
returned value is passed directly to
``reality.extraction.normalization.normalize()``, whose parameter is typed
as ``Any``; this protocol's return type is therefore also ``Any``, since
the concrete shape of a provider's raw output is not standardized at this
layer.

This module defines the interface only. No concrete provider
implementation exists here or anywhere in this package.
"""

from typing import Any, Protocol, runtime_checkable

from reality.schemas import Observation

__all__ = ["Provider"]


@runtime_checkable
class Provider(Protocol):
    """
    Structural interface every extraction provider must implement.

    A conforming provider accepts a single ``Observation`` and returns its
    raw, provider-specific output. A provider must not resolve entities,
    must not construct ``Assertion`` objects, and must have no dependency
    on ``reality.engine`` or ``reality.repository``.
    """

    def extract(self, observation: Observation) -> Any:
        """
        Produce raw, provider-specific output for the given ``Observation``.

        Args:
            observation: The ``Observation`` to extract semantic content
                from.

        Returns:
            Raw, provider-specific output. Its shape is opaque to this
            protocol and is interpreted downstream by
            ``reality.extraction.normalization.normalize()``.
        """
        ...