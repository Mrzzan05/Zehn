"""
tests/support/fake_provider.py

Deterministic scripted extraction provider for tests.

It obeys the provider contract (RFC-004 section 13) so it can stand in for a
real adapter: it either returns a value or raises a declared failure, it has
no side effects on Reality, and it uses no storage, clock or randomness.

The script is an ordered sequence. Each call consumes exactly one entry:
  * an exception INSTANCE is raised as the very same object;
  * anything else (including deliberately malformed values, None, strings)
    is returned by identity, never validated and never repaired.

Calling the provider more often than its script allows raises
ScriptExhausted, so an accidental extra call (for example an unintended
retry) fails loudly instead of silently reusing an entry.
"""

from typing import Any

from reality.schemas import Observation

__all__ = ["ScriptedProvider", "ScriptExhausted"]


class ScriptExhausted(AssertionError):
    """The provider was called more times than its script has entries."""


class ScriptedProvider:
    def __init__(self, *script: Any) -> None:
        self._script: tuple[Any, ...] = tuple(script)
        self.calls: list[Observation] = []

    def extract(self, observation: Observation) -> Any:
        self.calls.append(observation)
        index = len(self.calls) - 1
        if index >= len(self._script):
            raise ScriptExhausted(
                f"ScriptedProvider called {len(self.calls)} time(s) "
                f"but its script has {len(self._script)} entr(ies)"
            )
        step = self._script[index]
        if isinstance(step, BaseException):
            raise step
        return step