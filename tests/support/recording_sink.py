"""
tests/support/recording_sink.py

Audit sink for tests: keeps every DroppedClaim it receives, in order, as the
very same objects.
"""

from reality.extraction.contracts import DroppedClaim

__all__ = ["RecordingSink"]


class RecordingSink:
    def __init__(self) -> None:
        self.drops: list[DroppedClaim] = []

    def record(self, drop: DroppedClaim) -> None:
        self.drops.append(drop)