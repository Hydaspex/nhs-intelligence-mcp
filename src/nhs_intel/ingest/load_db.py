"""CLI to load CSVs into the NHS intelligence SQLite database.

Usage:
    uv run nhs-intel-load-db \\
        --rtt /path/to/rtt.csv \\
        --planned-care /path/to/planned_care.csv \\
        --identity /path/to/identity.csv \\
        --db ~/.local/share/nhs-intel/nhs_intel.db  # default varies by OS

All CSV args are optional; a table is skipped when its arg is absent.
Env-var fallbacks (backward compat): NHS_INTEL_RTT_CSV, NHS_INTEL_PLANNED_CARE_CSV,
NHS_INTEL_IDENTITY_CSV.
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path

from platformdirs import user_data_dir

_SCHEMA = Path(__file__).parents[3] / "data" / "schema.sql"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA.read_text())
    # Migrate existing identity tables that pre-date the overall_rating column.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(identity)")}
    if "overall_rating" not in cols:
        conn.execute("ALTER TABLE identity ADD COLUMN overall_rating TEXT")
    conn.commit()


def _load_rtt(conn: sqlite3.Connection, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [
            (
                row["provider_code"].strip(),
                row["specialty"].strip(),
                float(row["weeks"]),
                row["as_of"].strip(),
            )
            for row in reader
        ]
    conn.executemany(
        "INSERT OR REPLACE INTO rtt (provider_code, specialty, weeks, as_of) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def _load_planned_care(conn: sqlite3.Connection, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [
            (
                row.get("region", "").strip(),
                row.get("provider", "").strip(),
                row.get("specialty", "").strip(),
                row.get("source_url", "").strip(),
                row.get("metric", "").strip(),
                float(row["average_wait_weeks"]) if row.get("average_wait_weeks", "").strip() else None,
                float(row["patients_seen_within_weeks"]) if row.get("patients_seen_within_weeks", "").strip() else None,
                row.get("page_last_updated", "").strip() or None,
            )
            for row in reader
        ]
    conn.executemany(
        "INSERT OR REPLACE INTO planned_care "
        "(region, provider, specialty, source_url, metric, "
        "average_wait_weeks, patients_seen_within_weeks, page_last_updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def _load_identity(conn: sqlite3.Connection, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [
            (
                row["provider_code"].strip(),
                row["provider_name"].strip(),
                row.get("planned_care_name", "").strip() or None,
                row.get("cqc_provider_id", "").strip() or None,
            )
            for row in reader
        ]
    conn.executemany(
        "INSERT OR REPLACE INTO identity "
        "(provider_code, provider_name, planned_care_name, cqc_provider_id) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def _load_cqc(conn: sqlite3.Connection, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [
            (
                row["provider_code"].strip(),
                row["provider_name"].strip(),
                row["overall_rating"].strip(),
            )
            for row in reader
        ]
    conn.executemany(
        "INSERT INTO identity (provider_code, provider_name, overall_rating) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(provider_code) DO UPDATE SET overall_rating = excluded.overall_rating",
        rows,
    )
    conn.commit()
    return len(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load NHS intelligence CSVs into SQLite."
    )
    parser.add_argument("--rtt", default=os.environ.get("NHS_INTEL_RTT_CSV"))
    parser.add_argument("--planned-care", default=os.environ.get("NHS_INTEL_PLANNED_CARE_CSV"))
    parser.add_argument("--identity", default=os.environ.get("NHS_INTEL_IDENTITY_CSV"))
    parser.add_argument("--cqc", default=None, help="Path to CQC ratings CSV")
    parser.add_argument(
        "--db",
        default=os.environ.get("NHS_INTEL_DB") or str(Path(user_data_dir("nhs-intel")) / "nhs_intel.db"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        _ensure_schema(conn)

        if args.rtt:
            n = _load_rtt(conn, Path(args.rtt))
            print(f"rtt: {n} rows inserted")
        else:
            print("rtt: skipped (no --rtt arg)")

        if args.planned_care:
            n = _load_planned_care(conn, Path(args.planned_care))
            print(f"planned_care: {n} rows inserted")
        else:
            print("planned_care: skipped (no --planned-care arg)")

        if args.identity:
            n = _load_identity(conn, Path(args.identity))
            print(f"identity: {n} rows inserted")
        else:
            print("identity: skipped (no --identity arg)")

        if args.cqc:
            n = _load_cqc(conn, Path(args.cqc))
            print(f"cqc: {n} rows upserted")
        else:
            print("cqc: skipped (no --cqc arg)")


if __name__ == "__main__":
    main()
