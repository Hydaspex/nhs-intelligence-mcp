"""NHS England RTT wait-time source.

RTT is published as monthly provider-level XLSX. For M1 this adapter reads an
already-ingested CSV cache with columns ``provider_code,specialty,weeks,as_of``
(one row per provider/specialty/month). The XLSX-to-CSV ingest step is a later
milestone; separating ingest from serving keeps this class pure enough to test
against a small fixture and keeps the monthly download out of the request path.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from nhs_intel.domain import WaitTimePoint


class RttCsvSource:
    """Serve RTT wait-time points from a cached CSV.

    The CSV is read once at construction and held in memory, keyed by
    ``(provider_code, specialty)``, so repeated ``series`` calls do no I/O.
    """

    def __init__(self, csv_path: Path) -> None:
        self._by_key: dict[tuple[str, str], list[WaitTimePoint]] = {}
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"provider_code", "specialty", "weeks", "as_of"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"RTT CSV missing columns: {sorted(missing)}")

            for row in reader:
                point = WaitTimePoint(
                    provider_code=row["provider_code"].strip(),
                    specialty=row["specialty"].strip(),
                    weeks=float(row["weeks"]),
                    as_of=date.fromisoformat(row["as_of"].strip()),
                )
                key = (point.provider_code, point.specialty)
                self._by_key.setdefault(key, []).append(point)

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        """Return the cached points for one provider/specialty (may be empty)."""
        return list(self._by_key.get((provider_code, specialty), []))
