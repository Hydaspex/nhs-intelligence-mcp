"""Tests for centralised settings resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from nhs_intel.config import RTT_CSV_ENV, Settings

FIXTURE = Path(__file__).parent / "fixtures" / "rtt_sample.csv"


def test_from_env_resolves_existing_path():
    settings = Settings.from_env({RTT_CSV_ENV: str(FIXTURE)})
    assert settings.rtt_csv_path == FIXTURE


def test_missing_variable_names_the_variable():
    with pytest.raises(RuntimeError, match=RTT_CSV_ENV):
        Settings.from_env({})


def test_nonexistent_path_is_rejected():
    with pytest.raises(RuntimeError, match="does not point at a file"):
        Settings.from_env({RTT_CSV_ENV: "/no/such/file.csv"})
