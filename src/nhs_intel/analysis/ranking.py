"""Pure ranking of trusts by current wait.

Kept separate from the source so ordering, tie-breaking and missing-figure
handling are unit-testable without any I/O. Trusts that publish a specialty row
but no wait figure are not silently dropped: they are returned after the ranked
trusts, so a caller can see coverage gaps rather than mistake them for absence.
"""

from __future__ import annotations

from collections.abc import Iterable

from nhs_intel.domain import CurrentWait


def rank_by_wait(
    waits: Iterable[CurrentWait], descending: bool = True
) -> list[CurrentWait]:
    """Rank trusts by wait, longest first by default.

    Trusts with a known wait are ordered by ``weeks`` (ties broken by provider
    name for a stable, reproducible order). Trusts with no wait figure follow, in
    provider-name order, so they are visible but never ranked as if zero.
    """
    known = [w for w in waits if w.weeks is not None]
    unknown = [w for w in waits if w.weeks is None]

    # Sort by name first (ascending), then by weeks. Python's sort is stable, so
    # trusts tied on weeks keep the A→Z name order in both directions.
    known.sort(key=lambda w: w.provider)
    known.sort(key=lambda w: w.weeks, reverse=descending)  # weeks is non-None here

    unknown.sort(key=lambda w: w.provider)
    return known + unknown
