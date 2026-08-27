"""Centralised configuration for the server.

All environment access lives here, so no other module reads ``os.environ``
directly. The server now reads from a SQLite DB (NHS_INTEL_DB) rather than
individual CSV files. The CSV env vars are retained for use by nhs-intel-load-db
but are no longer read by the server at runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

# DB env var — set to override the default platform data-dir path.
DB_ENV = "NHS_INTEL_DB"

# Kept for backward compat with nhs-intel-load-db (ingest CLI).
RTT_CSV_ENV = "NHS_INTEL_RTT_CSV"
PLANNED_CARE_CSV_ENV = "NHS_INTEL_PLANNED_CARE_CSV"
IDENTITY_CSV_ENV = "NHS_INTEL_IDENTITY_CSV"
PARTNER_CODE_ENV = "NHS_INTEL_CQC_PARTNER_CODE"

# ~/Library/Application Support/nhs-intel/nhs_intel.db  (Mac)
# ~/.local/share/nhs-intel/nhs_intel.db                 (Linux)
# %APPDATA%\nhs-intel\nhs_intel.db                      (Windows)
_DEFAULT_DB = Path(user_data_dir("nhs-intel")) / "nhs_intel.db"


@dataclass(frozen=True)
class Settings:
    """Resolved server configuration."""

    db_path: Path
    cqc_partner_code: str | None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        """Build settings from the environment (or an injected mapping in tests).

        ``NHS_INTEL_DB`` overrides the default project-relative DB path.
        The DB file need not exist yet (tools fail gracefully with sqlite errors
        rather than at startup).
        """
        source = dict(env) if env is not None else dict(os.environ)
        raw_db = source.get(DB_ENV, "").strip()
        db_path = Path(raw_db) if raw_db else _DEFAULT_DB

        return cls(
            db_path=db_path,
            cqc_partner_code=source.get(PARTNER_CODE_ENV) or None,
        )
