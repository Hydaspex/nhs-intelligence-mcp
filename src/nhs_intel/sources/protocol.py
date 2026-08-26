"""Source protocols: the interface between the pure core and concrete data feeds.

The analysis and server layers depend only on these protocols, never on a
specific source. Tests inject in-memory fakes; production wires in the RTT and
My Planned Care adapters. This is the ports-and-adapters boundary reused from
nhs-webscraper, applied to data feeds rather than crawl backends.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nhs_intel.domain import CurrentWait, WaitTimePoint


@runtime_checkable
class WaitTimeSource(Protocol):
    """A source of historical wait-time points for a provider and specialty."""

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        """Return all known points for one provider/specialty, in any order.

        An empty list means the source holds no data for that pair; callers must
        handle it rather than assuming at least one point exists.
        """
        ...


@runtime_checkable
class CurrentWaitSource(Protocol):
    """A source of latest (current-state) waits, keyed on provider name."""

    def latest(self, provider: str, specialty: str) -> CurrentWait | None:
        """Return the latest wait for one provider/specialty, or None if unknown."""
        ...

    def for_specialty(self, specialty: str, region: str | None = None) -> list[CurrentWait]:
        """Return every trust's latest wait for a specialty, optionally by region.

        Used to rank trusts. The list is unordered; ranking is the caller's job.
        """
        ...
