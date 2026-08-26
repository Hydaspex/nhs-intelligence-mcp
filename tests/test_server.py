"""Tests for the wait-time trend request handler.

The pure handler ``_trend_payload`` is called directly with an injected fake
source, so these tests need no MCP transport, no environment variable, and no
data file. The MCP tool ``wait_time_trend`` is a one-line wrapper over it.
"""

from __future__ import annotations

from datetime import date

from nhs_intel.domain import WaitTimePoint
from nhs_intel.server import _trend_payload


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
