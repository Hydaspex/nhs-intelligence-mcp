"""Tests for centralised settings resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from nhs_intel.config import (
    IDENTITY_CSV_ENV,
    PARTNER_CODE_ENV,
    PLANNED_CARE_CSV_ENV,
    RTT_CSV_ENV,
    Settings,
)

FIXTURE = Path(__file__).parent / "fixtures" / "rtt_sample.csv"
PC_FIXTURE = Path(__file__).parent / "fixtures" / "planned_care_sample.csv"
ID_FIXTURE = Path(__file__).parent / "fixtures" / "identity_sample.csv"


def test_from_env_resolves_existing_path():
    settings = Settings.from_env({RTT_CSV_ENV: str(FIXTURE)})
    assert settings.rtt_csv_path == FIXTURE


def test_missing_variable_names_the_variable():
    with pytest.raises(RuntimeError, match=RTT_CSV_ENV):
        Settings.from_env({})


def test_nonexistent_path_is_rejected():
    with pytest.raises(RuntimeError, match="does not point at a file"):
        Settings.from_env({RTT_CSV_ENV: "/no/such/file.csv"})


def test_planned_care_is_optional():
    settings = Settings.from_env({RTT_CSV_ENV: str(FIXTURE)})
    assert settings.planned_care_csv_path is None
    with pytest.raises(RuntimeError, match=PLANNED_CARE_CSV_ENV):
        settings.require_planned_care()


def test_planned_care_resolved_when_present():
    settings = Settings.from_env(
        {RTT_CSV_ENV: str(FIXTURE), PLANNED_CARE_CSV_ENV: str(PC_FIXTURE)}
    )
    assert settings.require_planned_care() == PC_FIXTURE


def test_identity_is_optional():
    settings = Settings.from_env({RTT_CSV_ENV: str(FIXTURE)})
    assert settings.identity_csv_path is None
    with pytest.raises(RuntimeError, match=IDENTITY_CSV_ENV):
        settings.require_identity()


def test_identity_resolved_when_present():
    settings = Settings.from_env(
        {RTT_CSV_ENV: str(FIXTURE), IDENTITY_CSV_ENV: str(ID_FIXTURE)}
    )
    assert settings.require_identity() == ID_FIXTURE


def test_partner_code_defaults_none_and_reads_when_set():
    assert Settings.from_env({RTT_CSV_ENV: str(FIXTURE)}).cqc_partner_code is None
    settings = Settings.from_env(
        {RTT_CSV_ENV: str(FIXTURE), PARTNER_CODE_ENV: "my-org"}
    )
    assert settings.cqc_partner_code == "my-org"
