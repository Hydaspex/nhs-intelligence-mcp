"""Tests for the wait-time trend request handler.

The pure handler ``_trend_payload`` is called directly with an injected fake
source, so these tests need no MCP transport, no environment variable, and no
data file. The MCP tool ``wait_time_trend`` is a one-line wrapper over it.
"""

from __future__ import annotations

from datetime import date

from nhs_intel.domain import CurrentWait, WaitTimePoint
from nhs_intel.server import _lookup_payload, _ranking_payload, _trend_payload


class FakeSource:
    """In-memory WaitTimeSource for tests."""

    def __init__(self, points: list[WaitTimePoint]) -> None:
        self._points = points

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        return [
            p
            for p in self._points
            if p.provider_code == provider_code and p.specialty == specialty
        ]


class FakeCurrentSource:
    """In-memory CurrentWaitSource for tests."""

    def __init__(self, records: list[CurrentWait]) -> None:
        self._records = records

    def latest(self, provider: str, specialty: str) -> CurrentWait | None:
        matches = [
            r for r in self._records if r.provider == provider and r.specialty == specialty
        ]
        return matches[0] if matches else None

    def for_specialty(self, specialty: str, region: str | None = None) -> list[CurrentWait]:
        return [
            r
            for r in self._records
            if r.specialty == specialty and (region is None or r.region == region)
        ]


def _series() -> list[WaitTimePoint]:
    return [
        WaitTimePoint("RGT", "Cardiology", 18.4, date(2026, 1, 1)),
        WaitTimePoint("RGT", "Cardiology", 23.7, date(2026, 3, 1)),
    ]


def test_trend_tool_returns_worsening_payload():
    out = _trend_payload("RGT", "Cardiology", FakeSource(_series()))
    assert out["found"] is True
    assert out["direction"] == "worsening"
    assert out["delta_weeks"] == 23.7 - 18.4
    assert len(out["series"]) == 2
    assert out["start"]["as_of"] == "2026-01-01"


def test_trend_tool_reports_not_found_for_unknown_key():
    out = _trend_payload("ZZZ", "Cardiology", FakeSource(_series()))
    assert out["found"] is False
    assert out["reason"] == "no data"


def test_trend_tool_reports_not_found_for_single_point():
    one = [WaitTimePoint("RGT", "Cardiology", 18.4, date(2026, 1, 1))]
    out = _trend_payload("RGT", "Cardiology", FakeSource(one))
    assert out["found"] is False
    assert "one data point" in out["reason"]


def _current() -> list[CurrentWait]:
    return [
        CurrentWait("London", "Guy's", "Cardiology", 14, date(2026, 8, 24)),
        CurrentWait("London", "King's", "Cardiology", 19, date(2026, 8, 24)),
        CurrentWait("North West", "MRI", "Cardiology", 11, date(2026, 8, 24)),
    ]


def test_lookup_tool_returns_current_wait():
    out = _lookup_payload("Guy's", "Cardiology", FakeCurrentSource(_current()))
    assert out["found"] is True
    assert out["weeks"] == 14
    assert out["provider"] == "Guy's"


def test_lookup_tool_not_found():
    out = _lookup_payload("Nowhere", "Cardiology", FakeCurrentSource(_current()))
    assert out["found"] is False
    assert out["reason"] == "no current data"


def test_ranking_tool_orders_longest_first():
    out = _ranking_payload("Cardiology", FakeCurrentSource(_current()))
    assert out["count"] == 3
    assert [t["provider"] for t in out["trusts"]] == ["King's", "Guy's", "MRI"]


def test_ranking_tool_respects_region_and_limit():
    out = _ranking_payload(
        "Cardiology", FakeCurrentSource(_current()), region="London", limit=1
    )
    assert out["region"] == "London"
    assert out["count"] == 1
    assert out["trusts"][0]["provider"] == "King's"
