"""
CONTENT_ID: INS_CLAIMS_S2_TOOL_PY_V1
REPO_REF: 319ede0
UPDATED: 2026-08-05
FILE: agent_studio/studio_tools/spikes/s2_git_requirements/tool.py

CUSTOM TOOL spike_s2_git_requirements — git install via requirements.txt.

Upload only this tool.py + requirements.txt.
Tool params: {} or {"probe_symbol": "__version__"}

Pass = import ins_claims_agent succeeds (package came from requirements.txt git pin).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from typing import Any, Optional

from pydantic import BaseModel, Field

# If this string is missing from the tool result, Studio did not run this file.
TOOL_FINGERPRINT = "INS_CLAIMS_S2_TOOL_PY_V1"

REQUIREMENTS_LINE = (
    "ins-claims-agent @ "
    "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main"
    "#subdirectory=agent_studio"
)


class UserParameters(BaseModel):
    """No secrets required for import spike."""

    pass


class ToolParameters(BaseModel):
    probe_symbol: str = Field(
        default="__version__",
        description="Attribute to read from ins_claims_agent (e.g. __version__)",
    )


def _session_dir() -> str:
    return os.environ.get("SESSION_DIRECTORY", os.getcwd())


def _dist_info() -> dict[str, Any]:
    try:
        from importlib import metadata

        dist = metadata.distribution("ins-claims-agent")
        loc = None
        try:
            loc = str(dist.locate_file(""))
        except Exception:
            pass
        return {
            "name": dist.metadata.get("Name"),
            "version": dist.version,
            "location": loc,
            "direct_url": _read_direct_url(dist),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def _read_direct_url(dist: Any) -> Optional[dict[str, Any]]:
    """direct_url.json shows whether pip/uv installed from git."""
    try:
        text = dist.read_text("direct_url.json")
        if not text:
            return None
        return json.loads(text)
    except Exception:
        return None


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    report: dict[str, Any] = {
        "spike": "S2_git_requirements",
        "tool_fingerprint": TOOL_FINGERPRINT,
        "pass": False,
        "requirements_expected": REQUIREMENTS_LINE,
        "python": sys.version,
        "session_directory": _session_dir(),
        "workflow_data_directory": os.environ.get("WORKFLOW_DATA_DIRECTORY"),
    }

    try:
        import ins_claims_agent

        symbol = args.probe_symbol
        value = getattr(ins_claims_agent, symbol, None)
        dist = _dist_info()
        direct = dist.get("direct_url") if isinstance(dist, dict) else None
        from_git = False
        if isinstance(direct, dict):
            url = str(direct.get("url") or "")
            from_git = url.startswith("git+") or "github.com" in url

        report.update(
            {
                "pass": True,
                "module": "ins_claims_agent",
                "module_file": getattr(ins_claims_agent, "__file__", None),
                "symbol": symbol,
                "symbol_value": value,
                "package_dir": os.path.dirname(
                    getattr(ins_claims_agent, "__file__", "") or ""
                ),
                "distribution": dist,
                "installed_from_git": from_git,
                "interpretation": (
                    "PASS: ins_claims_agent imported from requirements.txt. "
                    "Pin real tools the same way"
                    + (" (direct_url confirms git)." if from_git else ".")
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        report.update(
            {
                "pass": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=12),
                "sys_path_head": sys.path[:12],
                "interpretation": (
                    "FAIL: could not import ins_claims_agent from requirements.txt. "
                    "git+https may be blocked; next try a published wheel / internal index."
                ),
            }
        )

    out_path = os.path.join(_session_dir(), "spike_s2_git_requirements.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        report["artifact"] = out_path
    except Exception as exc:  # noqa: BLE001
        report["artifact_error"] = f"{type(exc).__name__}: {exc}"

    return {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "pass": report["pass"],
        "interpretation": report["interpretation"],
        "module_file": report.get("module_file"),
        "symbol": report.get("symbol"),
        "symbol_value": report.get("symbol_value"),
        "installed_from_git": report.get("installed_from_git"),
        "distribution": report.get("distribution"),
        "error": report.get("error"),
        "artifact": report.get("artifact") or out_path,
        "requirements_expected": REQUIREMENTS_LINE,
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
