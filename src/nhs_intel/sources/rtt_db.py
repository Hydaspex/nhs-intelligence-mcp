"""SQLite-backed RTT wait-time source.

Replaces RttCsvSource for server use; reads the ``rtt`` table populated by
``nhs-intel-load-db``. DB path is resolved from the NHS_INTEL_DB env var,
defaulting to <project-root>/data/nhs_intel.db.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from nhs_intel.domain import WaitTimePoint

_DEFAULT_DB = Path(__file__).parents[3] / "data" / "nhs_intel.db"


class RttDbSource:
    """Serve RTT wait-time points from the SQLite ``rtt`` table."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def series(self, provider_code: str, specialty: str) -> list[WaitTimePoint]:
        """Return all points for one provider/specialty (may be empty)."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT provider_code, specialty, weeks, as_of "
                "FROM rtt WHERE provider_code = ? AND specialty = ?",
                (provider_code, specialty),
            )
            rows = cur.fetchall()

        return [
            WaitTimePoint(
                provider_code=row["provider_code"],
                specialty=row["specialty"],
                weeks=float(row["weeks"]),
                as_of=date.fromisoformat(row["as_of"]),
            )
            for row in rows
        ]
