"""Server identity for Agent Studio configuration / restart verification."""

from __future__ import annotations

import json
from importlib import metadata
from typing import Any

# Bump CONTENT_ID whenever shipped MCP behavior/tools change.
CONTENT_ID = "INS_CLAIMS_MCP_V10"
UPDATED = "2026-08-26"

# Keep in sync with @mcp.tool registrations in server.py
REGISTERED_TOOLS = (
    "get_server_info",
    "list_named_queries",
    "run_named_query",
    "run_named_write",
)

FEATURES = (
    "catalog_only_mcp_surface",
    "named_query_catalog",
    "run_named_query",
    "run_named_write",
    "flat_named_query_args",
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
