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

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from the environment (or an injected mapping in tests).

        Raises:
            RuntimeError: if RTT (required) is missing or points at a missing
                file. The planned-care path is optional and only validated when
                present.
        """
        source = dict(env) if env is not None else dict(os.environ)

        rtt = _resolve_file(source, RTT_CSV_ENV)

        planned_care: Path | None = None
        if source.get(PLANNED_CARE_CSV_ENV):
            planned_care = _resolve_file(source, PLANNED_CARE_CSV_ENV)

        return cls(rtt_csv_path=rtt, planned_care_csv_path=planned_care)

    def require_planned_care(self) -> Path:
        """Return the planned-care path, or raise if it was not configured."""
        if self.planned_care_csv_path is None:
            raise RuntimeError(
                f"{PLANNED_CARE_CSV_ENV} is not set; current-state tools need "
                "My Planned Care scraper output."
            )
        return self.planned_care_csv_path
