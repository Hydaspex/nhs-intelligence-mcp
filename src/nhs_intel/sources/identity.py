"""Trust-identity mapping across the RTT / My Planned Care / CQC schemes.

The three sources name trusts differently, and there is no reliable automatic
join between them, so identity is resolved from a small curated mapping table. A
trust absent from the table cannot be joined: the combined profile abstains for
it, which is the correct behaviour for a tool meant to avoid confident wrong
answers.

Mapping CSV columns: provider_code, provider_name, cqc_provider_id
"""

from __future__ import annotations

import csv
from pathlib import Path

from nhs_intel.domain import TrustIdentity

_REQUIRED_COLUMNS = {"provider_code", "provider_name", "cqc_provider_id"}


class TrustIdentityMap:
    """Look up a trust's cross-source identity by any of its identifiers."""

    def __init__(self, csv_path: Path) -> None:
        self._by_code: dict[str, TrustIdentity] = {}
        self._by_name: dict[str, TrustIdentity] = {}
        self._load(csv_path)

    def _load(self, csv_path: Path) -> None:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = _REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"identity CSV missing columns: {sorted(missing)}")

            for row in reader:
                identity = TrustIdentity(
                    provider_code=row["provider_code"].strip(),
                    provider_name=row["provider_name"].strip(),
                    cqc_provider_id=row["cqc_provider_id"].strip(),
                )
                self._by_code[identity.provider_code] = identity
                self._by_name[identity.provider_name] = identity

    def by_code(self, provider_code: str) -> TrustIdentity | None:
        """Resolve identity from an RTT provider code, or None if unmapped."""
        return self._by_code.get(provider_code)

    def by_name(self, provider_name: str) -> TrustIdentity | None:
        """Resolve identity from a My Planned Care trust name, or None if unmapped."""
        return self._by_name.get(provider_name)
