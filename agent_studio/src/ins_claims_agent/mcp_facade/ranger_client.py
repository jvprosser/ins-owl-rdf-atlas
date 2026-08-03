"""Facade for ranger-mcp-server (upstream, not forked in Phase 1)."""

from __future__ import annotations

from typing import Any

from .base import McpToolCaller

SERVER = "ranger-mcp-server"


class RangerFacade(McpToolCaller):
    """Ranger access, masking, and audit-log tools."""

    def create_access_policy(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "create_access_policy", **kwargs)

    def create_masking_policy(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "create_masking_policy", **kwargs)

    def create_tag_based_policy(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "create_tag_based_policy", **kwargs)

    def search_ranger_policies(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "search_ranger_policies", **kwargs)

    def search_access_audits(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "search_access_audits", **kwargs)

    def count_access_audits(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "count_access_audits", **kwargs)

    def search_admin_audit_logs(self, **kwargs: Any) -> Any:
        return self.call(SERVER, "search_admin_audit_logs", **kwargs)
