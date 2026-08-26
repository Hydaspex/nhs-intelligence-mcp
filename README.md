# nhs-intelligence-mcp

An MCP server exposing NHS waiting-time and trust-intelligence tools, so an
agentic client (Claude Code, Claude Desktop, or any MCP-compatible host) can
answer open questions about NHS provider performance grounded in real public
data.

The server exposes **data and analysis tools only**; it never calls an LLM. The
agentic reasoning happens in the connecting client, which chains these tools.
That keeps the numbers deterministic and the whole server unit-testable offline.

## Status

Milestone 3. Five tools over three data sources: RTT trend, My Planned Care
current-state (lookup and ranking), CQC quality ratings, and a combined
`trust_profile` that joins all three. Each is end to end with an offline test
suite (57 tests).

### A note on trust identity

The three sources name trusts differently: RTT uses a numeric provider code
(e.g. `RGT`), My Planned Care uses the trust name (e.g. `Guy's and St Thomas'`),
CQC uses its own provider id (e.g. `1-101681210`). The single-source tools take
the identity their source publishes. `trust_profile` reconciles the three from a
curated mapping file; a trust absent from the mapping returns `found=false`.
Rating data is supplementary: if the CQC feed is unreachable, the profile drops
that one section and still returns the wait and trend data.

## Design

```
src/nhs_intel/
  domain/      # immutable value objects (WaitTimePoint, TrustRating, ...)
  sources/     # adapters behind Protocols (CSV feeds, CQC HTTP, identity map)
  analysis/    # pure trend, ranking and profile-join logic
  server.py    # thin FastMCP layer: validate -> pure handler -> serialise
```

The pure core (`domain`, `analysis`) has no I/O and no MCP imports, so it runs in
CI with no network and no live NHS feed. Every source sits behind a `Protocol`,
including the CQC HTTP client, so tests inject in-memory fakes and the suite is
fully offline. This is the ports-and-adapters boundary from `nhs-webscraper`,
applied to data feeds.

## Data sources

| Source | Frequency | Role | Access |
| --- | --- | --- | --- |
| NHS England RTT | Monthly | Trend backbone | CSV cache |
| My Planned Care (via nhs-webscraper) | Weekly | Current-state layer | CSV |
| CQC ratings | Daily | Trust-quality context | Public API, no key |

## Tools

| Tool | Input | Returns |
| --- | --- | --- |
| `wait_time_trend` | provider_code, specialty | start/end waits, delta, % change, direction, monthly series (RTT) |
| `lookup_wait_time` | provider (name), specialty | latest current wait for one trust (My Planned Care) |
| `rank_trusts_by_wait` | specialty, region?, limit? | trusts ranked by current wait, longest first (My Planned Care) |
| `get_trust_rating` | cqc_provider_id | overall and per-domain CQC ratings |
| `trust_profile` | identifier, specialty, by_name? | combined current wait, trend, and rating for one trust |

Trend direction is decided by a **relative dead-band** (default 5%), so a small
wobble on a long wait reads as `flat` rather than a spurious trend: the same
noise-suppression choice made in the MRR-prediction project. Ranking lists
trusts that publish a specialty but no figure after the ranked ones, keeping
coverage gaps visible and distinct from a zero wait.

## Running

Dependencies are managed with [uv](https://docs.astral.sh/uv/) and locked in
`uv.lock`; a plain `requirements.txt` is exported alongside it for anyone
without `uv`.

```bash
# uv resolves and creates .venv automatically from uv.lock:
uv sync --extra dev

# Point the server at an ingested RTT CSV cache (provider_code,specialty,weeks,as_of):
export NHS_INTEL_RTT_CSV=tests/fixtures/rtt_sample.csv

# Optional: My Planned Care scraper output for the current-state tools.
export NHS_INTEL_PLANNED_CARE_CSV=tests/fixtures/planned_care_sample.csv

# Optional: cross-source identity mapping for trust_profile.
export NHS_INTEL_IDENTITY_CSV=tests/fixtures/identity_sample.csv

# Optional: a partnerCode string sent with CQC requests to identify your caller.
export NHS_INTEL_CQC_PARTNER_CODE=my-org

# Run the MCP server over stdio:
uv run nhs-intel-mcp
```

Without `uv`: `pip install -r requirements.txt` then run `nhs-intel-mcp`
directly, with the same environment variables set.

Only `NHS_INTEL_RTT_CSV` is required; each tool reports clearly when its source
is unconfigured, and the CQC feed degrades to an absent rating section when
unreachable. `.mcp.json` registers the server for Claude Code using `uv run`,
so the project's own environment is used regardless of what is active in the
calling shell.

## Development

```bash
uv sync --extra dev
uv run pytest    # offline, no network or keys required
uv run ruff check .
```
