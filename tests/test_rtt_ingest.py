"""Tests for the RTT ingest script.

The XLSX parser and CSV writer are tested against a small local fixture
workbook with no network. The index-page and download functions are tested
with an injected fake HTTP client, following the HttpClient seam pattern used
for the CQC source.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from nhs_intel.ingest.rtt_ingest import (
    RttRow,
    find_incomplete_provider_url,
    month_label_and_as_of,
    parse_incomplete_provider_xlsx,
    resolve_incomplete_provider_url,
    run,
    write_csv,
)
from nhs_intel.sources import RttCsvSource

FIXTURE_XLSX = Path(__file__).parent / "fixtures" / "rtt_incomplete_provider_sample.xlsx"


class FakeTextHttp:
    """TextHttpClient returning a fixed HTML body, no network."""

    def __init__(self, html: str) -> None:
        self._html = html

    def get_text(self, url: str) -> str:
        return self._html


_INDEX_HTML = """
<ul>
<li><a href="https://example.nhs.uk/files/Incomplete-Commissioner-Jun26-XLSX-4M-abc123.xlsx">Incomplete Commissioner Jun26 (XLSX, 4M)</a></li>
<li><a href="https://example.nhs.uk/files/Incomplete-Provider-Jun26-XLSX-9M-abc123.xlsx">Incomplete Provider Jun26 (XLSX, 9M)</a></li>
<li><a href="https://example.nhs.uk/files/Admitted-Provider-Jun26-XLSX-4M-abc123.xlsx">Admitted Provider Jun26 (XLSX, 4M)</a></li>
<li><a href="https://example.nhs.uk/files/Incomplete-Provider-May26-XLSX-9M-def456.xlsx">Incomplete Provider May26 (XLSX, 9M)</a></li>
</ul>
"""


def test_finds_incomplete_provider_link_for_target_month():
    url = find_incomplete_provider_url(_INDEX_HTML, "Jun26")
    assert url == "https://example.nhs.uk/files/Incomplete-Provider-Jun26-XLSX-9M-abc123.xlsx"


def test_does_not_match_admitted_or_commissioner_variants():
    url = find_incomplete_provider_url(_INDEX_HTML, "Jun26")
    assert "Admitted" not in url
    assert "Commissioner" not in url


def test_unknown_month_raises_lookup_error():
    with pytest.raises(LookupError):
        find_incomplete_provider_url(_INDEX_HTML, "Dec26")


def test_resolve_uses_injected_http_client():
    url = resolve_incomplete_provider_url(
        "https://example.nhs.uk/rtt-data-2026-27/", "Jun26", http=FakeTextHttp(_INDEX_HTML)
    )
    assert url.endswith("Incomplete-Provider-Jun26-XLSX-9M-abc123.xlsx")


def test_month_label_and_as_of():
    label, as_of = month_label_and_as_of("2026-06")
    assert label == "Jun26"
    assert as_of == date(2026, 6, 1)


def test_parses_provider_rows_from_fixture():
    rows = list(parse_incomplete_provider_xlsx(FIXTURE_XLSX, date(2026, 6, 1)))
    keys = {(r.provider_code, r.specialty) for r in rows}
    assert ("RGT", "Cardiology") in keys
    assert ("RGT", "Trauma & Orthopaedics") in keys
    assert ("RJ1", "Cardiology") in keys


def test_skips_total_aggregate_row():
    rows = list(parse_incomplete_provider_xlsx(FIXTURE_XLSX, date(2026, 6, 1)))
    assert not any(r.specialty == "Total" for r in rows)


def test_skips_suppressed_median_row():
    rows = list(parse_incomplete_provider_xlsx(FIXTURE_XLSX, date(2026, 6, 1)))
    assert not any(r.specialty == "Cardiothoracic Surgery" for r in rows)


def test_parsed_weeks_and_as_of_values():
    rows = list(parse_incomplete_provider_xlsx(FIXTURE_XLSX, date(2026, 6, 1)))
    by_key = {(r.provider_code, r.specialty): r for r in rows}
    cardiology = by_key[("RGT", "Cardiology")]
    assert cardiology.weeks == 18.4
    assert cardiology.as_of == date(2026, 6, 1)


def test_write_csv_matches_rtt_csv_source_contract(tmp_path: Path):
    rows = [
        RttRow(provider_code="RGT", specialty="Cardiology", weeks=18.4, as_of=date(2026, 6, 1)),
        RttRow(provider_code="RJ1", specialty="Cardiology", weeks=12.0, as_of=date(2026, 6, 1)),
    ]
    out_path = tmp_path / "rtt_out.csv"
    count = write_csv(iter(rows), out_path)
    assert count == 2

    with out_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["provider_code", "specialty", "weeks", "as_of"]
        written = list(reader)
    assert written[0]["provider_code"] == "RGT"

    # The written CSV must be directly loadable by the existing consumer.
    source = RttCsvSource(out_path)
    points = source.series("RGT", "Cardiology")
    assert len(points) == 1
    assert points[0].weeks == 18.4


def test_run_end_to_end_with_fake_http_and_local_download(tmp_path: Path, monkeypatch):
    def fake_download(url: str, dest_path: Path, timeout: float = 60.0) -> None:
        dest_path.write_bytes(FIXTURE_XLSX.read_bytes())

    monkeypatch.setattr("nhs_intel.ingest.rtt_ingest.download_xlsx", fake_download)
    monkeypatch.setattr(
        "nhs_intel.ingest.rtt_ingest.resolve_incomplete_provider_url",
        lambda index_url, month_label, http=None: "https://example.nhs.uk/fake.xlsx",
    )

    out_path = tmp_path / "rtt_out.csv"
    written = run("https://example.nhs.uk/rtt-data-2026-27/", "2026-06", out_path, None)

    assert written > 0
    source = RttCsvSource(out_path)
    assert source.series("RGT", "Cardiology")[0].weeks == 18.4
