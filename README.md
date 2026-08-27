# nhs-intelligence-mcp

An MCP server exposing NHS waiting-time and trust-intelligence tools, so an
agentic client (Claude Code, Claude Desktop, or any MCP-compatible host) can
answer questions about NHS provider performance grounded in real public data.

The server exposes **data and analysis tools only**; it never calls an LLM. The
agentic reasoning happens in the connecting client, which chains these tools.
That keeps the numbers deterministic and the whole server unit-testable offline.

## Quick start (new users)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Hydaspex/nhs-intelligence-mcp/main/scripts/setup.sh)
```

This one command:
1. Downloads the latest pre-built `nhs_intel.db` from the GitHub release
2. Verifies its SHA-256 checksum
3. Registers a weekly refresh job (launchd on Mac, cron on Linux)
4. Prints the `.mcp.json` snippet to add to Claude Code

Data is refreshed automatically every Sunday — no Playwright, no scraper needed on your machine.

## Data sources

| Source | Frequency | Tool |
|---|---|---|
| NHS My Planned Care (via [nhs-webscraper](https://github.com/Hydaspex/nhs-webscraper)) | Weekly | current wait lookup & ranking |
| NHS England RTT Incomplete Provider | Monthly | waiting-time trend |
| CQC HSCA Active Locations | Monthly | trust quality rating |

All three sources are ingested into a single SQLite database (`nhs_intel.db`) by
the CI pipeline and published as a [GitHub release asset](https://github.com/Hydaspex/nhs-intelligence-mcp/releases/latest).
The MCP server reads only from this DB — no network calls at query time.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `lookup_wait_time` | provider name, specialty | latest wait in weeks (My Planned Care) |
| `rank_trusts_by_wait` | specialty, region?, limit? | trusts ranked longest-first (My Planned Care) |
| `wait_time_trend` | provider_code, specialty | start/end waits, delta, direction, monthly series (RTT) |
| `get_trust_rating` | cqc_provider_id | overall and per-domain CQC ratings |
| `trust_profile` | identifier, specialty, by_name? | combined current wait + trend + CQC rating |

Example query in Claude Code:

> *"What are the waiting times at Chelsea and Westminster for cardiology?"*

Returns: **10 weeks** current wait, **Outstanding** CQC rating (as of Aug 2026).

## Architecture

```
src/nhs_intel/
  domain/      # immutable value objects (WaitTimePoint, TrustRating, ...)
  sources/     # SQLite-backed adapters behind Protocols
  analysis/    # pure trend, ranking and profile-join logic
  ingest/      # CLI tools: rtt_ingest, cqc_ingest, load_db
  server.py    # thin FastMCP layer: validate → pure handler → serialise
data/
  schema.sql   # tracked; nhs_intel.db is gitignored (download via setup.sh)
scripts/
  setup.sh     # one-command installer for new users
  refresh_data.sh  # weekly curl + checksum update (registered by setup.sh)
.github/workflows/
  publish_db.yml  # weekly CI: scrape → ingest → publish release
```

Pure core (`domain`, `analysis`) has no I/O and no MCP imports — fully testable
offline. Every source sits behind a `Protocol`; tests inject in-memory fakes.

## Database

The SQLite DB has three tables:

| Table | Source | Key columns |
|---|---|---|
| `planned_care` | My Planned Care scraper | region, provider, specialty, average_wait_weeks |
| `rtt` | NHS England RTT XLSX | provider_code, specialty, weeks, as_of |
| `identity` | Join table | provider_code, planned_care_name, overall_rating |

The `identity` table joins RTT provider codes ↔ My Planned Care display names ↔
CQC ratings, built by fuzzy-matching provider names and loading CQC ratings from
the HSCA ODS file.

## DB path

The DB is stored in the platform user-data directory:

| OS | Path |
|---|---|
| Mac | `~/Library/Application Support/nhs-intel/nhs_intel.db` |
| Linux | `~/.local/share/nhs-intel/nhs_intel.db` |
| Windows | `%APPDATA%\nhs-intel\nhs_intel.db` |

Override with `NHS_INTEL_DB=/path/to/nhs_intel.db`.

## Development

```bash
# Install deps
uv sync --extra dev

# Run tests (offline, no network required)
uv run pytest

# Populate DB from local data files
uv run nhs-intel-load-db \
  --rtt /path/to/rtt_latest.csv \
  --planned-care /path/to/planned_care_latest.csv \
  --identity /path/to/identity.csv

# Download and load CQC ratings
uv run nhs-intel-cqc-ingest --out /tmp/cqc_ratings.csv
uv run nhs-intel-load-db --cqc /tmp/cqc_ratings.csv

# Run the MCP server
uv run nhs-intel-mcp
```

## CI pipeline

The GitHub Actions workflow (`.github/workflows/publish_db.yml`) runs every
Sunday at 02:00 UTC:

1. Checks out this repo and [nhs-webscraper](https://github.com/Hydaspex/nhs-webscraper)
2. Scrapes all 131 NHS trusts from My Planned Care (`--concurrency 2`)
3. Downloads the latest RTT XLSX from NHS England
4. Downloads the CQC HSCA Active Locations ODS
5. Loads all three into `nhs_intel.db`
6. Publishes `nhs_intel.db` + SHA-256 checksum as a versioned release asset

Required secret: `WEBSCRAPER_READ_TOKEN` — a fine-grained PAT with read-only
access to the `nhs-webscraper` repo. See [.github/SECRETS.md](.github/SECRETS.md).
