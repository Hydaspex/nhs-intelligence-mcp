# nhs-intelligence-mcp

MCP server for NHS waiting times and trust quality. Connects to Claude Code, Claude Desktop, or any MCP-compatible client.

No LLM inside — deterministic data tools only. Reasoning happens in the client.

## Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Hydaspex/nhs-intelligence-mcp/main/scripts/setup.sh)
```

Downloads the latest `nhs_intel.db`, verifies checksum, registers a weekly refresh job, prints the `.mcp.json` snippet.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `lookup_wait_time` | provider name, specialty | latest wait in weeks |
| `rank_trusts_by_wait` | specialty, region?, limit? | trusts ranked longest-first |
| `wait_time_trend` | provider_code, specialty | delta, direction, monthly series |
| `get_trust_rating` | cqc_provider_id | overall + per-domain CQC ratings |
| `trust_profile` | identifier, specialty, by_name? | current wait + trend + CQC rating |

Example: *"Cardiology waiting times at Chelsea and Westminster?"* → 10 weeks, Outstanding (Aug 2026).

## Data sources

| Source | Frequency | Covers |
|---|---|---|
| NHS My Planned Care | Weekly | Current waits — 130 trusts, 74 specialties |
| NHS England RTT | Monthly | Trend data |
| CQC HSCA Active Locations | Monthly | Trust quality ratings |

All ingested into a single SQLite DB, published as a [GitHub release](https://github.com/Hydaspex/nhs-intelligence-mcp/releases/latest). No network calls at query time.

## DB location

| OS | Path |
|---|---|
| Mac | `~/Library/Application Support/nhs-intel/nhs_intel.db` |
| Linux | `~/.local/share/nhs-intel/nhs_intel.db` |
| Windows | `%APPDATA%\nhs-intel\nhs_intel.db` |

Override: `NHS_INTEL_DB=/path/to/nhs_intel.db`

## Architecture

```
src/nhs_intel/
  domain/      # value objects
  sources/     # SQLite-backed adapters
  analysis/    # pure trend, ranking, profile logic
  ingest/      # rtt_ingest, cqc_ingest, load_db CLIs
  server.py    # FastMCP layer
data/schema.sql
scripts/setup.sh, refresh_data.sh
.github/workflows/publish_db.yml
```

## Development

```bash
uv sync --extra dev
uv run pytest

# Populate DB
uv run nhs-intel-load-db --rtt rtt.csv --planned-care planned_care.csv
uv run nhs-intel-cqc-ingest --out /tmp/cqc.csv && uv run nhs-intel-load-db --cqc /tmp/cqc.csv

uv run nhs-intel-mcp
```

## CI

Runs every Sunday 02:00 UTC. Scrapes 131 trusts, downloads RTT + CQC data, publishes `nhs_intel.db` + SHA-256.

Requires `WEBSCRAPER_READ_TOKEN` secret — see [.github/SECRETS.md](.github/SECRETS.md).
