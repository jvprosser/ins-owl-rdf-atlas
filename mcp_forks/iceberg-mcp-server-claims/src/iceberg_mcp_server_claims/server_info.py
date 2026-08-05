"""Server identity for Studio paste / restart verification."""

from __future__ import annotations

import json
from importlib import metadata
from typing import Any

# Bump CONTENT_ID whenever shipped MCP behavior/tools change.
CONTENT_ID = "INS_CLAIMS_MCP_V3"
UPDATED = "2026-08-05"

# Keep in sync with @mcp.tool registrations in server.py
REGISTERED_TOOLS = (
    "get_server_info",
    "execute_query",
    "get_schema",
    "get_claim_spine",
    "get_claim_routing_signals",
    "get_litigation_view",
    "get_bi_view",
    "get_subrogation_view",
    "begin_agent_audit_run",
    "append_agent_audit_event",
    "append_agent_audit_evidence",
    "promote_agent_audit_run",
    "abandon_agent_audit_run",
    "write_audit_event",
    "promote_audit_run",
)

FEATURES = (
    "get_claim_spine",
    "get_claim_routing_signals",
    "get_litigation_view",
    "get_bi_view",
    "get_subrogation_view",
    "write_audit_event",
    "promote_audit_run",
    "cte_routing_signals",
    "get_server_info",
)


def package_version() -> str:
    try:
        return metadata.version("iceberg-mcp-server-claims")
    except Exception:
        from iceberg_mcp_server_claims import __version__

        return __version__


def server_info_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "done": True,
        "content_id": CONTENT_ID,
        "server": "iceberg-mcp-server-claims",
        "version": package_version(),
        "updated": UPDATED,
        "features": list(FEATURES),
        "registered_tools": list(REGISTERED_TOOLS),
    }


def get_server_info() -> str:
    return json.dumps(server_info_payload(), indent=2)
