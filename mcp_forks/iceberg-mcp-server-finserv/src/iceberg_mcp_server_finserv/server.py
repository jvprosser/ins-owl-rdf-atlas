"""MCP server: Impala Iceberg named catalog for retirement distributions.

Based on cloudera/iceberg-mcp-server (Impala). stdio-safe: no prints to stdout.
Distributions labels only — no claim or rollover catalog.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from iceberg_mcp_server_finserv import catalog, server_info

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("iceberg-mcp-server-finserv")

mcp = FastMCP(name="iceberg-mcp-server-finserv")


@mcp.tool()
def get_server_info() -> str:
    """One-shot MCP identity check. Call once, report JSON, then stop.

    Do not call again. Do not start distribution workflows. Just return content_id and version.
    """
    return server_info.get_server_info()


@mcp.tool()
def list_named_queries() -> str:
    """List allow-listed query/write labels. Call once if you need the catalog."""
    return catalog.list_named_queries()


@mcp.tool()
def run_named_query(
    label: str,
    claim_id: str | None = None,
    case_id: str | None = None,
    database: str | None = None,
    params_json: str = "{}",
) -> str:
    """Curated READ by catalog label. No free-form SQL.

    Flat Action Input example:
      {"label":"get_distribution_spine","claim_id":"7002"}
    Read labels: get_distribution_spine, get_distribution_routing_signals,
    get_distribution_exception_view, get_rmd_view, get_schema.
    """
    return catalog.run_named_query(
        label, params_json, claim_id=claim_id or case_id, case_id=case_id, database=database
    )


@mcp.tool()
def run_named_write(
    label: str,
    run_id: str | None = None,
    event_json: str | None = None,
    evidence_json: str | None = None,
    database: str | None = None,
    source_branch: str | None = None,
    params_json: str = "{}",
) -> str:
    """Curated WRITE by catalog label.

    Flat Action Input example:
      {"label":"write_audit_event","run_id":"demo-7002","event_json":"{\\"claim_id\\":\\"7002\\"}"}
    Write labels: write_audit_event, promote_audit_run, begin_agent_audit_run,
    append_agent_audit_event, append_agent_audit_evidence, abandon_agent_audit_run.
    """
    return catalog.run_named_write(
        label,
        params_json,
        run_id=run_id,
        event_json=event_json,
        evidence_json=evidence_json,
        database=database,
        source_branch=source_branch,
    )


def main() -> None:
    host = os.getenv("IMPALA_HOST", "(unset)")
    db = os.getenv("IMPALA_DATABASE", "retirement_distributions")
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    log.info(
        "Starting iceberg-mcp-server-finserv (transport=%s host=%s db=%s)",
        transport,
        host,
        db,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
