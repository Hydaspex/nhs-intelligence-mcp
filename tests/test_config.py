"""Tests for centralised settings resolution."""

from __future__ import annotations

from pathlib import Path

from nhs_intel.config import (
    DB_ENV,
    PARTNER_CODE_ENV,
    Settings,
)

_DEFAULT_DB = Path(__file__).parents[1] / "data" / "nhs_intel.db"


def test_from_env_defaults_db_path_when_unset():
    settings = Settings.from_env({})
    # Default path is platform user-data-dir/nhs_intel.db (platformdirs).
    assert settings.db_path.name == "nhs_intel.db"
    assert settings.db_path.parent.name == "nhs-intel"


def test_from_env_uses_override_when_set(tmp_path: Path):
    custom = tmp_path / "custom.db"
    settings = Settings.from_env({DB_ENV: str(custom)})
    assert settings.db_path == custom


def test_partner_code_defaults_none():
    assert Settings.from_env({}).cqc_partner_code is None


def test_partner_code_reads_when_set():
    settings = Settings.from_env({PARTNER_CODE_ENV: "my-org"})
    assert settings.cqc_partner_code == "my-org"
