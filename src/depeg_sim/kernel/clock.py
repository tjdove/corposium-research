"""Discrete simulation clock.

The clock counts steps; wall time is derived, never tracked separately, so
``elapsed_seconds == step_index * interval_seconds`` holds by construction.
"""

from __future__ import annotations


class Clock:
    def __init__(self, interval_seconds: int) -> None:
        if interval_seconds <= 0:
            raise ValueError(f"interval_seconds must be > 0, got {interval_seconds}")
        self.interval_seconds = interval_seconds
        self.step_index = 0

    @property
    def elapsed_seconds(self) -> int:
        return self.step_index * self.interval_seconds

    def tick(self) -> None:
        self.step_index += 1
