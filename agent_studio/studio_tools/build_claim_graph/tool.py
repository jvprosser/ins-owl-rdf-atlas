"""
CONTENT_ID: INS_CLAIMS_BUILD_JSON_V1
REPO_REF: json-yaml-runtime
UPDATED: 2026-08-16
FILE: agent_studio/studio_tools/build_claim_graph/tool.py

CUSTOM TOOL build_claim_graph — structured claim intake.

Agent must call MCP get_claim_spine (+ get_claim_routing_signals), then pass
those JSON payloads here. Writes claim_{id}_case.json to SESSION_DIRECTORY.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_BUILD_JSON_V1"


class UserParameters(BaseModel):
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
    from ins_claims_agent.graph.build_case_graph import build_case_graph
    from ins_claims_agent.graph.build_claim_graph import build_claim_graph
    from ins_claims_agent.paths import current_pack

    assets = studio_io.configure_workflow_assets()
    claim_id = args.claim_id
    spine = studio_io.normalize_spine_payload(args.spine_json)
    signals = studio_io.normalize_signals_payload(args.signals_json)
    pack = current_pack()
    if pack is not None and pack.graph.get("builder") == "generic":
        case = build_case_graph(claim_id, pack=pack, spine=spine, signals=signals)
    else:
        studio_io.assert_spine_has_triangle_fields(spine)
        case = build_claim_graph(claim_id, spine=spine, signals=signals)

    case_path = studio_io.graph_artifact_path(claim_id)
    studio_io.write_json_artifact(case_path, case)

    meta = {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        "claim_id": str(claim_id),
        "database": args.database or spine.get("database") or "car_insurance_claims",
        "field_count": len(case),
        "policy_id": spine.get("policy_id"),
        "insurable_object_id": spine.get("insurable_object_id"),
        "coverage_type_code": spine.get("coverage_type_code"),
        "graph_artifact": str(case_path.resolve()),
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
                "file_name": case_path.name,
                "file_path": str(case_path.resolve()),
                "description": "Case JSON for validate/route",
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
