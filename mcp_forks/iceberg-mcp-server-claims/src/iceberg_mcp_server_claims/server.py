"""MCP server: Impala Iceberg tools + claim/audit helpers.

Based on cloudera/iceberg-mcp-server (Impala). Additive tools only.
stdio-safe: no prints to stdout.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from iceberg_mcp_server_claims import catalog, server_info
from iceberg_mcp_server_claims.tools import impala_tools

load_dotenv()

# Never use print() — stdout is the MCP stdio channel.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("iceberg-mcp-server-claims")

mcp = FastMCP(name="iceberg-mcp-server-claims")


# --- Identity / version -----------------------------------------------------


@mcp.tool()
def get_server_info() -> str:
    """One-shot MCP identity check. Call once, report JSON, then stop.

    Do not call again. Do not start claim workflows. Just return content_id and version.
    """
    return server_info.get_server_info()


# --- Named catalog (preferred) ----------------------------------------------


@mcp.tool()
def list_named_queries() -> str:
    """List allow-listed query/write labels. Call once if you need the catalog."""
    return catalog.list_named_queries()


@mcp.tool()
def run_named_query(
    label: str,
    claim_id: str | None = None,
    database: str | None = None,
    params_json: str = "{}",
) -> str:
    """Preferred curated READ. Use this instead of get_litigation_view / get_claim_spine.

    Flat Action Input example:
      {"label":"get_litigation_view","claim_id":"402"}
    Do not call get_litigation_view when this tool is available.
    """
    return catalog.run_named_query(
        label, params_json, claim_id=claim_id, database=database
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
    """Preferred curated WRITE. Use this instead of write_audit_event.

    Flat Action Input example:
      {"label":"write_audit_event","run_id":"demo-402","event_json":"{\\"claim_id\\":\\"402\\"}"}
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


# --- Upstream-compatible Impala tools ---------------------------------------


@mcp.tool()
def execute_query(query: str) -> str:
    """Execute a read-only Impala SQL query. Returns JSON {columns, rows}."""
    return impala_tools.execute_query(query)


@mcp.tool()
def get_schema(database: str | None = None) -> str:
    """List tables. Optional database overrides IMPALA_DATABASE."""
    return catalog.run_named_query("get_schema", database=database)


# --- Claims P0 helpers (catalog aliases; same SQL, stamps named_op) ---------


@mcp.tool()
def get_claim_spine(claim_id: str, database: str | None = None) -> str:
    """Curated claim spine for graph build (claim/loss/policy/vehicle/roles).

    Prefer run_named_query. This alias still stamps named_op.
    """
    return catalog.run_named_query(
        "get_claim_spine", claim_id=claim_id, database=database
    )


@mcp.tool()
def get_claim_routing_signals(claim_id: str, database: str | None = None) -> str:
    """Routing/existence signals (subrogation, litigation, injury, offers, …)."""
    return catalog.run_named_query(
        "get_claim_routing_signals", claim_id=claim_id, database=database
    )


# --- Specialist views (playbook allowed_tools names) ------------------------


@mcp.tool()
def get_litigation_view(claim_id: str, database: str | None = None) -> str:
    """Litigation case facts. Catalog alias of run_named_query."""
    return catalog.run_named_query(
        "get_litigation_view", claim_id=claim_id, database=database
    )


@mcp.tool()
def get_bi_view(claim_id: str, database: str | None = None) -> str:
    """Injury facts. Catalog alias of run_named_query."""
    return catalog.run_named_query("get_bi_view", claim_id=claim_id, database=database)


@mcp.tool()
def get_subrogation_view(claim_id: str, database: str | None = None) -> str:
    """Subrogation case facts. Catalog alias of run_named_query."""
    return catalog.run_named_query(
        "get_subrogation_view", claim_id=claim_id, database=database
    )


# --- Audit helpers (Impala table-append mode) -------------------------------


@mcp.tool()
def begin_agent_audit_run(
    run_id: str,
    database: str | None = None,
    source_branch: str | None = None,
) -> str:
    """Begin an audit run. Impala: table-append mode (no Iceberg WAP branch)."""
    return catalog.run_named_write(
        "begin_agent_audit_run",
        run_id=run_id,
        database=database,
        source_branch=source_branch,
    )


@mcp.tool()
def append_agent_audit_event(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    """Insert one audit event row (JSON object string) for run_id."""
    return catalog.run_named_write(
        "append_agent_audit_event",
        run_id=run_id,
        event_json=event_json,
        database=database,
    )


@mcp.tool()
def append_agent_audit_evidence(
    run_id: str,
    evidence_json: str,
    database: str | None = None,
) -> str:
    """Insert one audit evidence row (JSON object string) for run_id."""
    return catalog.run_named_write(
        "append_agent_audit_evidence",
        run_id=run_id,
        evidence_json=evidence_json,
        database=database,
    )


@mcp.tool()
def promote_agent_audit_run(run_id: str, database: str | None = None) -> str:
    """Promote audit run. Impala: no-op (rows already on main)."""
    return catalog.run_named_write(
        "promote_agent_audit_run", run_id=run_id, database=database
    )


@mcp.tool()
def abandon_agent_audit_run(run_id: str, database: str | None = None) -> str:
    """Abandon audit run by deleting rows for run_id (best effort)."""
    return catalog.run_named_write(
        "abandon_agent_audit_run", run_id=run_id, database=database
    )


@mcp.tool()
def write_audit_event(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    """Playbook write_audit_event. Catalog alias of run_named_write."""
    return catalog.run_named_write(
        "write_audit_event",
        run_id=run_id,
        event_json=event_json,
        database=database,
    )


@mcp.tool()
def promote_audit_run(run_id: str, database: str | None = None) -> str:
    """Playbook promote_audit_run. Catalog alias of run_named_write."""
    return catalog.run_named_write(
        "promote_audit_run", run_id=run_id, database=database
    )


def main() -> None:
    host = os.getenv("IMPALA_HOST", "(unset)")
    db = os.getenv("IMPALA_DATABASE", "default")
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    log.info(
        "Starting iceberg-mcp-server-claims (transport=%s host=%s db=%s)",
        transport,
        host,
        db,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
