"""Immutable domain models shared across sources, analysis and the server.

No I/O, no third-party imports beyond the standard library: everything here is
a plain value object so the analysis layer can be unit-tested without a network,
a cache, or the MCP runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Any


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

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON-friendly shape returned by MCP tools."""
        return {"weeks": self.weeks, "as_of": self.as_of.isoformat()}


@dataclass(frozen=True)
class CurrentWait:
    """The latest reported wait for a trust/specialty from My Planned Care.

    This is the weekly current-state counterpart to the RTT time series. It is
    keyed on the provider *name* and region, because that is the identity My
    Planned Care publishes; RTT's numeric provider code is a separate scheme,
    reconciled only where the two must meet (the combined trust profile).

    ``weeks`` may be ``None`` when a trust publishes a specialty row but no
    average-wait figure for it, so callers must treat missing figures explicitly
    rather than assuming a number is always present.
    """

    region: str
    provider: str
    specialty: str
    weeks: int | None
    as_of: date | None

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON shape returned by current-state tools."""
        return {
            "region": self.region,
            "provider": self.provider,
            "specialty": self.specialty,
            "weeks": self.weeks,
            "as_of": self.as_of.isoformat() if self.as_of else None,
        }


@dataclass(frozen=True)
class TrustRating:
    """A CQC quality rating for a provider.

    ``overall`` is the headline rating (e.g. "Good", "Requires improvement").
    ``key_questions`` maps each CQC domain (safe, effective, caring, responsive,
    well-led) to its rating, and may be empty if the provider has an overall
    rating but no per-domain breakdown.
    """

    cqc_provider_id: str
    overall: str
    report_date: str | None
    key_questions: Mapping[str, str]

    def __post_init__(self) -> None:
        # Freeze the mapping so a frozen TrustRating cannot be mutated through it.
        object.__setattr__(
            self, "key_questions", MappingProxyType(dict(self.key_questions))
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "cqc_provider_id": self.cqc_provider_id,
            "overall": self.overall,
            "report_date": self.report_date,
            "key_questions": dict(self.key_questions),
        }


@dataclass(frozen=True)
class TrustIdentity:
    """One trust's identity across the three data schemes.

    RTT keys on ``provider_code`` (e.g. "RGT"), My Planned Care on
    ``provider_name`` (e.g. "Guy's and St Thomas'"), CQC on ``cqc_provider_id``.
    A trust missing from the mapping cannot be joined across sources, so the
    combined profile abstains for it.
    """

    provider_code: str
    provider_name: str
    cqc_provider_id: str


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

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the ``found=true`` JSON shape returned by the trend tool.

        This is the single definition of the trend wire format: tools serialise
        by calling this, never by rebuilding the dict inline.
        """
        return {
            "found": True,
            "provider_code": self.provider_code,
            "specialty": self.specialty,
            "start": self.start.to_payload(),
            "end": self.end.to_payload(),
            "delta_weeks": self.delta_weeks,
            "pct_change": self.pct_change,
            "direction": self.direction.value,
            "series": [p.to_payload() for p in self.series],
        }
