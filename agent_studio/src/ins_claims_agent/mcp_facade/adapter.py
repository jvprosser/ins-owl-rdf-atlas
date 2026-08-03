"""Adapters that bind Agent Studio (or test) MCP invokers to facade callers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


Caller = Callable[..., Any]


def bind_facades(caller: Caller, *facades: Any) -> Caller:
    """Inject ``caller(server, tool_name, **kwargs)`` into one or more facades."""
    for facade in facades:
        facade._caller = caller
    return caller


def from_namespaced_invoker(
    invoke: Callable[[str, Mapping[str, Any]], Any],
    *,
    server_aliases: Mapping[str, str] | None = None,
) -> Caller:
    """Adapt ``invoke("server.tool", args)`` → ``caller(server, tool, **kwargs)``.

    ``server_aliases`` remaps logical facade server ids to Agent Studio registration
    names when they differ (e.g. fork package name).
    """
    aliases = dict(server_aliases or {})

    def caller(server: str, tool_name: str, **kwargs: Any) -> Any:
        registered = aliases.get(server, server)
        return invoke(f"{registered}.{tool_name}", kwargs)

    return caller


def from_tool_map(tools: Mapping[str, Callable[..., Any]]) -> Caller:
    """Test helper: map ``\"server.tool\"`` → callable(**kwargs)."""

    def caller(server: str, tool_name: str, **kwargs: Any) -> Any:
        key = f"{server}.{tool_name}"
        if key not in tools:
            raise LookupError(f"Unknown tool: {key}")
        return tools[key](**kwargs)

    return caller


def from_agent_studio_mcp(
    call_tool: Callable[..., Any],
    *,
    arg_style: str = "kwargs",
) -> Caller:
    """Adapt a typical Agent Studio MCP bridge.

    Supported ``call_tool`` shapes:
    - ``call_tool(server, tool_name, **kwargs)`` when ``arg_style=\"kwargs\"``
    - ``call_tool(server, tool_name, arguments=dict)`` when ``arg_style=\"arguments\"``
    """

    def caller(server: str, tool_name: str, **kwargs: Any) -> Any:
        if arg_style == "arguments":
            return call_tool(server, tool_name, arguments=kwargs)
        return call_tool(server, tool_name, **kwargs)

    return caller
