"""Server identity tool."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims import server_info
from iceberg_mcp_server_claims.server import get_server_info


def test_content_id_and_version():
    payload = json.loads(get_server_info())
    assert payload["ok"] is True
    assert payload["done"] is True
    assert payload["content_id"] == "INS_CLAIMS_MCP_V6"
    assert payload["server"] == "iceberg-mcp-server-claims"
    assert payload["version"] == "0.3.2"
    assert "legacy_tools_via_catalog" in payload["features"]
    assert "run_named_query" in payload["registered_tools"]
    assert "list_named_queries" in payload["registered_tools"]
    assert "named_query_catalog" in payload["features"]
    assert "notes" not in payload


def test_registered_tools_match_constant():
    assert "get_server_info" in server_info.REGISTERED_TOOLS
