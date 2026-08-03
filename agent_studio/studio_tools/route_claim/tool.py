"""
Route a claim by running Git-managed SPARQL probes + playbook against the
built claim graph artifact. Returns next_step / lane / agent_role / tools.

Single-route demo tool for Cloudera AI Agent Studio.
Call after build_claim_graph (and optionally validate_claim_graph).
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
    AssetsOnlyUserParameters,
    configure_assets_root,
    decision_artifact_path,
    ensure_sys_path,
    graph_artifact_path,
    write_json_artifact,
)


class UserParameters(AssetsOnlyUserParameters):
    """Optional assets root for probes/playbook; Hive not required."""


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id to route")
    graph_path: Optional[str] = Field(
        default=None,
        description="Optional path to Turtle graph; default claim_{id}_graph.ttl in workspace",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    """Load graph artifact, run Style B SPARQL router, write decision JSON."""
    ensure_sys_path(_TOOL_FILE)
    configure_assets_root(config.assets_root, tool_file=_TOOL_FILE)

    from rdflib import Graph

    from ins_claims_agent.graph.route_claim import route_claim

    claim_id = args.claim_id
    ttl_path = Path(args.graph_path) if args.graph_path else graph_artifact_path(claim_id)
    if not ttl_path.is_file():
        raise FileNotFoundError(
            f"Graph artifact not found: {ttl_path}. Run build_claim_graph first."
        )

    graph = Graph()
    graph.parse(str(ttl_path), format="turtle")
    decision = route_claim(graph, claim_id)

    summary = {
        "claim_id": decision.get("claim_id"),
        "lane": decision.get("lane"),
        "next_step": decision.get("next_step"),
        "agent_role": decision.get("agent_role"),
        "allowed_tools": decision.get("allowed_tools"),
        "needs_llm": decision.get("needs_llm"),
        "terminal": decision.get("terminal"),
        "reason_probe_ids": decision.get("reason_probe_ids"),
    }

    out_path = decision_artifact_path(claim_id)
    write_json_artifact(out_path, decision)

    return {
        **summary,
        "graph_artifact": str(ttl_path.resolve()),
        "decision_artifact": str(out_path.resolve()),
        "artifacts_created": [
            {
                "file_name": out_path.name,
                "file_path": str(out_path.resolve()),
                "description": "Full routing decision including probe_trace",
            }
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
