"""
Studio spike S1: Can a custom tool invoke a registered MCP tool?

Register Iceberg MCP on the workflow/agent, attach this tool, run once.
Pass = tool returns an MCP execute_query result without the LLM writing SQL.
Fail = no in-process bridge; document env/modules probed.
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from typing import Any, Optional

from pydantic import BaseModel, Field


class UserParameters(BaseModel):
    """Optional hints if Studio documents an MCP bridge name."""

    mcp_server_name: str = Field(
        default="iceberg-mcp-server-hive",
        description="Registered MCP server name to try",
    )
    mcp_tool_name: str = Field(
        default="execute_query",
        description="MCP tool to invoke",
    )


class ToolParameters(BaseModel):
    sql: str = Field(
        default="SHOW DATABASES",
        description="Read-only SQL to send via MCP execute_query",
    )


def _session_dir() -> str:
    return os.environ.get("SESSION_DIRECTORY", os.getcwd())


def _probe_environment() -> dict[str, Any]:
    interesting = {
        k: v
        for k, v in sorted(os.environ.items())
        if any(
            token in k.upper()
            for token in ("MCP", "STUDIO", "AGENT", "SESSION", "WORKFLOW", "CML", "CAI")
        )
    }
    candidate_modules = [
        "agent_studio",
        "cai_studio",
        "studio_mcp",
        "mcp_client",
        "mcp",
        "cloudera_agent_studio",
    ]
    imports: dict[str, Any] = {}
    for name in candidate_modules:
        try:
            mod = __import__(name)
            imports[name] = {
                "ok": True,
                "file": getattr(mod, "__file__", None),
                "attrs_sample": sorted(
                    [a for a in dir(mod) if not a.startswith("_")]
                )[:40],
            }
        except Exception as exc:  # noqa: BLE001 — spike must record failures
            imports[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "cwd": os.getcwd(),
        "session_directory": os.environ.get("SESSION_DIRECTORY"),
        "workflow_data_directory": os.environ.get("WORKFLOW_DATA_DIRECTORY"),
        "env_interesting": interesting,
        "imports": imports,
    }


def _try_call_patterns(config: UserParameters, sql: str) -> list[dict[str, Any]]:
    """Try plausible Studio MCP bridges; each attempt is isolated."""
    attempts: list[dict[str, Any]] = []

    def record(name: str, fn) -> None:
        try:
            result = fn()
            attempts.append({"pattern": name, "ok": True, "result": result})
        except Exception as exc:  # noqa: BLE001
            attempts.append(
                {
                    "pattern": name,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=5),
                }
            )

    # Pattern 1: globals injected into tool module
    def via_globals():
        for key in ("call_mcp_tool", "invoke_mcp", "mcp_call", "studio_call_mcp"):
            fn = globals().get(key)
            if callable(fn):
                return {"via": key, "value": fn(config.mcp_server_name, config.mcp_tool_name, query=sql)}
        raise RuntimeError("No call_mcp_tool/invoke_mcp/mcp_call in tool globals")

    record("globals_bridge", via_globals)

    # Pattern 2: common env pointing at a callable endpoint / token (observation only + http)
    def via_env_http():
        base = (
            os.environ.get("MCP_GATEWAY_URL")
            or os.environ.get("STUDIO_MCP_URL")
            or os.environ.get("AGENT_STUDIO_MCP_URL")
        )
        if not base:
            raise RuntimeError("No MCP_GATEWAY_URL / STUDIO_MCP_URL / AGENT_STUDIO_MCP_URL")
        import urllib.request

        payload = json.dumps(
            {
                "server": config.mcp_server_name,
                "tool": config.mcp_tool_name,
                "arguments": {"query": sql},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            base,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return {"url": base, "status": getattr(resp, "status", None), "body": body[:4000]}

    record("env_http_gateway", via_env_http)

    # Pattern 3: import studio SDK-style helpers if present
    def via_studio_sdk():
        errors = []
        for mod_name, attr in (
            ("agent_studio.mcp", "call_tool"),
            ("cai_studio.mcp", "call_tool"),
            ("studio_mcp", "call_tool"),
        ):
            try:
                mod = __import__(mod_name, fromlist=[attr])
                fn = getattr(mod, attr)
                return {
                    "via": f"{mod_name}.{attr}",
                    "value": fn(config.mcp_server_name, config.mcp_tool_name, query=sql),
                }
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{mod_name}.{attr}: {type(exc).__name__}: {exc}")
        raise RuntimeError("; ".join(errors) if errors else "no studio mcp sdk")

    record("studio_sdk_import", via_studio_sdk)

    # Pattern 4: mcp Python client against a stdio command from env (explicit opt-in)
    def via_mcp_sdk_stdio():
        cmd = os.environ.get("SPIKE_MCP_STDIO_COMMAND")
        if not cmd:
            raise RuntimeError(
                "SPIKE_MCP_STDIO_COMMAND not set "
                "(intentionally skip spawning MCP outside Studio registration)"
            )
        raise RuntimeError(
            f"SPIKE_MCP_STDIO_COMMAND is set ({cmd!r}) but auto-spawn is not "
            "implemented in this spike — treat as manual follow-up"
        )

    record("mcp_sdk_stdio_opt_in", via_mcp_sdk_stdio)

    return attempts


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    probe = _probe_environment()
    attempts = _try_call_patterns(config, args.sql)
    any_ok = any(a.get("ok") for a in attempts)

    report = {
        "spike": "S1_mcp_from_tool",
        "pass": any_ok,
        "mcp_server_name": config.mcp_server_name,
        "mcp_tool_name": config.mcp_tool_name,
        "sql": args.sql,
        "probe": probe,
        "attempts": attempts,
        "interpretation": (
            "PASS: at least one in-process/gateway pattern returned a result — "
            "wire Iceberg facade through that bridge."
            if any_ok
            else "FAIL: no Studio MCP bridge found from tool.py. "
            "MCP may be agent-only; escalate or add a platform bridge before "
            "build_claim_graph can use MCP from tools."
        ),
    }

    out_path = os.path.join(_session_dir(), "spike_s1_mcp_from_tool.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return {
        "pass": report["pass"],
        "interpretation": report["interpretation"],
        "attempts_ok": [a["pattern"] for a in attempts if a.get("ok")],
        "attempts_failed": [a["pattern"] for a in attempts if not a.get("ok")],
        "artifact": out_path,
        "session_directory": _session_dir(),
        "interesting_env_keys": list(probe.get("env_interesting", {}).keys()),
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
