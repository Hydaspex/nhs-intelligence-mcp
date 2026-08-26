"""Tests for the CQC rating source, with a fake HTTP client (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nhs_intel.sources import CqcRatingSource

FIXTURE = Path(__file__).parent / "fixtures" / "cqc_provider.json"


class FakeHttp:
    """HttpClient returning a fixed body, or raising LookupError for 404s."""

    def __init__(self, body: dict | None) -> None:
        self._body = body

    def get_json(self, url: str) -> dict:
        if self._body is None:
            raise LookupError(url)
        return self._body


def _body() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_overall_and_key_questions():
    source = CqcRatingSource(http=FakeHttp(_body()))
    rating = source.rating("1-101681210")
    assert rating is not None
    assert rating.overall == "Good"
    assert rating.report_date == "2023-05-01"
    assert rating.key_questions["Well-led"] == "Outstanding"
    assert rating.key_questions["Safe"] == "Requires improvement"


def test_unknown_provider_returns_none():
    source = CqcRatingSource(http=FakeHttp(None))  # simulates a 404
    assert source.rating("1-000000000") is None


def test_provider_without_ratings_returns_none():
    source = CqcRatingSource(http=FakeHttp({"providerId": "x", "currentRatings": {}}))
    assert source.rating("x") is None


class RaisingHttp:
    """HttpClient that raises an HTTP-style error (e.g. 403), not a 404."""

    def get_json(self, url: str) -> dict:
        import urllib.error

        raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]


def test_transient_http_failure_returns_none_not_raise():
    # A rating fetch failure must degrade to "unavailable", never crash a profile.
    assert CqcRatingSource(http=RaisingHttp()).rating("1-101681210") is None


def test_rating_mapping_is_immutable():
    rating = CqcRatingSource(http=FakeHttp(_body())).rating("1-101681210")
    assert rating is not None
    with pytest.raises(TypeError):
        rating.key_questions["Safe"] = "Good"  # type: ignore[index]
