"""
CONTENT_ID: INS_CLAIMS_BUILD_PATH_A_V2
REPO_REF: 319ede0
UPDATED: 2026-08-05
FILE: agent_studio/studio_tools/build_claim_graph/tool.py

CUSTOM TOOL build_claim_graph — Path A.

Agent must call MCP get_claim_spine (+ get_claim_routing_signals), then pass
those JSON payloads here. Writes claim_{id}_graph.ttl to SESSION_DIRECTORY.

Tool params example:
  {
    "claim_id": "401",
    "spine_json": "<MCP get_claim_spine result>",
    "signals_json": "<MCP get_claim_routing_signals result>"
  }
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_BUILD_PATH_A_V2"


class UserParameters(BaseModel):
    """No Hive secrets — lake I/O is via agent MCP (Path A)."""

    pass


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id (e.g. 401)")
    spine_json: str = Field(
        description="JSON from MCP get_claim_spine (stringified tool result)"
    )
    signals_json: str = Field(
        default="{}",
        description="JSON from MCP get_claim_routing_signals (optional but recommended)",
    )
    database: Optional[str] = Field(
        default=None,
        description="Optional database label for metadata only",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from ins_claims_agent import studio_io
    from ins_claims_agent.graph.build_claim_graph import build_claim_graph

    assets = studio_io.configure_workflow_assets()
    claim_id = args.claim_id
    spine = studio_io.normalize_spine_payload(args.spine_json)
    signals = studio_io.normalize_signals_payload(args.signals_json)
    studio_io.assert_spine_has_triangle_fields(spine)

    graph = build_claim_graph(claim_id, spine=spine, signals=signals)

    ttl_path = studio_io.graph_artifact_path(claim_id)
    ttl_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(ttl_path), format="turtle")

    meta = {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        "claim_id": str(claim_id),
        "database": args.database or spine.get("database") or "car_insurance_claims",
        "triple_count": len(graph),
        "policy_id": spine.get("policy_id"),
        "insurable_object_id": spine.get("insurable_object_id"),
        "coverage_type_code": spine.get("coverage_type_code"),
        "graph_artifact": str(ttl_path.resolve()),
        "session_directory": str(studio_io.session_dir()),
        "workflow_data_directory": str(assets),
        "status": "success",
    }
    meta_path = studio_io.session_dir() / f"claim_{claim_id}_build.json"
    studio_io.write_json_artifact(meta_path, meta)

    return {
        **meta,
        "artifacts_created": [
            {
                "file_name": ttl_path.name,
                "file_path": str(ttl_path.resolve()),
                "description": "Claim RDF graph (Turtle) for validate/route",
            },
            {
                "file_name": meta_path.name,
                "file_path": str(meta_path.resolve()),
                "description": "Build metadata JSON",
            },
        ],
    }


OUTPUT_KEY = "tool_output"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True)
    parser.add_argument("--tool-params", required=True)
    cli = parser.parse_args()
    output = run_tool(
        UserParameters(**json.loads(cli.user_params)),
        ToolParameters(**json.loads(cli.tool_params)),
    )
    print(OUTPUT_KEY, output)
