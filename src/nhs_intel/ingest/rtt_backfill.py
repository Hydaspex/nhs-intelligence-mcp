"""Incremental multi-month RTT ingest.

The weekly cron rebuilds ``nhs_intel.db`` from the previous release, so a
single-month load leaves the ``rtt`` table with one ``as_of`` date and no
history for :func:`nhs_intel.analysis.trend.compute_trend` to work on. This
module fills the gap: given the months already present in a DB, it fetches only
the *missing* recent months and loads them, so history accrues and a skipped
week self-heals on the next run.

NHS England's RTT index page sits behind AWS WAF, which serves plain HTTP
clients a JavaScript challenge instead of the real listing. Fetching is
therefore isolated behind :class:`BrowserFetcher`, a small Protocol whose real
implementation drives Playwright (the ``crawl`` extra) to solve the challenge
and return both the index HTML and the XLSX bytes. The month-selection and
loading logic take that Protocol, so they are unit tested with a fake fetcher
and neither a browser nor a network is touched offline.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from .rtt_ingest import (
    find_incomplete_provider_url,
    month_label_and_as_of,
    parse_incomplete_provider_xlsx,
)

# How many recent months to consider each run. NHS England publishes with a
# ~2-month lag and keeps a financial year's workbooks on one index page, so a
# window this size covers the lag plus a few missed runs without unbounded fetching.
DEFAULT_WINDOW = 6


@runtime_checkable
class BrowserFetcher(Protocol):
    """A WAF-passing fetch seam: rendered page text and raw file bytes."""

    def get_html(self, url: str) -> str:
        """Return the fully rendered HTML of ``url`` (WAF challenge solved)."""
        ...

    def get_bytes(self, url: str) -> bytes:
        """Return the raw bytes of ``url`` using the solved session."""
        ...


def recent_months(today: date, window: int = DEFAULT_WINDOW) -> list[str]:
    """The ``window`` most recent whole months before ``today``, newest first.

    The current month is excluded because RTT data lags publication; callers
    intersect this with what the index actually offers.
    """
    months: list[str] = []
    year, month = today.year, today.month
    for _ in range(window):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        months.append(f"{year:04d}-{month:02d}")
    return months


def existing_months(db_path: Path) -> set[str]:
    """The ``YYYY-MM`` RTT months already loaded in ``db_path`` (empty if none)."""
    if not db_path.exists():
        return set()
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT as_of FROM rtt").fetchall()
    return {row[0][:7] for row in rows}


def missing_months(db_path: Path, today: date, window: int = DEFAULT_WINDOW) -> list[str]:
    """Recent months not yet in the DB, oldest first so the series loads in order."""
    have = existing_months(db_path)
    wanted = recent_months(today, window)
    return sorted(month for month in wanted if month not in have)


def financial_year_index_url(year_month: str) -> str:
    """The NHS England RTT index URL for the financial year containing ``year_month``."""
    target = date.fromisoformat(f"{year_month}-01")
    if target.month < 4:
        fy_start, fy_end = target.year - 1, target.year
    else:
        fy_start, fy_end = target.year, target.year + 1
    fy_slug = f"{fy_start}-{str(fy_end)[-2:]}"
    return (
        "https://www.england.nhs.uk/statistics/statistical-work-areas/"
        f"rtt-waiting-times/rtt-data-{fy_slug}/"
    )


def backfill(
    db_path: Path,
    months: Iterable[str],
    fetcher: BrowserFetcher,
    xlsx_cache: Path,
) -> int:
    """Fetch and load each of ``months`` missing from the index into ``db_path``.

    A month absent from its financial-year index (not yet published, or too old
    for that page) is reported and skipped, not fatal. Returns rows loaded.
    """
    xlsx_cache.mkdir(parents=True, exist_ok=True)
    # One index page per financial year covers several months; fetch each once.
    index_html: dict[str, str] = {}
    loaded = 0

    with sqlite3.connect(db_path) as conn:
        for year_month in months:
            label, as_of = month_label_and_as_of(year_month)
            index_url = financial_year_index_url(year_month)
            if index_url not in index_html:
                index_html[index_url] = fetcher.get_html(index_url)
            try:
                xlsx_url = find_incomplete_provider_url(index_html[index_url], label)
            except LookupError:
                print(f"{year_month} ({label}): not on index; skipped")
                continue

            dest = xlsx_cache / f"rtt_{year_month}.xlsx"
            dest.write_bytes(fetcher.get_bytes(xlsx_url))
            rows = [
                (row.provider_code, row.specialty, row.weeks, row.as_of.isoformat())
                for row in parse_incomplete_provider_xlsx(dest, as_of)
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO rtt (provider_code, specialty, weeks, as_of) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            loaded += len(rows)
            print(f"{year_month} ({label}): {len(rows)} rows loaded")

    return loaded


class PlaywrightFetcher:
    """Real :class:`BrowserFetcher`: a headless Chromium that passes AWS WAF.

    Playwright and a browser come from the ``crawl`` extra; importing lazily
    keeps them out of the core server install and the offline test path.
    """

    _WAF_SETTLE_MS = 6000  # the challenge posts a cookie then reloads; let it settle.

    def __init__(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError(
                "Playwright is not installed; run `pip install nhs-intelligence-mcp[crawl]` "
                "and `playwright install chromium` to use PlaywrightFetcher"
            ) from exc
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        )

    def get_html(self, url: str) -> str:
        page = self._context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(self._WAF_SETTLE_MS)
        html = page.content()
        page.close()
        return html

    def get_bytes(self, url: str) -> bytes:
        response = self._context.request.get(url, timeout=120000)
        if not response.ok:
            raise RuntimeError(f"download {url} -> HTTP {response.status}")
        return response.body()

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._pw.stop()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="SQLite DB to update in place")
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_WINDOW,
        help=f"How many recent months to reconcile (default {DEFAULT_WINDOW})",
    )
    parser.add_argument(
        "--months",
        nargs="+",
        default=None,
        help="Explicit YYYY-MM months to load, bypassing the missing-month check",
    )
    parser.add_argument(
        "--xlsx-cache",
        type=Path,
        default=Path("/tmp/rtt_backfill"),
        help="Directory for downloaded XLSX files",
    )
    return parser


def main() -> None:
    args = _build_arg_parser().parse_args()
    months = args.months or missing_months(args.db, datetime.now(UTC).date(), args.window)
    if not months:
        print("RTT DB already current; nothing to fetch.")
        return
    print(f"Months to load: {', '.join(months)}")

    fetcher = PlaywrightFetcher()
    try:
        loaded = backfill(args.db, months, fetcher, args.xlsx_cache)
    finally:
        fetcher.close()
    print(f"Done: {loaded} rows loaded into {args.db}")
    if loaded == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
