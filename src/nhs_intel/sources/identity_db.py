"""SQLite-backed trust-identity source.

Replaces TrustIdentityMap for server use; reads the ``identity`` table
populated by ``nhs-intel-load-db``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from nhs_intel.domain import TrustIdentity

_DEFAULT_DB = Path(__file__).parents[3] / "data" / "nhs_intel.db"


class TrustIdentityDbMap:
    """Look up a trust's cross-source identity from the SQLite ``identity`` table."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def by_code(self, provider_code: str) -> TrustIdentity | None:
        """Resolve identity from an RTT provider code, or None if unmapped."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT provider_code, provider_name, cqc_provider_id "
                "FROM identity WHERE provider_code = ?",
                (provider_code,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return TrustIdentity(
            provider_code=row["provider_code"],
            provider_name=row["provider_name"],
            cqc_provider_id=row["cqc_provider_id"],
        )

    def by_name(self, provider_name: str) -> TrustIdentity | None:
        """Resolve identity from a My Planned Care trust name, or None if unmapped."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT provider_code, provider_name, cqc_provider_id "
                "FROM identity WHERE provider_name = ?",
                (provider_name,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return TrustIdentity(
            provider_code=row["provider_code"],
            provider_name=row["provider_name"],
            cqc_provider_id=row["cqc_provider_id"],
        )
