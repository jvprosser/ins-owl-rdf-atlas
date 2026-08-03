from __future__ import annotations

from collections.abc import Callable
from typing import Any


class McpToolCaller:
    """Optional injection point for Agent Studio MCP tool invocation.

    ``caller(server, tool_name, **kwargs) -> Any``
    """

    def __init__(self, caller: Callable[..., Any] | None = None) -> None:
        self._caller = caller

    def call(self, server: str, tool_name: str, **kwargs: Any) -> Any:
        if self._caller is None:
            raise NotImplementedError(
                f"MCP caller not bound; cannot invoke {server}.{tool_name}. "
                "Inject a caller from Agent Studio runtime."
            )
        return self._caller(server, tool_name, **kwargs)
