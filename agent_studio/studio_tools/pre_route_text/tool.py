"""
CONTENT_ID: INS_CLAIMS_PRE_ROUTE_V2
REPO_REF: main
UPDATED: 2026-08-13
FILE: agent_studio/studio_tools/pre_route_text/tool.py

CUSTOM TOOL pre_route_text — unstructured NL pre-router.

TF-IDF + numpy cosine against a small exemplar catalog. Returns label + score.
If score is below threshold (or a close call), needs_llm=true — the Routing
Agent must run a bounded LLM classify. Structured claim intake still wins
when claim_id is set.

Tool params example:
  {"text": "We were served a complaint and the case is in discovery", "claim_id": ""}
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_PRE_ROUTE_V2"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    text: str = Field(description="Unstructured notes / FNOL / email to triage")
    claim_id: Optional[str] = Field(
        default=None,
        description="Optional claim id. If set, cosine is advisory; structured claim intake is authoritative.",
    )
    threshold: Optional[float] = Field(
        default=None,
        description="Min cosine score to accept without LLM (default 0.28)",
    )
    margin: Optional[float] = Field(
        default=None,
        description="Min top1-top2 gap when labels differ (default 0.04)",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from ins_claims_agent.pre_router.route_text import (
        DEFAULT_MARGIN,
        DEFAULT_THRESHOLD,
        route_unstructured,
    )
    from ins_claims_agent import studio_io

    threshold = DEFAULT_THRESHOLD if args.threshold is None else float(args.threshold)
    margin = DEFAULT_MARGIN if args.margin is None else float(args.margin)
    result = route_unstructured(
        args.text,
        claim_id=args.claim_id,
        threshold=threshold,
        margin=margin,
    )
    result["tool_fingerprint"] = TOOL_FINGERPRINT
    result["content_id"] = TOOL_FINGERPRINT

    cid = result.get("claim_id") or "nl"
    out_path = studio_io.session_dir() / f"pre_route_{cid}.json"
    studio_io.write_json_artifact(out_path, result)
    return {
        **result,
        "decision_artifact": str(out_path.resolve()),
        "artifacts_created": [
            {
                "file_name": out_path.name,
                "file_path": str(out_path.resolve()),
                "description": "Unstructured pre-router cosine decision",
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
