"""
CONTENT_ID: INS_CLAIMS_ROUTE_JSON_V1
REPO_REF: json-yaml-runtime
UPDATED: 2026-08-16
FILE: agent_studio/studio_tools/route_claim/tool.py

CUSTOM TOOL route_claim — structured claim intake.

Reads claim_{id}_case.json from SESSION_DIRECTORY; playbook YAML from
WORKFLOW_DATA_DIRECTORY. Returns next_step / lane / agent_role / reason_probe_ids.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_ROUTE_JSON_V1"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id to route")
    graph_path: Optional[str] = Field(
        default=None,
        description="Optional case JSON path; default SESSION_DIRECTORY/claim_{id}_case.json",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from pathlib import Path

    from ins_claims_agent import studio_io
    from ins_claims_agent.graph.route_claim import route_claim

    assets = studio_io.configure_workflow_assets()
    claim_id = args.claim_id
    case_path = (
        Path(args.graph_path) if args.graph_path else studio_io.graph_artifact_path(claim_id)
    )
    if not case_path.is_file():
        raise FileNotFoundError(
            f"Case artifact not found: {case_path}. "
            "Run build_claim_graph first (MCP spine → build)."
        )

    case = json.loads(case_path.read_text(encoding="utf-8"))
    decision = route_claim(case, claim_id)

    summary = {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        "claim_id": decision.get("claim_id"),
        "lane": decision.get("lane"),
        "next_step": decision.get("next_step"),
        "agent_role": decision.get("agent_role"),
        "allowed_tools": decision.get("allowed_tools"),
        "needs_llm": decision.get("needs_llm"),
        "terminal": decision.get("terminal"),
        "reason_probe_ids": decision.get("reason_probe_ids"),
        "graph_artifact": str(case_path.resolve()),
        "workflow_data_directory": str(assets),
        "session_directory": str(studio_io.session_dir()),
    }

    out_path = studio_io.decision_artifact_path(claim_id)
    studio_io.write_json_artifact(out_path, decision)

    return {
        **summary,
        "decision_artifact": str(out_path.resolve()),
        "artifacts_created": [
            {
                "file_name": out_path.name,
                "file_path": str(out_path.resolve()),
                "description": "Full routing decision including probe_trace",
            }
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
