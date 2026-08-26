"""CQC quality-rating source over the public syndication API.

The public v1 API (https://api.cqc.org.uk/public/v1/) needs no key; callers pass
a ``partnerCode`` query parameter identifying themselves. HTTP is isolated behind
an ``HttpClient`` seam so parsing is unit-tested against fixture JSON and CI never
touches the network.

Response shape used (GET /providers/{id}):
    {
      "providerId": "1-101681210",
      "currentRatings": {
        "overall": {"rating": "Good", "reportDate": "2023-05-01"},
        "keyQuestionRatings": [
          {"name": "Safe", "rating": "Good"},
          {"name": "Well-led", "rating": "Requires improvement"}
        ]
      }
    }

A provider with no ``currentRatings`` (not yet inspected) yields None rather than
a fabricated rating.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import urlencode

from nhs_intel.domain import TrustRating
from nhs_intel.sources.protocol import HttpClient

_BASE_URL = "https://api.cqc.org.uk/public/v1"
_DEFAULT_PARTNER_CODE = "nhs-intelligence-mcp"


class UrllibHttpClient:
    """The real HTTP client: a thin urllib GET returning parsed JSON."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def get_json(self, url: str) -> dict:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LookupError(f"CQC provider not found: {url}") from exc
            raise


class CqcRatingSource:
    """Fetch and parse CQC current ratings for a provider."""

    def __init__(
        self,
        http: HttpClient | None = None,
        partner_code: str = _DEFAULT_PARTNER_CODE,
        base_url: str = _BASE_URL,
    ) -> None:
        self._http = http or UrllibHttpClient()
        self._partner_code = partner_code
        self._base_url = base_url.rstrip("/")

    def rating(self, cqc_provider_id: str) -> TrustRating | None:
        """Return the current rating for a provider, or None if unavailable.

        A rating is treated as unavailable (None) for a missing provider, an
        unrated provider, or any transient fetch failure. The CQC feed is
        supplementary context, so its unavailability degrades one profile
        section rather than failing the whole request.
        """
        query = urlencode({"partnerCode": self._partner_code})
        url = f"{self._base_url}/providers/{cqc_provider_id}?{query}"
        try:
            body = self._http.get_json(url)
        except (LookupError, OSError):
            # LookupError: 404 from the client. OSError covers urllib HTTPError
            # (e.g. 403/5xx) and connection failures, both subclasses of OSError.
            return None
        return _parse_rating(cqc_provider_id, body)


def _parse_rating(cqc_provider_id: str, body: dict) -> TrustRating | None:
    """Build a TrustRating from a provider response, or None if unrated."""
    ratings = body.get("currentRatings") or {}
    overall = ratings.get("overall") or {}
    overall_rating = overall.get("rating")
    if not overall_rating:
        return None

    key_questions = {
        entry["name"]: entry["rating"]
        for entry in ratings.get("keyQuestionRatings") or []
        if entry.get("name") and entry.get("rating")
    }
    return TrustRating(
        cqc_provider_id=cqc_provider_id,
        overall=overall_rating,
        report_date=overall.get("reportDate"),
        key_questions=key_questions,
    )
