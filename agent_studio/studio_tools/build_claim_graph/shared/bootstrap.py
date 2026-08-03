"""Shared bootstrap for Agent Studio claim tools."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


def _detect_roots(tool_file: Optional[Path] = None) -> tuple[Path, Path, Path]:
    """Return (import_root, package_src, runtime_assets).

    Supports:
    - Repo layout: ``studio_tools/{tool}/tool.py`` + ``studio_tools/shared`` + ``../src``
    - Bundled layout: ``{tool}/tool.py`` with vendored ``shared/``, ``ins_claims_agent/``, ``runtime_assets/``
    """
    if tool_file is not None:
        tool_dir = tool_file.resolve().parent
        if (tool_dir / "ins_claims_agent").is_dir() and (tool_dir / "runtime_assets").is_dir():
            return tool_dir, tool_dir, tool_dir / "runtime_assets"
        studio = tool_dir.parent
        return studio, studio.parent / "src", studio / "runtime_assets"

    # shared/bootstrap.py
    shared_dir = Path(__file__).resolve().parent
    parent = shared_dir.parent
    if (parent / "ins_claims_agent").is_dir() and (parent / "runtime_assets").is_dir():
        # Vendored: shared/ lives inside the tool bundle root
        return parent, parent, parent / "runtime_assets"
    # Repo: shared/ lives under studio_tools/
    return parent, parent.parent / "src", parent / "runtime_assets"


def ensure_sys_path(tool_file: Optional[Path] = None) -> None:
    """Make ``ins_claims_agent`` and ``shared`` imports available."""
    import_root, package_src, _assets = _detect_roots(tool_file)
    for path in (package_src, import_root):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def configure_assets_root(
    assets_root: Optional[str] = None, tool_file: Optional[Path] = None
) -> Path:
    """Point path discovery at bundled ontology/probes/playbook."""
    _import_root, _src, default_assets = _detect_roots(tool_file)
    root = Path(assets_root).expanduser().resolve() if assets_root else default_assets
    if not (root / "ontology" / "claims_mvt.ttl").is_file():
        raise FileNotFoundError(
            f"Assets root missing ontology/claims_mvt.ttl: {root}. "
            "Bundle runtime_assets or set assets_root / INS_CLAIMS_REPO_ROOT."
        )
    os.environ["INS_CLAIMS_REPO_ROOT"] = str(root)
    return root


def graph_artifact_path(claim_id: str | int) -> Path:
    """Workspace-relative graph artifact (Agent Studio cwd is /workspace)."""
    return Path(f"claim_{claim_id}_graph.ttl")


def decision_artifact_path(claim_id: str | int) -> Path:
    return Path(f"claim_{claim_id}_route.json")


def write_json_artifact(path: Path, data: Any) -> str:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return str(path.resolve())


class HiveUserParameters(BaseModel):
    """HiveServer2 settings (same env surface as iceberg-mcp-server-hive)."""

    hive_host: str = Field(description="HiveServer2 / Knox host")
    hive_user: str = Field(description="LDAP / service user")
    hive_password: str = Field(description="Hive password")
    hive_port: int = Field(default=443, description="HS2 port (443 for Knox HTTP)")
    hive_database: str = Field(
        default="car_insurance_claims",
        description="Default Hive database for connection",
    )
    hive_auth_mechanism: str = Field(default="LDAP")
    hive_use_http_transport: bool = Field(default=True)
    hive_http_path: str = Field(default="cliservice")
    hive_use_ssl: bool = Field(default=True)
    claims_database: str = Field(
        default="car_insurance_claims",
        description="Database containing claim spine tables",
    )
    assets_root: Optional[str] = Field(
        default=None,
        description="Optional override for ontology/probes/playbook root",
    )


class AssetsOnlyUserParameters(BaseModel):
    """Config for tools that only need graph artifacts + Git assets."""

    assets_root: Optional[str] = Field(
        default=None,
        description="Optional override for ontology/probes/playbook root",
    )


def bind_iceberg_from_hive(
    config: HiveUserParameters, tool_file: Optional[Path] = None
) -> Any:
    """Bind IcebergFacade to direct Hive SQL (MCP execute_query equivalent)."""
    ensure_sys_path(tool_file)
    configure_assets_root(config.assets_root, tool_file=tool_file)

    from ins_claims_agent.mcp_facade import IcebergFacade, from_tool_map
    from shared.hive_caller import make_execute_query

    execute_query = make_execute_query(config)
    tools = {
        "iceberg-mcp-server-hive.execute_query": execute_query,
    }
    return IcebergFacade(from_tool_map(tools))
