"""Tests for the incremental RTT backfill.

Month selection, index parsing, and DB loading run against a fake BrowserFetcher
and the shared fixture workbook, so no browser or network is touched. Only
PlaywrightFetcher needs the real browser, and it is not exercised here.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from nhs_intel.ingest.rtt_backfill import (
    backfill,
    existing_months,
    financial_year_index_url,
    missing_months,
    recent_months,
)

FIXTURE_XLSX = Path(__file__).parent / "fixtures" / "rtt_incomplete_provider_sample.xlsx"

_INDEX_HTML = """
<ul>
<li><a href="https://example.nhs.uk/files/Incomplete-Provider-Jun26-9M.xlsx">Incomplete Provider Jun26 (XLSX, 9M)</a></li>
<li><a href="https://example.nhs.uk/files/Incomplete-Provider-May26-9M.xlsx">Incomplete Provider May26 (XLSX, 9M)</a></li>
</ul>
"""


class FakeFetcher:
    """BrowserFetcher returning a fixed index and the fixture workbook bytes."""

    def __init__(self) -> None:
        self.html_calls: list[str] = []
        self.byte_calls: list[str] = []

    def get_html(self, url: str) -> str:
        self.html_calls.append(url)
        return _INDEX_HTML

    def get_bytes(self, url: str) -> bytes:
        self.byte_calls.append(url)
        return FIXTURE_XLSX.read_bytes()


def _seed_db(path: Path, months: list[str]) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE rtt (provider_code TEXT, specialty TEXT, weeks REAL, as_of TEXT, "
            "PRIMARY KEY (provider_code, specialty, as_of))"
        )
        conn.executemany(
            "INSERT INTO rtt VALUES ('RGT', 'Cardiology', 10.0, ?)",
            [(f"{m}-01",) for m in months],
        )


def test_recent_months_excludes_current_and_counts_back():
    assert recent_months(date(2026, 8, 15), window=3) == ["2026-07", "2026-06", "2026-05"]


def test_recent_months_crosses_year_boundary():
    assert recent_months(date(2026, 2, 1), window=3) == ["2026-01", "2025-12", "2025-11"]


def test_existing_months_reads_distinct_as_of(tmp_path: Path):
    db = tmp_path / "nhs.db"
    _seed_db(db, ["2026-04", "2026-05"])
    assert existing_months(db) == {"2026-04", "2026-05"}


def test_existing_months_empty_when_db_absent(tmp_path: Path):
    assert existing_months(tmp_path / "missing.db") == set()


def test_missing_months_returns_gap_oldest_first(tmp_path: Path):
    db = tmp_path / "nhs.db"
    _seed_db(db, ["2026-06"])
    missing = missing_months(db, date(2026, 8, 15), window=3)
    assert missing == ["2026-05", "2026-07"]


def test_financial_year_index_url_splits_on_april():
    assert "rtt-data-2026-27" in financial_year_index_url("2026-06")
    assert "rtt-data-2025-26" in financial_year_index_url("2026-03")


def test_backfill_loads_only_months_on_index(tmp_path: Path):
    db = tmp_path / "nhs.db"
    _seed_db(db, [])
    fetcher = FakeFetcher()

    # Apr26 is not on the fixture index and must be skipped, not fatal.
    loaded = backfill(db, ["2026-04", "2026-05", "2026-06"], fetcher, tmp_path / "cache")

    assert loaded > 0
    with sqlite3.connect(db) as conn:
        got = {row[0][:7] for row in conn.execute("SELECT DISTINCT as_of FROM rtt")}
    assert got == {"2026-05", "2026-06"}


def test_backfill_fetches_index_once_per_financial_year(tmp_path: Path):
    db = tmp_path / "nhs.db"
    _seed_db(db, [])
    fetcher = FakeFetcher()

    backfill(db, ["2026-05", "2026-06"], fetcher, tmp_path / "cache")

    # Both months share the 2026-27 index, so it is fetched exactly once.
    assert len(fetcher.html_calls) == 1
