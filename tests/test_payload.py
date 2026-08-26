"""Tests for domain-object serialisation (the single wire-format definition)."""

from __future__ import annotations

from datetime import date

from nhs_intel.analysis import compute_trend
from nhs_intel.domain import WaitTimePoint


def test_waittimepoint_payload_shape():
    payload = WaitTimePoint("RGT", "Cardiology", 18.4, date(2026, 1, 1)).to_payload()
    assert payload == {"weeks": 18.4, "as_of": "2026-01-01"}


def test_trendresult_payload_shape():
    result = compute_trend(
        [
            WaitTimePoint("RGT", "Cardiology", 18.4, date(2026, 1, 1)),
            WaitTimePoint("RGT", "Cardiology", 23.7, date(2026, 3, 1)),
        ]
    )
    payload = result.to_payload()
    assert payload["found"] is True
    assert payload["provider_code"] == "RGT"
    assert payload["direction"] == "worsening"
    assert payload["start"] == {"weeks": 18.4, "as_of": "2026-01-01"}
    assert payload["end"] == {"weeks": 23.7, "as_of": "2026-03-01"}
    assert len(payload["series"]) == 2
