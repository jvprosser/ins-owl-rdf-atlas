"""Server identity tool."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims import server_info
from iceberg_mcp_server_claims.server import get_server_info


def test_content_id_and_version():
    payload = json.loads(get_server_info())
    assert payload["content_id"] == "INS_CLAIMS_MCP_V2"
    assert payload["server"] == "iceberg-mcp-server-claims"
    assert payload["version"] == "0.2.0"
    assert "get_server_info" in payload["registered_tools"]
    assert "get_litigation_view" in payload["registered_tools"]
    assert "write_audit_event" in payload["registered_tools"]


def test_registered_tools_match_constant():
    assert "get_server_info" in server_info.REGISTERED_TOOLS
