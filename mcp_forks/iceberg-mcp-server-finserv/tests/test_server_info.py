"""Server identity tool."""

from __future__ import annotations

import json

from iceberg_mcp_server_finserv import server_info
from iceberg_mcp_server_finserv.server import get_server_info


def test_content_id_and_version():
    payload = json.loads(get_server_info())
    assert payload["ok"] is True
    assert payload["done"] is True
    assert payload["content_id"] == "INS_FINSERV_MCP_V2"
    assert payload["server"] == "iceberg-mcp-server-finserv"
    assert payload["version"] == "0.2.0"
    assert "distributions_only" in payload["features"]
    assert payload["registered_tools"] == [
        "get_server_info",
        "list_named_queries",
        "run_named_query",
        "run_named_write",
    ]
    assert "execute_query" not in payload["registered_tools"]
    assert "get_claim_spine" not in payload["registered_tools"]
    assert "get_distribution_spine" not in payload["registered_tools"]


def test_registered_tools_match_constant():
    assert server_info.REGISTERED_TOOLS == (
        "get_server_info",
        "list_named_queries",
        "run_named_query",
        "run_named_write",
    )
