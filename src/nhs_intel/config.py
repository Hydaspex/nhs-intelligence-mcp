"""Centralised configuration for the server.

All environment access lives here, so no other module reads ``os.environ``
directly. As later milestones add the My Planned Care scraper path and the
optional CQC key, each becomes one validated field here rather than a raw
``os.environ.get`` scattered through the code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RTT_CSV_ENV = "NHS_INTEL_RTT_CSV"
PLANNED_CARE_CSV_ENV = "NHS_INTEL_PLANNED_CARE_CSV"
IDENTITY_CSV_ENV = "NHS_INTEL_IDENTITY_CSV"
PARTNER_CODE_ENV = "NHS_INTEL_CQC_PARTNER_CODE"


def _resolve_file(env: dict[str, str], var: str) -> Path:
    """Resolve a required file path from an env var, or raise naming the var."""
    raw = env.get(var)
    if not raw:
        raise RuntimeError(f"{var} is not set; point it at the expected CSV cache.")
    path = Path(raw)
    if not path.is_file():
        raise RuntimeError(f"{var} does not point at a file: {path}")
    return path


@dataclass(frozen=True)
class Settings:
    """Resolved server configuration.

    ``rtt_csv_path`` backs the trend tool; ``planned_care_csv_path`` backs the
    current-state tools and is optional, so a deployment that only has RTT data
    still serves ``wait_time_trend``. Each ``*_path`` accessor raises with a
    clear message when the underlying source was not configured.
    """

    rtt_csv_path: Path
    planned_care_csv_path: Path | None
    identity_csv_path: Path | None
    cqc_partner_code: str | None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from the environment (or an injected mapping in tests).

        Only ``rtt_csv_path`` is required. The planned-care and identity paths are
        optional and validated only when present; the partner code is a plain
        string with no default here (the CQC source supplies its own).

        Raises:
            RuntimeError: if RTT is missing or its path does not exist, or if an
                optional path is set but points at a missing file.
        """
        source = dict(env) if env is not None else dict(os.environ)

        rtt = _resolve_file(source, RTT_CSV_ENV)

        planned_care: Path | None = None
        if source.get(PLANNED_CARE_CSV_ENV):
            planned_care = _resolve_file(source, PLANNED_CARE_CSV_ENV)

        identity: Path | None = None
        if source.get(IDENTITY_CSV_ENV):
            identity = _resolve_file(source, IDENTITY_CSV_ENV)

        return cls(
            rtt_csv_path=rtt,
            planned_care_csv_path=planned_care,
            identity_csv_path=identity,
            cqc_partner_code=source.get(PARTNER_CODE_ENV) or None,
        )

    def require_planned_care(self) -> Path:
        """Return the planned-care path, or raise if it was not configured."""
        if self.planned_care_csv_path is None:
            raise RuntimeError(
                f"{PLANNED_CARE_CSV_ENV} is not set; current-state tools need "
                "My Planned Care scraper output."
            )
        return self.planned_care_csv_path

    def require_identity(self) -> Path:
        """Return the identity-map path, or raise if it was not configured."""
        if self.identity_csv_path is None:
            raise RuntimeError(
                f"{IDENTITY_CSV_ENV} is not set; the trust profile needs the "
                "cross-source identity mapping."
            )
        return self.identity_csv_path
