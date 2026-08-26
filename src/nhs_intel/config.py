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


@dataclass(frozen=True)
class Settings:
    """Resolved server configuration."""

    rtt_csv_path: Path

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        """Build settings from the environment (or an injected mapping in tests).

        Raises:
            RuntimeError: if a required setting is missing or points at a path
                that does not exist, with a message naming the variable to set.
        """
        source = env if env is not None else os.environ

        raw = source.get(RTT_CSV_ENV)
        if not raw:
            raise RuntimeError(
                f"{RTT_CSV_ENV} is not set; point it at an ingested RTT CSV cache."
            )

        path = Path(raw)
        if not path.is_file():
            raise RuntimeError(f"{RTT_CSV_ENV} does not point at a file: {path}")

        return cls(rtt_csv_path=path)
