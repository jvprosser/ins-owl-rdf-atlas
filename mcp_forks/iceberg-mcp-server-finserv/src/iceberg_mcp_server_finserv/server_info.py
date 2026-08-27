"""Server identity for Agent Studio configuration / restart verification."""

from __future__ import annotations

import json
from importlib import metadata
from typing import Any

CONTENT_ID = "INS_FINSERV_MCP_V2"
UPDATED = "2026-08-26"

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
    "distributions_only",
)


def package_version() -> str:
    try:
        return metadata.version("iceberg-mcp-server-finserv")
    except Exception:
        from iceberg_mcp_server_finserv import __version__

        return __version__


def server_info_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "done": True,
        "content_id": CONTENT_ID,
        "server": "iceberg-mcp-server-finserv",
        "version": package_version(),
        "updated": UPDATED,
        "features": list(FEATURES),
        "registered_tools": list(REGISTERED_TOOLS),
    }


def get_server_info() -> str:
    return json.dumps(server_info_payload(), indent=2)
