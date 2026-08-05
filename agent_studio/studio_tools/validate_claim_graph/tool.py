"""
CONTENT_ID: INS_CLAIMS_VALIDATE_PATH_A_V2
REPO_REF: 319ede0
UPDATED: 2026-08-05
FILE: agent_studio/studio_tools/validate_claim_graph/tool.py

CUSTOM TOOL validate_claim_graph — Path A.

Reads claim_{id}_graph.ttl from SESSION_DIRECTORY (after build_claim_graph).
Ontology/probes live under WORKFLOW_DATA_DIRECTORY (not required for this tool).
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_VALIDATE_PATH_A_V2"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id whose graph to validate")
    graph_path: Optional[str] = Field(
        default=None,
        description="Optional Turtle path; default SESSION_DIRECTORY/claim_{id}_graph.ttl",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from pathlib import Path

    from rdflib import Graph

    from ins_claims_agent import studio_io
    from ins_claims_agent.graph.validate_graph import validate_claim_graph

    studio_io.configure_workflow_assets()
    claim_id = args.claim_id
    ttl_path = (
        Path(args.graph_path) if args.graph_path else studio_io.graph_artifact_path(claim_id)
    )
    if not ttl_path.is_file():
        raise FileNotFoundError(
            f"Graph artifact not found: {ttl_path}. "
            "Run build_claim_graph first (Path A: MCP spine → build)."
        )

    graph = Graph()
    graph.parse(str(ttl_path), format="turtle")
    report = validate_claim_graph(graph, claim_id)

    out_path = studio_io.validation_artifact_path(claim_id)
    studio_io.write_json_artifact(out_path, report)

    return {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        **report,
        "graph_artifact": str(ttl_path.resolve()),
        "triple_count": len(graph),
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
