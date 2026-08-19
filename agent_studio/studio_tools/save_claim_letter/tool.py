"""
CONTENT_ID: INS_CLAIMS_LETTER_TXT_V1
REPO_REF: json-yaml-runtime
UPDATED: 2026-08-17
FILE: agent_studio/studio_tools/save_claim_letter/tool.py

CUSTOM TOOL save_claim_letter — persist drafted hold/status or police-report letter.

Call only when the user asks to write the letter. Playbook
`letter_on_request` (LitigationSupport / RequestPoliceReport) marks the
letter as recommended next work; intake and status must not auto-draft.
Does not send mail and does not call MCP.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

TOOL_FINGERPRINT = "INS_CLAIMS_LETTER_TXT_V1"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    claim_id: str = Field(description="Claim surrogate id (e.g. 402)")
    body: str = Field(description="Drafted letter text (include Subject: line)")
    run_id: Optional[str] = Field(
        default=None,
        description="Optional agent run_id for metadata",
    )
    next_step: Optional[str] = Field(
        default="LitigationSupport",
        description="Playbook next_step that requested the letter",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    from pathlib import Path

    from ins_claims_agent import studio_io

    if hasattr(studio_io, "save_claim_letter"):
        saved = studio_io.save_claim_letter(
            args.claim_id,
            args.body,
            run_id=args.run_id,
            next_step=args.next_step or "LitigationSupport",
        )
        letter_path = Path(saved["letter_artifact"])
    else:
        text = (args.body or "").strip()
        if not text:
            raise ValueError("body is required (drafted letter text)")
        if not text.endswith("\n"):
            text = text + "\n"
        letter_path = studio_io.session_dir() / f"claim_{args.claim_id}_letter.txt"
        letter_path.parent.mkdir(parents=True, exist_ok=True)
        letter_path.write_text(text, encoding="utf-8")
        saved = {
            "claim_id": str(args.claim_id),
            "run_id": args.run_id,
            "next_step": args.next_step or "LitigationSupport",
            "letter_artifact": str(letter_path.resolve()),
            "session_directory": str(studio_io.session_dir()),
            "bytes": letter_path.stat().st_size,
        }
    return {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "content_id": TOOL_FINGERPRINT,
        "status": "success",
        **saved,
        "artifacts_created": [
            {
                "file_name": letter_path.name,
                "file_path": saved["letter_artifact"],
                "description": "Hold/status letter text for BPA email handoff",
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
