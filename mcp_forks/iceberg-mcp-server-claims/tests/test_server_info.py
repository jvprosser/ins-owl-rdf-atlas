"""Server identity tool."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims import server_info
from iceberg_mcp_server_claims.server import get_server_info


def test_content_id_and_version():
    payload = json.loads(get_server_info())
    assert payload["ok"] is True
    assert payload["done"] is True
    assert payload["content_id"] == "INS_CLAIMS_MCP_V7"
    assert payload["server"] == "iceberg-mcp-server-claims"
    assert payload["version"] == "0.3.5"
    assert "catalog_only_mcp_surface" in payload["features"]
    assert payload["registered_tools"] == [
        "get_server_info",
        "list_named_queries",
        "run_named_query",
        "run_named_write",
    ]
    assert "execute_query" not in payload["registered_tools"]
    assert "get_litigation_view" not in payload["registered_tools"]
    assert "notes" not in payload


def test_registered_tools_match_constant():
    assert server_info.REGISTERED_TOOLS == (
        "get_server_info",
        "list_named_queries",
        "run_named_query",
        "run_named_write",
    )
    assert "get_server_info" in server_info.REGISTERED_TOOLS
