"""Unit tests for the pure trend analysis."""

from __future__ import annotations

from datetime import date

import pytest

from nhs_intel.analysis import compute_trend
from nhs_intel.domain import Trend, WaitTimePoint


def _pt(weeks: float, month: int, provider: str = "RGT", specialty: str = "Cardiology"):
    return WaitTimePoint(provider, specialty, weeks, date(2026, month, 1))


def test_worsening_when_wait_grows_beyond_dead_band():
    result = compute_trend([_pt(18.4, 1), _pt(20.1, 2), _pt(23.7, 3)])
    assert result.direction is Trend.WORSENING
    assert result.delta_weeks == pytest.approx(5.3)
    assert result.pct_change == pytest.approx(5.3 / 18.4)


def test_improving_when_wait_shrinks_beyond_dead_band():
    result = compute_trend([_pt(30.0, 1), _pt(20.0, 3)])
    assert result.direction is Trend.IMPROVING
    assert result.delta_weeks == pytest.approx(-10.0)


def test_flat_when_change_within_dead_band():
    # -2% on a 41-week wait is inside the default 5% dead-band.
    result = compute_trend(
        [_pt(41.0, 1, specialty="Ortho"), _pt(40.2, 3, specialty="Ortho")]
    )
    assert result.direction is Trend.FLAT


def test_points_are_sorted_before_comparison():
    # Supplied newest-first; start/end must still be Jan/Mar.
    result = compute_trend([_pt(23.7, 3), _pt(18.4, 1)])
    assert result.start.as_of == date(2026, 1, 1)
    assert result.end.as_of == date(2026, 3, 1)
    assert result.direction is Trend.WORSENING


def test_single_point_rejected():
    with pytest.raises(ValueError, match="at least two points"):
        compute_trend([_pt(18.4, 1)])


def test_mixed_provider_or_specialty_rejected():
    with pytest.raises(ValueError, match="one provider_code and specialty"):
        compute_trend([_pt(18.4, 1, provider="RGT"), _pt(18.4, 2, provider="RJ1")])


def test_zero_baseline_increase_is_worsening():
    result = compute_trend([_pt(0.0, 1), _pt(5.0, 2)])
    assert result.direction is Trend.WORSENING
    assert result.pct_change is None  # undefined against a zero baseline


def test_negative_weeks_rejected_at_construction():
    with pytest.raises(ValueError, match="weeks must be >= 0"):
        WaitTimePoint("RGT", "Cardiology", -1.0, date(2026, 1, 1))
