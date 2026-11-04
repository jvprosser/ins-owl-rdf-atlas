"""MCP server: Impala Iceberg named catalog for underwriting submissions.

Based on cloudera/iceberg-mcp-server (Impala). stdio-safe: no prints to stdout.
Underwriting labels only — no claim or distribution catalog.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from iceberg_mcp_server_underwriting import catalog, server_info

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("iceberg-mcp-server-underwriting")

mcp = FastMCP(name="iceberg-mcp-server-underwriting")


@mcp.tool()
def get_server_info() -> str:
    """One-shot MCP identity check. Call once, report JSON, then stop.

    Do not call again. Do not start underwriting workflows. Just return content_id and version.
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
    submission_id: str | None = None,
    party_id: str | None = None,
    database: str | None = None,
    params_json: str = "{}",
) -> str:
    """Curated READ by catalog label. No free-form SQL.

    Flat Action Input example:
      {"label":"get_submission_spine","claim_id":"SUB-9102"}
    Read labels: get_submission_spine, get_submission_routing_signals,
    get_senior_uw_referral_context, list_underwriter_open_submissions, get_schema.
    claim_id is the submission id. list_underwriter_open_submissions takes party_id.
    """
    return catalog.run_named_query(
        label,
        params_json,
        claim_id=claim_id or submission_id or case_id,
        case_id=case_id,
        submission_id=submission_id,
        party_id=party_id,
        database=database,
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
      {"label":"write_quote_issuance","run_id":"demo-SUB-9103-e2e","event_json":"{\\"claim_id\\":\\"SUB-9103\\"}"}
    Write labels: write_submission_decline, write_quote_issuance,
    write_data_enrichment_request, write_referral_queue, write_audit_event,
    promote_audit_run, begin_agent_audit_run, append_agent_audit_event,
    append_agent_audit_evidence, abandon_agent_audit_run.
    Do not pass premium_cents. The catalog computes the quote.
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
    db = os.getenv("IMPALA_DATABASE", "underwriting")
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    log.info(
        "Starting iceberg-mcp-server-underwriting (transport=%s host=%s db=%s)",
        transport,
        host,
        db,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
