# nhs-intelligence-mcp

An MCP server exposing NHS waiting-time and trust-intelligence tools, so an
agentic client (Claude Code, Claude Desktop, or any MCP-compatible host) can
answer open questions about NHS provider performance grounded in real public
data.

The server exposes **data and analysis tools only**; it never calls an LLM. The
agentic reasoning happens in the connecting client, which chains these tools.
That keeps the numbers deterministic and the whole server unit-testable offline.

## Status

Milestone 1: a runnable vertical slice. One tool, `wait_time_trend`, backed by
NHS England RTT data, end to end, with an offline test suite. Later milestones
add the weekly My Planned Care current-state layer, CQC ratings, ranking, and a
combined trust profile (see `../nhs-intelligence-mcp-PLAN.md`).

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
| `wait_time_trend` | provider_code, specialty | start/end waits, delta, % change, direction, monthly series |

Direction is decided by a **relative dead-band** (default 5%), so a small wobble
on a long wait reads as `flat` rather than a spurious trend — the same
noise-suppression choice made in the MRR-prediction project.

## Running

```bash
pip install -e ".[dev]"

# Point the server at an ingested RTT CSV cache (provider_code,specialty,weeks,as_of):
export NHS_INTEL_RTT_CSV=tests/fixtures/rtt_sample.csv

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
