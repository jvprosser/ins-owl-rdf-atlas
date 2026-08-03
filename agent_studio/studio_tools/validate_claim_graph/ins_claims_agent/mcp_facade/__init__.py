"""Thin facades over Iceberg / Atlas / Ranger MCP servers.

Agent Studio registers the MCP servers; these modules document and wrap the
tool names the Python tools should call. Until runtime MCP bindings are injected,
methods raise NotImplementedError or accept an injected client.
"""

from .adapter import bind_facades, from_agent_studio_mcp, from_namespaced_invoker, from_tool_map
from .atlas_client import AtlasFacade
from .iceberg_client import IcebergFacade
from .ranger_client import RangerFacade

__all__ = [
    "AtlasFacade",
    "IcebergFacade",
    "RangerFacade",
    "bind_facades",
    "from_agent_studio_mcp",
    "from_namespaced_invoker",
    "from_tool_map",
]
