"""
Studio spike S2: Can requirements.txt install a package from git?

requirements.txt pins ins-claims-agent from this repo (subdirectory=agent_studio).
Pass = import succeeds and version/__file__ are returned.
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from typing import Any, Optional

from pydantic import BaseModel, Field


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


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    report: dict[str, Any] = {
        "spike": "S2_git_requirements",
        "pass": False,
        "requirements_expected": (
            "ins-claims-agent @ "
            "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main"
            "#subdirectory=agent_studio"
        ),
        "session_directory": _session_dir(),
        "workflow_data_directory": os.environ.get("WORKFLOW_DATA_DIRECTORY"),
    }

    try:
        import ins_claims_agent

        symbol = args.probe_symbol
        value = getattr(ins_claims_agent, symbol, None)
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
                "interpretation": (
                    "PASS: git (or resolved) install worked. "
                    "Pin ins-claims-agent the same way in real tools."
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        report.update(
            {
                "pass": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=8),
                "interpretation": (
                    "FAIL: could not import ins_claims_agent from requirements.txt. "
                    "Try a published wheel / internal index next; git+https may be blocked."
                ),
            }
        )

    out_path = os.path.join(_session_dir(), "spike_s2_git_requirements.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return {
        "pass": report["pass"],
        "interpretation": report["interpretation"],
        "module_file": report.get("module_file"),
        "symbol": report.get("symbol"),
        "symbol_value": report.get("symbol_value"),
        "error": report.get("error"),
        "artifact": out_path,
        "requirements_expected": report["requirements_expected"],
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
