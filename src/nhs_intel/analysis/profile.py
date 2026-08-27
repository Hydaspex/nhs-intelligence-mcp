"""Combined trust profile: the join across the three data sources.

Identity is resolved by the caller from the mapping; this module never guesses a
join. Each section (current wait, trend, rating) is included only when its source
holds data for the trust, and omitted otherwise. Pure orchestration over injected
sources and a trend function, so it is unit-tested with fakes and no I/O.
"""

from __future__ import annotations

from collections.abc import Callable

from nhs_intel.domain import CurrentWait, TrendResult, TrustIdentity, WaitTimePoint
from nhs_intel.sources.protocol import (
    CurrentWaitSource,
    WaitTimeSource,
)

# analysis.trend.compute_trend, injected to keep this module pure.
TrendFn = Callable[[list[WaitTimePoint]], TrendResult]


def build_trust_profile(
    identity: TrustIdentity,
    specialty: str,
    wait_source: WaitTimeSource,
    current_source: CurrentWaitSource,
    trend_fn: TrendFn,
) -> dict[str, object]:
    """Assemble a profile for one resolved trust and specialty.

    Each section is ``None`` when its source holds no data for the trust.
    """
    return {
        "found": True,
        "provider_code": identity.provider_code,
        "provider_name": identity.provider_name,
        "specialty": specialty,
        "current": _current_section(
            current_source.latest(identity.planned_care_name or identity.provider_name, specialty)
        ),
        "trend": _trend_section(
            wait_source.series(identity.provider_code, specialty), trend_fn
        ),
        "rating": _rating_section(identity),
    }


def unmapped_profile(identifier: str) -> dict[str, object]:
    """Profile for a trust absent from the identity map: no join is attempted."""
    return {
        "found": False,
        "identifier": identifier,
        "reason": "trust not in identity mapping; cannot join across sources",
    }


def _current_section(current: CurrentWait | None) -> dict[str, object] | None:
    return current.to_payload() if current is not None else None


def _trend_section(
    points: list[WaitTimePoint], trend_fn: TrendFn
) -> dict[str, object] | None:
    if len(points) < 2:
        return None
    return trend_fn(points).to_payload()


def _rating_section(identity: TrustIdentity) -> dict[str, object] | None:
    if not identity.overall_rating:
        return None
    return {"overall": identity.overall_rating}
