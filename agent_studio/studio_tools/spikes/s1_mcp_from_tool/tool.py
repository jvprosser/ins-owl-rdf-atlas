"""
spike_s1_record_iceberg_mcp — REQUIRED custom-tool step for the S1 spike.

When the user asks to run spike S1 / test Iceberg MCP orchestration, you MUST
call THIS tool (do not stop after using iceberg-mcp-server alone).

Intended agent sequence when iceberg-mcp-server is attached with
execute_query and get_schema:

1) Call MCP execute_query with sql SHOW DATABASES (or get_schema).
2) Call this tool with action=record_agent_mcp_result and pass the MCP
   response in mcp_result (string or JSON).
3) Optionally call again with action=probe_inprocess_bridge to test whether
   tool.py can invoke MCP without the agent.

Writes spike_s1_mcp_from_tool.json under SESSION_DIRECTORY (/workspace).
"""

from __future__ import annotations

import argparse
import json
import os
import traceback
from typing import Any, Optional

from pydantic import BaseModel, Field

MCP_TOOLS_AVAILABLE = ("execute_query", "get_schema")
ALLOWED_ACTIONS = (
    "record_agent_mcp_result",
    "probe_inprocess_bridge",
)


class UserParameters(BaseModel):
    """Config for which MCP server/tool names the spike refers to."""

    mcp_server_name: str = Field(
        default="iceberg-mcp-server",
        description="Registered MCP server name (Impala Iceberg)",
    )
    mcp_tool_name: str = Field(
        default="execute_query",
        description="MCP tool the agent should use: execute_query | get_schema",
    )


class ToolParameters(BaseModel):
    """
    Runtime args. The agent chooses `action` — that is what causes this tool
    to be invoked as a distinct step from the attached MCP tools.

    Note: Agent Studio extracts this class in isolation — use only builtin /
    typing annotations here (no custom Enum/alias types).
    """

    action: str = Field(
        description=(
            "Required action for this custom tool. "
            "Must be exactly one of: record_agent_mcp_result | probe_inprocess_bridge. "
            "Use record_agent_mcp_result after you called iceberg-mcp-server "
            "(execute_query or get_schema), and pass that MCP output in mcp_result. "
            "Use probe_inprocess_bridge to test whether this tool can call MCP itself."
        )
    )
    sql: str = Field(
        default="SHOW DATABASES",
        description="SQL used with execute_query (for logging / bridge probe)",
    )
    database: str = Field(
        default="",
        description="Optional database for get_schema",
    )
    mcp_result: Optional[str] = Field(
        default=None,
        description=(
            "REQUIRED when action=record_agent_mcp_result. "
            "Paste the full raw result returned by iceberg-mcp-server "
            "execute_query or get_schema (as a string)."
        ),
    )


def _session_dir() -> str:
    return os.environ.get("SESSION_DIRECTORY", os.getcwd())


def _redact(key: str, value: str) -> str:
    upper = key.upper()
    if any(tok in upper for tok in ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")):
        return "***REDACTED***"
    return value


def _probe_environment() -> dict[str, Any]:
    interesting = {
        k: _redact(k, v)
        for k, v in sorted(os.environ.items())
        if any(
            token in k.upper()
            for token in (
                "MCP",
                "STUDIO",
                "AGENT",
                "SESSION",
                "WORKFLOW",
                "CML",
                "CAI",
                "IMPALA",
            )
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
        except Exception as exc:  # noqa: BLE001
            imports[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "cwd": os.getcwd(),
        "session_directory": os.environ.get("SESSION_DIRECTORY"),
        "workflow_data_directory": os.environ.get("WORKFLOW_DATA_DIRECTORY"),
        "env_interesting": interesting,
        "imports": imports,
    }


def _mcp_arguments(config: UserParameters, args: ToolParameters) -> dict[str, Any]:
    tool = config.mcp_tool_name
    if tool == "get_schema":
        return {"database": args.database} if args.database else {}
    if tool == "execute_query":
        return {"query": args.sql}
    raise ValueError(
        f"Unsupported mcp_tool_name={tool!r}; expected one of {MCP_TOOLS_AVAILABLE}"
    )


def _try_call_patterns(
    config: UserParameters, args: ToolParameters
) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    mcp_args = _mcp_arguments(config, args)

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

    def via_globals():
        for key in ("call_mcp_tool", "invoke_mcp", "mcp_call", "studio_call_mcp"):
            fn = globals().get(key)
            if callable(fn):
                return {
                    "via": key,
                    "value": fn(config.mcp_server_name, config.mcp_tool_name, **mcp_args),
                }
        raise RuntimeError("No call_mcp_tool/invoke_mcp/mcp_call in tool globals")

    record("globals_bridge", via_globals)

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
        return {"url": base, "status": getattr(resp, "status", None), "body": body[:4000]}

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
                    "via": f"{mod_name}.{attr}",
                    "value": fn(config.mcp_server_name, config.mcp_tool_name, **mcp_args),
                }
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{mod_name}.{attr}: {type(exc).__name__}: {exc}")
        raise RuntimeError("; ".join(errors) if errors else "no studio mcp sdk")

    record("studio_sdk_import", via_studio_sdk)

    def via_mcp_sdk_stdio():
        cmd = os.environ.get("SPIKE_MCP_STDIO_COMMAND")
        if not cmd:
            raise RuntimeError("SPIKE_MCP_STDIO_COMMAND not set")
        raise RuntimeError(
            f"SPIKE_MCP_STDIO_COMMAND is set ({cmd!r}) but auto-spawn is not "
            "implemented in this spike"
        )

    record("mcp_sdk_stdio_opt_in", via_mcp_sdk_stdio)

    return attempts


def _action_record_agent_mcp_result(
    config: UserParameters, args: ToolParameters
) -> dict[str, Any]:
    if args.mcp_result is None or args.mcp_result == "":
        return {
            "pass": False,
            "action": args.action,
            "interpretation": (
                "FAIL: action=record_agent_mcp_result requires mcp_result. "
                "Call iceberg-mcp-server execute_query (or get_schema) first, "
                "then call this tool again with that output in mcp_result."
            ),
            "next_step_for_agent": (
                f"1) Call MCP tool {config.mcp_tool_name} on {config.mcp_server_name} "
                f"with {_mcp_arguments(config, args)}. "
                "2) Call spike_s1_record_iceberg_mcp with "
                "action=record_agent_mcp_result and mcp_result=<MCP output>."
            ),
        }

    preview = args.mcp_result
    if isinstance(preview, (dict, list)):
        preview_text = json.dumps(preview, default=str)[:2000]
    else:
        preview_text = str(preview)[:2000]

    return {
        "pass": True,
        "action": args.action,
        "path": "agent_then_custom_tool",
        "mcp_server_name": config.mcp_server_name,
        "mcp_tool_name": config.mcp_tool_name,
        "mcp_arguments": _mcp_arguments(config, args),
        "mcp_result_preview": preview_text,
        "mcp_result_type": type(args.mcp_result).__name__,
        "interpretation": (
            "PASS: Agent used attached iceberg-mcp-server, then called this custom "
            "tool with the MCP payload. This is the supported orchestration path "
            "when MCP tools must remain on the agent."
        ),
    }


def _action_probe_inprocess_bridge(
    config: UserParameters, args: ToolParameters
) -> dict[str, Any]:
    attempts = _try_call_patterns(config, args)
    any_ok = any(a.get("ok") for a in attempts)
    return {
        "pass": any_ok,
        "action": args.action,
        "path": "tool_calls_mcp_inprocess",
        "attempts_ok": [a["pattern"] for a in attempts if a.get("ok")],
        "attempts_failed": [a["pattern"] for a in attempts if not a.get("ok")],
        "attempts": attempts,
        "interpretation": (
            "PASS: tool.py can invoke MCP without the agent."
            if any_ok
            else "FAIL: no in-process MCP bridge from tool.py. "
            "Keep using action=record_agent_mcp_result (agent calls MCP, then this tool)."
        ),
    }


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    probe = _probe_environment()
    action = (args.action or "").strip()

    if action == "record_agent_mcp_result":
        outcome = _action_record_agent_mcp_result(config, args)
    elif action == "probe_inprocess_bridge":
        outcome = _action_probe_inprocess_bridge(config, args)
    else:
        outcome = {
            "pass": False,
            "action": action,
            "interpretation": (
                f"Unknown action: {action!r}. "
                f"Allowed: {', '.join(ALLOWED_ACTIONS)}"
            ),
        }

    report = {
        "spike": "S1_mcp_from_tool",
        "mcp_tools_available": list(MCP_TOOLS_AVAILABLE),
        "sql": args.sql,
        "database": args.database or None,
        "probe": probe,
        **outcome,
    }

    out_path = os.path.join(_session_dir(), "spike_s1_mcp_from_tool.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    return {
        "pass": report.get("pass"),
        "action": action,
        "interpretation": report.get("interpretation"),
        "next_step_for_agent": report.get("next_step_for_agent"),
        "path": report.get("path"),
        "mcp_result_preview": report.get("mcp_result_preview"),
        "attempts_ok": report.get("attempts_ok"),
        "attempts_failed": report.get("attempts_failed"),
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
