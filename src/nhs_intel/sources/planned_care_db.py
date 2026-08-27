"""SQLite-backed My Planned Care source.

Replaces PlannedCareCsvSource for server use; reads the ``planned_care`` table
populated by ``nhs-intel-load-db``.

The same metric-filtering and recency logic from the CSV adapter is applied at
query time via SQL so no extra in-memory pass is needed.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from nhs_intel.domain import CurrentWait

_DEFAULT_DB = Path(__file__).parents[3] / "data" / "nhs_intel.db"
_HEADLINE_METRIC = "first_outpatient_appointment"


def _parse_weeks(raw: float | None) -> int | None:
    if raw is None:
        return None
    val = float(raw)
    return int(val) if val == int(val) else int(val)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


class PlannedCareDbSource:
    """Serve current-state waits from the SQLite ``planned_care`` table."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def latest(self, provider: str, specialty: str) -> CurrentWait | None:
        """Return the latest first-outpatient wait for one provider/specialty."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT region, provider, specialty, average_wait_weeks, page_last_updated "
                "FROM planned_care "
                "WHERE provider = ? AND specialty = ? AND metric = ? "
                "ORDER BY page_last_updated DESC NULLS LAST "
                "LIMIT 1",
                (provider, specialty, _HEADLINE_METRIC),
            )
            row = cur.fetchone()

        if row is None:
            return None
        return CurrentWait(
            region=row["region"] or "",
            provider=row["provider"],
            specialty=row["specialty"],
            weeks=_parse_weeks(row["average_wait_weeks"]),
            as_of=_parse_date(row["page_last_updated"]),
        )

    def for_specialty(
        self, specialty: str, region: str | None = None
    ) -> list[CurrentWait]:
        """Return every trust's latest wait for a specialty, optionally by region."""
        # Subquery picks the most-recent row per (provider, specialty).
        base_sql = (
            "SELECT region, provider, specialty, average_wait_weeks, page_last_updated "
            "FROM planned_care p1 "
            "WHERE metric = ? AND specialty = ? "
            "AND page_last_updated = ("
            "  SELECT MAX(page_last_updated) FROM planned_care p2 "
            "  WHERE p2.provider = p1.provider AND p2.specialty = p1.specialty "
            "  AND p2.metric = p1.metric"
            ")"
        )
        params: list = [_HEADLINE_METRIC, specialty]

        if region is not None:
            base_sql += " AND region = ?"
            params.append(region)

        with self._connect() as conn:
            cur = conn.execute(base_sql, params)
            rows = cur.fetchall()

        return [
            CurrentWait(
                region=row["region"] or "",
                provider=row["provider"],
                specialty=row["specialty"],
                weeks=_parse_weeks(row["average_wait_weeks"]),
                as_of=_parse_date(row["page_last_updated"]),
            )
            for row in rows
        ]
