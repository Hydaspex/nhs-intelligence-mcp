"""Immutable domain models shared across sources, analysis and the server.

No I/O, no third-party imports beyond the standard library: everything here is
a plain value object so the analysis layer can be unit-tested without a network,
a cache, or the MCP runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Trend(str, Enum):
    """Direction of a wait-time change over a window."""

    IMPROVING = "improving"  # waits getting shorter
    WORSENING = "worsening"  # waits getting longer
    FLAT = "flat"            # within the neutral dead-band


@dataclass(frozen=True)
class WaitTimePoint:
    """One measurement of waiting time for a trust/specialty at a point in time.

    ``weeks`` is the reported average wait in weeks. RTT and My Planned Care both
    report in weeks; a source that reports days converts before constructing this.
    """

    provider_code: str
    specialty: str
    weeks: float
    as_of: date

    def __post_init__(self) -> None:
        if self.weeks < 0:
            raise ValueError(f"weeks must be >= 0, got {self.weeks}")


@dataclass(frozen=True)
class TrendResult:
    """Outcome of comparing the earliest and latest points in a series."""

    provider_code: str
    specialty: str
    start: WaitTimePoint
    end: WaitTimePoint
    delta_weeks: float          # end.weeks - start.weeks (positive = worsening)
    pct_change: float | None    # None when the start value is zero
    direction: Trend
    series: tuple[WaitTimePoint, ...]  # full ordered series, earliest first
