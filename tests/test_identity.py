"""Tests for the trust-identity mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from nhs_intel.sources import TrustIdentityMap

FIXTURE = Path(__file__).parent / "fixtures" / "identity_sample.csv"


@pytest.fixture
def identity_map() -> TrustIdentityMap:
    return TrustIdentityMap(FIXTURE)


def test_resolves_by_code(identity_map: TrustIdentityMap):
    identity = identity_map.by_code("RGT")
    assert identity is not None
    assert identity.provider_name == "Guy's and St Thomas'"
    assert identity.cqc_provider_id == "1-101681210"


def test_resolves_by_name(identity_map: TrustIdentityMap):
    identity = identity_map.by_name("King's College Hospital")
    assert identity is not None
    assert identity.provider_code == "RJ1"


def test_unmapped_code_returns_none(identity_map: TrustIdentityMap):
    assert identity_map.by_code("ZZZ") is None


def test_unmapped_name_returns_none(identity_map: TrustIdentityMap):
    assert identity_map.by_name("Nonexistent Trust") is None


def test_missing_columns_rejected(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("provider_code,provider_name\nRGT,Guy's\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        TrustIdentityMap(bad)
