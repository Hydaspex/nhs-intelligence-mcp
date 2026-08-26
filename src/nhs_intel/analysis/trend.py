"""Pure trend analysis over a series of wait-time points.

The one rule worth stating: direction is decided by a dead-band, not by the sign
of the delta alone. A one-week wobble on a fifty-week wait is noise, not a trend,
so a change is only called improving or worsening once it clears a relative
threshold. This mirrors the dead-band labelling used in the MRR project, for the
same reason: to stop the metric reporting every small movement as a signal.
"""

from __future__ import annotations

from collections.abc import Iterable

from nhs_intel.domain import Trend, TrendResult, WaitTimePoint

# A change smaller than this fraction of the starting wait is treated as flat.
DEFAULT_DEAD_BAND = 0.05


def compute_trend(
    points: Iterable[WaitTimePoint],
    dead_band: float = DEFAULT_DEAD_BAND,
) -> TrendResult:
    """Summarise a series of wait-time points as a single trend.

    Points are sorted by ``as_of`` before comparison, so callers need not pre-sort.
    The delta is ``end.weeks - start.weeks``: positive means waits grew (worsening).

    Raises:
        ValueError: if fewer than two points are supplied, or the points are not
            all for the same provider and specialty.
    """
    ordered = tuple(sorted(points, key=lambda p: p.as_of))
    if len(ordered) < 2:
        raise ValueError("a trend needs at least two points")

    providers = {p.provider_code for p in ordered}
    specialties = {p.specialty for p in ordered}
    if len(providers) != 1 or len(specialties) != 1:
        raise ValueError(
            "all points must share one provider_code and specialty; "
            f"got providers={providers}, specialties={specialties}"
        )

    start, end = ordered[0], ordered[-1]
    delta = end.weeks - start.weeks
    pct = (delta / start.weeks) if start.weeks > 0 else None

    direction = _classify(delta, start.weeks, dead_band)

    return TrendResult(
        provider_code=start.provider_code,
        specialty=start.specialty,
        start=start,
        end=end,
        delta_weeks=delta,
        pct_change=pct,
        direction=direction,
        series=ordered,
    )


def _classify(delta: float, base: float, dead_band: float) -> Trend:
    """Direction of a change, treating sub-threshold moves as flat."""
    # When the baseline is zero, any increase is worsening and no change is flat;
    # a relative dead-band is undefined, so fall back to the raw sign.
    if base == 0:
        if delta > 0:
            return Trend.WORSENING
        return Trend.FLAT

    if abs(delta) < dead_band * base:
        return Trend.FLAT
    return Trend.WORSENING if delta > 0 else Trend.IMPROVING
