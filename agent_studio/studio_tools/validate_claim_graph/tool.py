"""
CONTENT_ID: INS_CLAIMS_VALIDATE_JSON_V1
REPO_REF: json-yaml-runtime
UPDATED: 2026-08-16
FILE: agent_studio/studio_tools/validate_claim_graph/tool.py

CUSTOM TOOL validate_claim_graph — structured claim intake.

Reads claim_{id}_case.json from SESSION_DIRECTORY (after build_claim_graph).
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_VALIDATE_JSON_V1"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id whose case JSON to validate")
    graph_path: Optional[str] = Field(
        default=None,
        description="Optional case JSON path; default SESSION_DIRECTORY/claim_{id}_case.json",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from pathlib import Path

    from ins_claims_agent import studio_io
    from ins_claims_agent.graph.validate_graph import validate_claim_graph

    studio_io.configure_workflow_assets()
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
    report = validate_claim_graph(case, claim_id)

    out_path = studio_io.validation_artifact_path(claim_id)
    studio_io.write_json_artifact(out_path, report)

    return {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        **report,
        "graph_artifact": str(case_path.resolve()),
        "field_count": len(case) if isinstance(case, dict) else 0,
        "session_directory": str(studio_io.session_dir()),
        "artifacts_created": [
            {
                "file_name": out_path.name,
                "file_path": str(out_path.resolve()),
                "description": "Validation report JSON",
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
