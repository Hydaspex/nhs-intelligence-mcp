"""FastMCP server exposing NHS wait-time intelligence tools.

The server is a thin layer: each tool validates input, calls one pure analysis
function over a source, and serialises the result. No business logic lives here,
and the server never calls an LLM: the agentic reasoning happens in whichever
MCP client connects and chains these tools.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from nhs_intel.analysis import compute_trend, rank_by_wait
from nhs_intel.config import Settings
from nhs_intel.sources import PlannedCareCsvSource, RttCsvSource
from nhs_intel.sources.protocol import CurrentWaitSource, WaitTimeSource

mcp = FastMCP("nhs-intelligence")


def _default_source() -> WaitTimeSource:
    """Build the configured historical wait-time (RTT) source.

    Configuration is resolved lazily (only when a tool actually runs) so the
    module imports cleanly and the tool list stays inspectable without a data
    file present.
    """
    return RttCsvSource(Settings.from_env().rtt_csv_path)


def _default_current_source() -> CurrentWaitSource:
    """Build the configured current-state (My Planned Care) source."""
    return PlannedCareCsvSource(Settings.from_env().require_planned_care())


def _not_found(provider_code: str, specialty: str, reason: str) -> dict[str, Any]:
    """The single ``found=false`` shape, so every not-found path matches."""
    return {
        "found": False,
        "provider_code": provider_code,
        "specialty": specialty,
        "reason": reason,
    }


def _trend_payload(
    provider_code: str,
    specialty: str,
    source: WaitTimeSource,
) -> dict[str, Any]:
    """Pure request handler: source in, serialisable payload out.

    Kept separate from the MCP tool so it can be unit-tested with an injected
    fake source. The ``source`` seam stays out of the model-facing tool schema,
    where a Protocol parameter would neither serialise nor make sense to expose.
    Serialisation of a found trend lives on ``TrendResult.to_payload``.
    """
    points = source.series(provider_code, specialty)

    if not points:
        return _not_found(provider_code, specialty, "no data")
    if len(points) < 2:
        return _not_found(
            provider_code, specialty, "only one data point; cannot form a trend"
        )

    return compute_trend(points).to_payload()


@mcp.tool(
    description=(
        "Summarise how the waiting time for a given NHS trust and specialty has "
        "moved over time, using NHS England RTT monthly data. Waits are in weeks. "
        "Provide the provider code (e.g. 'RGT') and specialty (e.g. 'Cardiology'). "
        "Returns the start and end values, the change in weeks, the percentage "
        "change, a direction (improving | worsening | flat), and the full monthly "
        "series. If no data is held for that trust/specialty, returns "
        "found=false; do not invent a trend in that case."
    )
)
def wait_time_trend(provider_code: str, specialty: str) -> dict[str, Any]:
    """MCP tool: trend for a trust/specialty from the configured source."""
    return _trend_payload(provider_code, specialty, _default_source())


def _lookup_payload(
    provider: str,
    specialty: str,
    source: CurrentWaitSource,
) -> dict[str, Any]:
    """Pure handler for the current-wait lookup (fake-injectable in tests)."""
    record = source.latest(provider, specialty)
    if record is None:
        return {
            "found": False,
            "provider": provider,
            "specialty": specialty,
            "reason": "no current data",
        }
    return {"found": True, **record.to_payload()}


def _ranking_payload(
    specialty: str,
    source: CurrentWaitSource,
    region: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Pure handler for ranking trusts by current wait (longest first)."""
    ranked = rank_by_wait(source.for_specialty(specialty, region))
    if limit is not None:
        ranked = ranked[:limit]
    return {
        "specialty": specialty,
        "region": region,
        "count": len(ranked),
        "trusts": [record.to_payload() for record in ranked],
    }


@mcp.tool(
    description=(
        "Look up the latest reported waiting time for one NHS trust and specialty "
        "from My Planned Care (updated weekly). Waits are in whole weeks. Provide "
        "the trust name as published (e.g. 'Guy's and St Thomas'') and the "
        "specialty (e.g. 'Cardiology'). Returns found=false if the trust/specialty "
        "is not held; do not invent a figure. Note the trust is identified by "
        "name here, unlike wait_time_trend which uses an RTT provider code."
    )
)
def lookup_wait_time(provider: str, specialty: str) -> dict[str, Any]:
    """MCP tool: latest current wait for a trust/specialty."""
    return _lookup_payload(provider, specialty, _default_current_source())


@mcp.tool(
    description=(
        "Rank NHS trusts by their latest waiting time for a specialty (longest "
        "first), using My Planned Care weekly data. Provide the specialty; "
        "optionally restrict to a region and cap the number of trusts returned. "
        "Trusts that publish the specialty but no wait figure are listed after "
        "the ranked ones, so coverage gaps are visible rather than hidden."
    )
)
def rank_trusts_by_wait(
    specialty: str,
    region: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """MCP tool: trusts ranked by current wait for a specialty."""
    return _ranking_payload(specialty, _default_current_source(), region, limit)


def main() -> None:
    """Run the server over stdio (the default MCP transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
