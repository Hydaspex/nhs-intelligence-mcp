"""CLI to download and parse CQC HSCA Active Locations ODS file.

Usage:
    python -m nhs_intel.ingest.cqc_ingest --out /tmp/cqc_ratings.csv

Fetches the latest HSCA_Active_Locations ODS from cqc.org.uk, parses it
using stdlib only (zipfile + xml.etree.ElementTree), and writes a CSV with
columns: provider_code, provider_name, overall_rating.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_DISCOVERY_URL = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"
_ODS_PATTERN = re.compile(r'href="([^"]*HSCA_Active_Locations[^"]*\.ods)"')
_NS_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
_NS_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_NS_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
_TARGET_SHEET = "HSCA_Active_Locations"


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


def _open(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(req, timeout=timeout)


def _discover_ods_url() -> str:
    with _open(_DISCOVERY_URL, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    match = _ODS_PATTERN.search(html)
    if not match:
        raise RuntimeError("Could not find HSCA_Active_Locations ODS link on CQC page")
    href = match.group(1)
    if href.startswith("http"):
        return href
    return "https://www.cqc.org.uk" + href


def _download(url: str) -> bytes:
    with _open(url, timeout=120) as resp:
        return resp.read()


def _expand_cells(row: ET.Element) -> list[str]:
    result: list[str] = []
    for cell in row.findall(f"{_NS_TABLE}table-cell"):
        repeat = int(cell.attrib.get(f"{_NS_TABLE}number-columns-repeated", 1))
        text = cell.findtext(f"{_NS_TEXT}p", default="")
        result.extend([text] * repeat)
    return result


def _parse_ods(data: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        content_xml = zf.read("content.xml")

    root = ET.fromstring(content_xml)
    body = root.find(f"{_NS_OFFICE}body")
    spreadsheet = body.find(f"{_NS_OFFICE}spreadsheet") if body is not None else None
    if spreadsheet is None:
        raise RuntimeError("No spreadsheet body found in ODS content.xml")

    for table in spreadsheet.findall(f"{_NS_TABLE}table"):
        name = table.attrib.get(f"{_NS_TABLE}name", "")
        if name == _TARGET_SHEET:
            return _parse_table(table)

    raise RuntimeError(f"Sheet '{_TARGET_SHEET}' not found in ODS file")


def _parse_table(table: ET.Element) -> list[dict[str, str]]:
    rows_iter = iter(table.findall(f"{_NS_TABLE}table-row"))
    header_row = next(rows_iter, None)
    if header_row is None:
        return []
    headers = _expand_cells(header_row)

    records: list[dict[str, str]] = []
    for row_el in rows_iter:
        cells = _expand_cells(row_el)
        # Pad or trim to match header length
        while len(cells) < len(headers):
            cells.append("")
        records.append(dict(zip(headers, cells)))
    return records


def _extract_nhs_ratings(records: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    seen: set[str] = set()
    results: list[tuple[str, str, str]] = []
    for rec in records:
        sector = rec.get("Provider Type/Sector", "")
        if "NHS" not in sector:
            continue
        code = rec.get("Provider ID", "").strip()
        if not code or code in seen:
            continue
        rating = rec.get("Location Latest Overall Rating", "").strip()
        if not rating or rating == "Not applicable":
            continue
        name = rec.get("Provider Name", "").strip()
        seen.add(code)
        results.append((code, name, rating))
    return results


def _write_csv(rows: list[tuple[str, str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["provider_code", "provider_name", "overall_rating"])
        writer.writerows(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download CQC ratings to CSV.")
    parser.add_argument("--out", required=True, help="Output CSV path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    print("Discovering CQC ODS URL...")
    url = _discover_ods_url()
    print(f"Downloading: {url}")
    data = _download(url)
    print(f"Downloaded {len(data):,} bytes; parsing...")
    records = _parse_ods(data)
    rows = _extract_nhs_ratings(records)
    print(f"Extracted {len(rows)} NHS provider ratings")
    _write_csv(rows, Path(args.out))
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
