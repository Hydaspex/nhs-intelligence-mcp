"""Source protocols: the interface between the pure core and concrete data feeds.

The analysis and server layers depend only on these protocols, never on a
specific source. Tests inject in-memory fakes; production wires in the RTT and
My Planned Care adapters. This is the ports-and-adapters boundary reused from
nhs-webscraper, applied to data feeds rather than crawl backends.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nhs_intel.domain import WaitTimePoint


@runtime_checkable
class WaitTimeSource(Protocol):
    """A source of historical wait-time points for a provider and specialty."""

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        """Return all known points for one provider/specialty, in any order.

        An empty list means the source holds no data for that pair; callers must
        handle it rather than assuming at least one point exists.
        """
        ...
