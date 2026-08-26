"""Contract tests for the RTT CSV source against a captured fixture."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nhs_intel.sources import RttCsvSource

FIXTURE = Path(__file__).parent / "fixtures" / "rtt_sample.csv"


@pytest.fixture
def source() -> RttCsvSource:
    return RttCsvSource(FIXTURE)


def test_series_returns_all_points_for_key(source: RttCsvSource):
    points = source.series("RGT", "Cardiology")
    assert len(points) == 3
    assert {p.as_of for p in points} == {
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    }


def test_series_is_isolated_per_specialty(source: RttCsvSource):
    assert len(source.series("RGT", "Trauma & Orthopaedics")) == 2
    assert len(source.series("RGT", "Cardiology")) == 3


def test_unknown_key_returns_empty(source: RttCsvSource):
    assert source.series("ZZZ", "Cardiology") == []
    assert source.series("RGT", "Dermatology") == []


def test_returned_list_is_a_copy(source: RttCsvSource):
    first = source.series("RGT", "Cardiology")
    first.clear()
    assert len(source.series("RGT", "Cardiology")) == 3  # cache not mutated


def test_missing_columns_rejected(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("provider_code,specialty\nRGT,Cardiology\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        RttCsvSource(bad)
