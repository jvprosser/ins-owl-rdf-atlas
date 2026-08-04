"""
CUSTOM TOOL spike_s1_probe_mcp_bridge — not iceberg-mcp-server.

Invoke this custom tool only. Do not use call-mcp or execute_query yourself.
Tool params: {"sql": "SHOW DATABASES"}

Returns TOOL_FINGERPRINT so you can confirm this Python file ran.
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from typing import Any

from pydantic import BaseModel, Field

# If this string is missing from the tool result, Studio did not run this file.
TOOL_FINGERPRINT = "INS_CLAIMS_S1_TOOL_PY_V3"


class UserParameters(BaseModel):
    mcp_server_name: str = Field(
        default="iceberg-mcp-server",
        description="Registered MCP server name to probe from inside this tool",
    )
    mcp_tool_name: str = Field(
        default="execute_query",
        description="MCP tool this custom tool will try to call internally",
    )


class ToolParameters(BaseModel):
    sql: str = Field(
        default="SHOW DATABASES",
        description="SQL this custom tool will try to send via MCP internally",
    )
    database: str = Field(
        default="",
        description="Optional database if internal call uses get_schema",
    )


def _session_dir() -> str:
    return os.environ.get("SESSION_DIRECTORY", os.getcwd())


def _redact(key: str, value: str) -> str:
    upper = key.upper()
    if any(tok in upper for tok in ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")):
        return "***REDACTED***"
    return value


def _probe_environment() -> dict:
    interesting = {}
    for k, v in sorted(os.environ.items()):
        ku = k.upper()
        if any(
            t in ku
            for t in ("MCP", "STUDIO", "AGENT", "SESSION", "WORKFLOW", "CML", "CAI", "IMPALA")
        ):
            interesting[k] = _redact(k, v)

    imports = {}
    for name in (
        "agent_studio",
        "cai_studio",
        "studio_mcp",
        "mcp_client",
        "mcp",
        "cloudera_agent_studio",
    ):
        try:
            mod = __import__(name)
            imports[name] = {"ok": True, "file": getattr(mod, "__file__", None)}
        except Exception as exc:
            imports[name] = {"ok": False, "error": type(exc).__name__ + ": " + str(exc)}

    return {
        "cwd": os.getcwd(),
        "session_directory": os.environ.get("SESSION_DIRECTORY"),
        "workflow_data_directory": os.environ.get("WORKFLOW_DATA_DIRECTORY"),
        "env_interesting": interesting,
        "imports": imports,
    }


def _mcp_arguments(config: UserParameters, args: ToolParameters) -> dict:
    if config.mcp_tool_name == "get_schema":
        if args.database:
            return {"database": args.database}
        return {}
    return {"query": args.sql}


def _try_call_patterns(config: UserParameters, args: ToolParameters) -> list:
    attempts = []
    mcp_args = _mcp_arguments(config, args)

    def record(name, fn):
        try:
            result = fn()
            attempts.append({"pattern": name, "ok": True, "result": result})
        except Exception as exc:
            attempts.append(
                {
                    "pattern": name,
                    "ok": False,
                    "error": type(exc).__name__ + ": " + str(exc),
                    "traceback": traceback.format_exc(limit=5),
                }
            )

    def via_globals():
        for key in ("call_mcp_tool", "invoke_mcp", "mcp_call", "studio_call_mcp"):
            fn = globals().get(key)
            if callable(fn):
                return {
                    "via": key,
                    "value": fn(config.mcp_server_name, config.mcp_tool_name, **mcp_args),
                }
        raise RuntimeError("No MCP bridge in tool globals")

    record("globals_bridge", via_globals)

    def via_env_http():
        base = (
            os.environ.get("MCP_GATEWAY_URL")
            or os.environ.get("STUDIO_MCP_URL")
            or os.environ.get("AGENT_STUDIO_MCP_URL")
        )
        if not base:
            raise RuntimeError("No MCP gateway URL env var")
        import urllib.request

        payload = json.dumps(
            {
                "server": config.mcp_server_name,
                "tool": config.mcp_tool_name,
                "arguments": mcp_args,
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
        return {"url": base, "body": body[:4000]}

    record("env_http_gateway", via_env_http)

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
                    "via": mod_name + "." + attr,
                    "value": fn(config.mcp_server_name, config.mcp_tool_name, **mcp_args),
                }
            except Exception as exc:
                errors.append(mod_name + ": " + type(exc).__name__)
        raise RuntimeError("no studio mcp sdk: " + "; ".join(errors))

    record("studio_sdk_import", via_studio_sdk)

    def via_stdio_opt_in():
        if not os.environ.get("SPIKE_MCP_STDIO_COMMAND"):
            raise RuntimeError("SPIKE_MCP_STDIO_COMMAND not set")
        raise RuntimeError("stdio opt-in not implemented")

    record("mcp_sdk_stdio_opt_in", via_stdio_opt_in)
    return attempts


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    probe = _probe_environment()
    attempts = _try_call_patterns(config, args)
    any_ok = any(a.get("ok") for a in attempts)

    report = {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "spike": "S1_mcp_from_tool",
        "pass": any_ok,
        "path": "tool_calls_mcp_inprocess",
        "mcp_server_name": config.mcp_server_name,
        "mcp_tool_name": config.mcp_tool_name,
        "mcp_arguments": _mcp_arguments(config, args),
        "attempts_ok": [a["pattern"] for a in attempts if a.get("ok")],
        "attempts_failed": [a["pattern"] for a in attempts if not a.get("ok")],
        "attempts": attempts,
        "probe": probe,
        "interpretation": (
            "PASS: this custom tool.py invoked MCP."
            if any_ok
            else "FAIL: this custom tool.py ran, but found no in-process MCP bridge."
        ),
    }

    out_path = os.path.join(_session_dir(), "spike_s1_mcp_from_tool.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return {
        "tool_fingerprint": TOOL_FINGERPRINT,
        "pass": report["pass"],
        "interpretation": report["interpretation"],
        "attempts_ok": report["attempts_ok"],
        "attempts_failed": report["attempts_failed"],
        "artifact": out_path,
        "session_directory": _session_dir(),
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
