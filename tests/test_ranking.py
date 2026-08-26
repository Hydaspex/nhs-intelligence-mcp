"""Unit tests for the pure trust-ranking analysis."""

from __future__ import annotations

from datetime import date

from nhs_intel.analysis import rank_by_wait
from nhs_intel.domain import CurrentWait


def _w(provider: str, weeks: int | None, region: str = "London") -> CurrentWait:
    return CurrentWait(region, provider, "Cardiology", weeks, date(2026, 8, 24))


def test_ranks_longest_wait_first():
    ranked = rank_by_wait([_w("A", 11), _w("B", 19), _w("C", 14)])
    assert [r.provider for r in ranked] == ["B", "C", "A"]


def test_ties_break_alphabetically():
    # King's and St George's both 19 weeks -> A→Z order, longest-first overall.
    ranked = rank_by_wait([_w("St George's", 19), _w("King's", 19), _w("A", 11)])
    assert [r.provider for r in ranked] == ["King's", "St George's", "A"]


def test_ascending_order_when_requested():
    ranked = rank_by_wait([_w("A", 11), _w("B", 19)], descending=False)
    assert [r.provider for r in ranked] == ["A", "B"]


def test_unknown_waits_go_last_in_name_order():
    ranked = rank_by_wait([_w("Z", None), _w("A", 14), _w("M", None)])
    assert [r.provider for r in ranked] == ["A", "M", "Z"]
    # the two unknowns are last, and ordered A→Z among themselves
    assert ranked[1].weeks is None and ranked[2].weeks is None


def test_empty_input():
    assert rank_by_wait([]) == []
