"""Contract tests for the My Planned Care CSV source."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nhs_intel.sources import PlannedCareCsvSource

FIXTURE = Path(__file__).parent / "fixtures" / "planned_care_sample.csv"


@pytest.fixture
def source() -> PlannedCareCsvSource:
    return PlannedCareCsvSource(FIXTURE)


def test_latest_returns_first_outpatient_not_treatment(source: PlannedCareCsvSource):
    record = source.latest("Guy's and St Thomas'", "Cardiology")
    assert record is not None
    assert record.weeks == 14  # the first_outpatient row, not the treatment row (22)
    assert record.as_of == date(2026, 8, 24)


def test_latest_unknown_returns_none(source: PlannedCareCsvSource):
    assert source.latest("Nonexistent Trust", "Cardiology") is None


def test_for_specialty_lists_all_regions(source: PlannedCareCsvSource):
    records = source.for_specialty("Cardiology")
    providers = {r.provider for r in records}
    assert providers == {
        "Guy's and St Thomas'",
        "King's College Hospital",
        "Manchester Royal Infirmary",
        "St George's",
    }


def test_for_specialty_filters_by_region(source: PlannedCareCsvSource):
    records = source.for_specialty("Cardiology", region="North West")
    assert [r.provider for r in records] == ["Manchester Royal Infirmary"]


def test_null_wait_is_preserved_not_dropped(source: PlannedCareCsvSource):
    record = source.latest("Guy's and St Thomas'", "Trauma & Orthopaedics")
    assert record is not None
    assert record.weeks is None  # published the row but no figure


def test_missing_columns_rejected(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("region,provider\nLondon,Guy's\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        PlannedCareCsvSource(bad)
