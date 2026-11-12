"""
CONTENT_ID: INS_CLAIMS_NAMED_CATALOG_V1
REPO_REF: main
UPDATED: 2026-11-12
FILE: agent_studio/studio_tools/run_named_catalog/tool.py

CUSTOM TOOL run_named_catalog — claims lake I/O without the MCP process.

One tool for run_named_query and run_named_write. The allow-list is
Workflow Data catalog/catalog.yaml. sql: labels run that file. handler:
labels call iceberg-mcp-server-claims. build/validate/route stay separate.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_NAMED_CATALOG_V1"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    op: str = Field(description="query, write, or list")
    label: Optional[str] = Field(default=None, description="Catalog label")
    claim_id: Optional[str] = Field(default=None, description="Claim surrogate id")
    fnol_id: Optional[str] = Field(default=None, description="FNOL id or FNOL-2026-00088")
    party_id: Optional[str] = Field(default=None, description="Adjuster party id")
    database: Optional[str] = Field(default=None, description="Impala database")
    run_id: Optional[str] = Field(default=None, description="Agent run id")
    event_json: Optional[str] = Field(default=None, description="Write event JSON")
    evidence_json: Optional[str] = Field(default=None, description="Audit evidence JSON")
    source_branch: Optional[str] = Field(default=None, description="Audit source branch")
    params_json: Optional[str] = Field(
        default=None,
        description="Optional JSON object merged under the flat fields",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from ins_claims_agent.named_catalog import execute

    params: dict[str, Any] = {}
    if args.params_json:
        extra = json.loads(args.params_json)
        if not isinstance(extra, dict):
            return _stamp({"ok": False, "error": "params_json must be a JSON object"})
        params.update(extra)
    for key in (
        "claim_id",
        "fnol_id",
        "party_id",
        "database",
        "run_id",
        "event_json",
        "evidence_json",
        "source_branch",
    ):
        value = getattr(args, key)
        if value not in (None, ""):
            params[key] = value
    return _stamp(execute(op=args.op, label=args.label, params=params))


def _stamp(payload: dict[str, Any]) -> dict[str, Any]:
    payload["tool_fingerprint"] = TOOL_FINGERPRINT
    payload["content_id"] = TOOL_FINGERPRINT
    return payload


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
