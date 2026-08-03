"""
Build an in-memory claim RDF graph from Iceberg/Hive spine + routing signals,
then persist it as a workspace Turtle artifact for validate/route tools.

Single-route demo tool for Cloudera AI Agent Studio.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

_TOOL_FILE = Path(__file__).resolve()
_TOOL_DIR = _TOOL_FILE.parent
_STUDIO_TOOLS = _TOOL_DIR if (_TOOL_DIR / "shared").is_dir() else _TOOL_DIR.parent
_PACKAGE_SRC = (
    _TOOL_DIR if (_TOOL_DIR / "ins_claims_agent").is_dir() else _STUDIO_TOOLS.parent / "src"
)
for _p in (_PACKAGE_SRC, _STUDIO_TOOLS):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from shared.bootstrap import (  # noqa: E402
    HiveUserParameters,
    bind_iceberg_from_hive,
    configure_assets_root,
    ensure_sys_path,
    graph_artifact_path,
    write_json_artifact,
)


class UserParameters(HiveUserParameters):
    """Hive connection + optional assets root for ontology bundling."""


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id to load (e.g. 401)")
    database: Optional[str] = Field(
        default=None,
        description="Override claims database (default: user claims_database)",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    """Load claim spine/signals from Hive, build RDF graph, write artifacts."""
    ensure_sys_path(_TOOL_FILE)
    configure_assets_root(config.assets_root, tool_file=_TOOL_FILE)

    from ins_claims_agent.graph.build_claim_graph import build_claim_graph

    iceberg = bind_iceberg_from_hive(config, tool_file=_TOOL_FILE)
    database = args.database or config.claims_database
    claim_id = args.claim_id

    graph = build_claim_graph(claim_id, iceberg=iceberg, database=database)

    ttl_path = graph_artifact_path(claim_id)
    graph.serialize(destination=str(ttl_path), format="turtle")

    meta = {
        "claim_id": str(claim_id),
        "database": database,
        "triple_count": len(graph),
        "graph_artifact": str(ttl_path.resolve()),
        "status": "success",
    }
    meta_path = Path(f"claim_{claim_id}_build.json")
    write_json_artifact(meta_path, meta)

    return {
        **meta,
        "artifacts_created": [
            {
                "file_name": ttl_path.name,
                "file_path": str(ttl_path.resolve()),
                "description": "Claim RDF graph (Turtle) for validate/route tools",
            },
            {
                "file_name": meta_path.name,
                "file_path": str(meta_path.resolve()),
                "description": "Build metadata JSON",
            },
        ],
        "artifact_directory": os.getcwd(),
    }


OUTPUT_KEY = "tool_output"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="Tool configuration")
    parser.add_argument("--tool-params", required=True, help="Tool arguments")
    cli = parser.parse_args()

    config = UserParameters(**json.loads(cli.user_params))
    params = ToolParameters(**json.loads(cli.tool_params))
    output = run_tool(config, params)
    print(OUTPUT_KEY, output)
