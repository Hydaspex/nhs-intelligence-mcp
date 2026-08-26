"""My Planned Care current-state source, reading nhs-webscraper CSV output.

The interface between the two projects is the CSV column contract, not a Python
import: this adapter depends on the scraper's published column names, never on
its package. That keeps the two repos loosely coupled: the scraper can change
internally as long as its CSV schema holds.

Scraper CSV columns (fixed, versioned in nhs-webscraper):
    region, provider, specialty, source_url, metric,
    average_wait_weeks, patients_seen_within_weeks, page_last_updated

Only the first-outpatient metric is used as "the current wait"; the treatment
metric is a different measure and is filtered out so a provider/specialty maps to
one figure. When a provider/specialty appears more than once (multiple metrics,
or a re-scrape), the most recently updated first-outpatient row wins.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from nhs_intel.domain import CurrentWait

# The metric treated as the headline current wait.
_HEADLINE_METRIC = "first_outpatient_appointment"

_REQUIRED_COLUMNS = {
    "region",
    "provider",
    "specialty",
    "metric",
    "average_wait_weeks",
    "page_last_updated",
}


def _parse_weeks(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    number = float(raw)  # tolerate legacy "8.0" formatting from the scraper
    if not number.is_integer():
        raise ValueError(f"expected a whole number of weeks, got {raw!r}")
    return int(number)


def _parse_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    return date.fromisoformat(raw) if raw else None


def _more_recent(candidate: CurrentWait, incumbent: CurrentWait) -> bool:
    """True if candidate should replace incumbent as the latest for a key.

    A row with a date beats one without; between two dated rows the later wins.
    """
    if candidate.as_of is None:
        return False
    if incumbent.as_of is None:
        return True
    return candidate.as_of > incumbent.as_of


class PlannedCareCsvSource:
    """Serve current-state waits from a My Planned Care scraper CSV.

    The CSV is read once at construction; the latest first-outpatient row per
    (provider, specialty) is retained, indexed for both point lookup and
    per-specialty ranking.
    """

    def __init__(self, csv_path: Path) -> None:
        # keyed (provider, specialty) -> latest CurrentWait
        self._latest: dict[tuple[str, str], CurrentWait] = {}
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = _REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"planned-care CSV missing columns: {sorted(missing)}"
                )

            for row in reader:
                if row["metric"].strip() != _HEADLINE_METRIC:
                    continue
                record = CurrentWait(
                    region=row["region"].strip(),
                    provider=row["provider"].strip(),
                    specialty=row["specialty"].strip(),
                    weeks=_parse_weeks(row["average_wait_weeks"]),
                    as_of=_parse_date(row["page_last_updated"]),
                )
                key = (record.provider, record.specialty)
                incumbent = self._latest.get(key)
                if incumbent is None or _more_recent(record, incumbent):
                    self._latest[key] = record

    def latest(self, provider: str, specialty: str) -> CurrentWait | None:
        """Return the latest wait for one provider/specialty, or None."""
        return self._latest.get((provider, specialty))

    def for_specialty(
        self, specialty: str, region: str | None = None
    ) -> list[CurrentWait]:
        """Return every trust's latest wait for a specialty, optionally by region."""
        return [
            record
            for (_, spec), record in self._latest.items()
            if spec == specialty and (region is None or record.region == region)
        ]
