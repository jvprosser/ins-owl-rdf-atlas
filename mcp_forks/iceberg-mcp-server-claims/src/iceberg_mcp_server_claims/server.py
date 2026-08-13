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
from iceberg_mcp_server_claims.tools import audit_tools, claim_tools, impala_tools, view_tools

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
def run_named_query(label: str, params_json: str = "{}") -> str:
    """Run a curated READ by catalog label. Do not invent SQL.

    params_json is a JSON object string, e.g. {\"claim_id\":\"402\"}.
    Read labels: get_claim_spine, get_claim_routing_signals, get_litigation_view,
    get_bi_view, get_subrogation_view, get_schema.
    """
    return catalog.run_named_query(label, params_json)


@mcp.tool()
def run_named_write(label: str, params_json: str = "{}") -> str:
    """Run a curated WRITE by catalog label. Do not invent SQL.

    params_json is a JSON object string, e.g.
    {\"run_id\":\"demo-402\",\"event_json\":{...}}.
    Write labels: write_audit_event, append_agent_audit_event,
    append_agent_audit_evidence, begin_agent_audit_run, promote_audit_run,
    promote_agent_audit_run, abandon_agent_audit_run.
    """
    return catalog.run_named_write(label, params_json)


# --- Upstream-compatible Impala tools ---------------------------------------


@mcp.tool()
def execute_query(query: str) -> str:
    """Execute a read-only Impala SQL query. Returns JSON {columns, rows}."""
    return impala_tools.execute_query(query)


@mcp.tool()
def get_schema(database: str | None = None) -> str:
    """List tables. Optional database overrides IMPALA_DATABASE."""
    return impala_tools.get_schema(database)


# --- Claims P0 helpers ------------------------------------------------------


@mcp.tool()
def get_claim_spine(claim_id: str, database: str | None = None) -> str:
    """Curated claim spine for graph build (claim/loss/policy/vehicle/roles).

    Prefer this over free-form execute_query joins.
    """
    return claim_tools.get_claim_spine(claim_id, database)


@mcp.tool()
def get_claim_routing_signals(claim_id: str, database: str | None = None) -> str:
    """Routing/existence signals (subrogation, litigation, injury, offers, …)."""
    return claim_tools.get_claim_routing_signals(claim_id, database)


# --- Specialist views (playbook allowed_tools names) ------------------------


@mcp.tool()
def get_litigation_view(claim_id: str, database: str | None = None) -> str:
    """Litigation case facts for LitigationAgent."""
    return view_tools.get_litigation_view(claim_id, database)


@mcp.tool()
def get_bi_view(claim_id: str, database: str | None = None) -> str:
    """Injury facts for BiClaimsAgent."""
    return view_tools.get_bi_view(claim_id, database)


@mcp.tool()
def get_subrogation_view(claim_id: str, database: str | None = None) -> str:
    """Subrogation case facts for SubrogationAgent."""
    return view_tools.get_subrogation_view(claim_id, database)


# --- Audit helpers (Impala table-append mode) -------------------------------


@mcp.tool()
def begin_agent_audit_run(
    run_id: str,
    database: str | None = None,
    source_branch: str | None = None,
) -> str:
    """Begin an audit run. Impala: table-append mode (no Iceberg WAP branch)."""
    return audit_tools.begin_agent_audit_run(run_id, database, source_branch)


@mcp.tool()
def append_agent_audit_event(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    """Insert one audit event row (JSON object string) for run_id."""
    return audit_tools.append_agent_audit_event(run_id, event_json, database)


@mcp.tool()
def append_agent_audit_evidence(
    run_id: str,
    evidence_json: str,
    database: str | None = None,
) -> str:
    """Insert one audit evidence row (JSON object string) for run_id."""
    return audit_tools.append_agent_audit_evidence(run_id, evidence_json, database)


@mcp.tool()
def promote_agent_audit_run(run_id: str, database: str | None = None) -> str:
    """Promote audit run. Impala: no-op (rows already on main)."""
    return audit_tools.promote_agent_audit_run(run_id, database)


@mcp.tool()
def abandon_agent_audit_run(run_id: str, database: str | None = None) -> str:
    """Abandon audit run by deleting rows for run_id (best effort)."""
    return audit_tools.abandon_agent_audit_run(run_id, database)


# Playbook-aligned aliases (same impl; names match route allowed_tools)


@mcp.tool()
def write_audit_event(
    run_id: str,
    event_json: str,
    database: str | None = None,
) -> str:
    """Alias for append_agent_audit_event (playbook: write_audit_event)."""
    return audit_tools.append_agent_audit_event(run_id, event_json, database)


@mcp.tool()
def promote_audit_run(run_id: str, database: str | None = None) -> str:
    """Alias for promote_agent_audit_run (playbook: promote_audit_run)."""
    return audit_tools.promote_agent_audit_run(run_id, database)


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
