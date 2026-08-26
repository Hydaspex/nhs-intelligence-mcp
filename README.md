# nhs-intelligence-mcp

An MCP server exposing NHS waiting-time and trust-intelligence tools, so an
agentic client (Claude Code, Claude Desktop, or any MCP-compatible host) can
answer open questions about NHS provider performance grounded in real public
data.

The server exposes **data and analysis tools only**; it never calls an LLM. The
agentic reasoning happens in the connecting client, which chains these tools.
That keeps the numbers deterministic and the whole server unit-testable offline.

## Status

Milestone 2. Three tools over two data layers: `wait_time_trend` (RTT monthly
history) plus `lookup_wait_time` and `rank_trusts_by_wait` (My Planned Care
weekly current-state), each end to end with an offline test suite. Remaining
milestones add CQC ratings and a combined trust profile (see
`../nhs-intelligence-mcp-PLAN.md`).

### A note on trust identity

The two data layers name trusts differently. RTT uses a numeric provider code
(e.g. `RGT`); My Planned Care uses the trust name (e.g. `Guy's and St Thomas'`).
Rather than invent a mapping, each tool takes the identity its backing source
actually publishes: `wait_time_trend` a provider code, the current-state tools a
name. Reconciling the two into one identity is deferred to the combined trust
profile (M3), where they must meet. Each tool description states which identity
it expects, so a client picks the right one.

## Design

```
src/nhs_intel/
  domain/      # immutable value objects (WaitTimePoint, TrendResult)
  sources/     # data adapters behind a Protocol (RttCsvSource; fakes in tests)
  analysis/    # pure trend maths, unit-tested against golden expectations
  server.py    # thin FastMCP layer: validate -> pure handler -> serialise
```

The pure core (`domain`, `analysis`) has no I/O and no MCP imports, so it runs in
CI with no network, no key, and no live NHS site. Sources sit behind a `Protocol`
so tests inject in-memory fakes. This is the ports-and-adapters boundary from
`nhs-webscraper`, applied to data feeds.

## Data sources

| Source | Frequency | Role |
| --- | --- | --- |
| NHS England RTT | Monthly | Authoritative trend backbone |
| My Planned Care (via nhs-webscraper) | Weekly | Fresher current-state layer (M2) |
| CQC ratings | Daily | Optional trust-quality context, key-gated (M3) |

## Tools

| Tool | Input | Returns |
| --- | --- | --- |
| `wait_time_trend` | provider_code, specialty | start/end waits, delta, % change, direction, monthly series (RTT) |
| `lookup_wait_time` | provider (name), specialty | latest current wait for one trust (My Planned Care) |
| `rank_trusts_by_wait` | specialty, region?, limit? | trusts ranked by current wait, longest first (My Planned Care) |

Trend direction is decided by a **relative dead-band** (default 5%), so a small
wobble on a long wait reads as `flat` rather than a spurious trend: the same
noise-suppression choice made in the MRR-prediction project. Ranking lists
trusts that publish a specialty but no figure after the ranked ones, so coverage
gaps stay visible rather than being read as a zero wait.

## Running

```bash
pip install -e ".[dev]"

# Point the server at an ingested RTT CSV cache (provider_code,specialty,weeks,as_of):
export NHS_INTEL_RTT_CSV=tests/fixtures/rtt_sample.csv

# Optional: add My Planned Care scraper output for the current-state tools.
# Without it, wait_time_trend still works; the current-state tools report it missing.
export NHS_INTEL_PLANNED_CARE_CSV=tests/fixtures/planned_care_sample.csv

# Run the MCP server over stdio:
nhs-intel-mcp
```

To use it from an MCP client, register `nhs-intel-mcp` as a stdio server with
`NHS_INTEL_RTT_CSV` set in its environment.

## Development

```bash
pip install -e ".[dev]"
pytest        # offline, no network or keys required
ruff check .
```
