"""Tests for the combined trust-profile join."""

from __future__ import annotations

from datetime import date

from nhs_intel.analysis import build_trust_profile, compute_trend, unmapped_profile
from nhs_intel.domain import CurrentWait, TrustIdentity, TrustRating, WaitTimePoint

IDENTITY = TrustIdentity("RGT", "Guy's and St Thomas'", "1-101681210")


class FakeWaitSource:
    def __init__(self, points: list[WaitTimePoint]) -> None:
        self._points = points

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        return list(self._points)


class FakeCurrentSource:
    def __init__(self, record: CurrentWait | None) -> None:
        self._record = record

    def latest(self, provider: str, specialty: str) -> CurrentWait | None:
        return self._record

    def for_specialty(self, specialty, region=None):  # unused here
        return []


class FakeRatingSource:
    def __init__(self, rating: TrustRating | None) -> None:
        self._rating = rating

    def rating(self, cqc_provider_id: str) -> TrustRating | None:
        return self._rating


def _points() -> list[WaitTimePoint]:
    return [
        WaitTimePoint("RGT", "Cardiology", 18.0, date(2026, 1, 1)),
        WaitTimePoint("RGT", "Cardiology", 24.0, date(2026, 3, 1)),
    ]


def _full_profile():
    return build_trust_profile(
        identity=IDENTITY,
        specialty="Cardiology",
        wait_source=FakeWaitSource(_points()),
        current_source=FakeCurrentSource(
            CurrentWait("London", "Guy's and St Thomas'", "Cardiology", 14, date(2026, 8, 24))
        ),
        rating_source=FakeRatingSource(
            TrustRating("1-101681210", "Good", "2023-05-01", {"Safe": "Good"})
        ),
        trend_fn=compute_trend,
    )


def test_full_profile_has_all_three_sections():
    profile = _full_profile()
    assert profile["found"] is True
    assert profile["provider_code"] == "RGT"
    assert profile["current"]["weeks"] == 14
    assert profile["trend"]["direction"] == "worsening"
    assert profile["rating"]["overall"] == "Good"


def test_missing_sections_are_none_not_fabricated():
    profile = build_trust_profile(
        identity=IDENTITY,
        specialty="Cardiology",
        wait_source=FakeWaitSource([]),          # no RTT history
        current_source=FakeCurrentSource(None),  # no current wait
        rating_source=FakeRatingSource(None),    # no rating
        trend_fn=compute_trend,
    )
    assert profile["found"] is True
    assert profile["current"] is None
    assert profile["trend"] is None
    assert profile["rating"] is None


def test_single_point_yields_no_trend_section():
    profile = build_trust_profile(
        identity=IDENTITY,
        specialty="Cardiology",
        wait_source=FakeWaitSource([_points()[0]]),  # one point only
        current_source=FakeCurrentSource(None),
        rating_source=FakeRatingSource(None),
        trend_fn=compute_trend,
    )
    assert profile["trend"] is None


def test_unmapped_profile_shape():
    profile = unmapped_profile("ZZZ")
    assert profile["found"] is False
    assert profile["identifier"] == "ZZZ"
    assert "identity mapping" in profile["reason"]
