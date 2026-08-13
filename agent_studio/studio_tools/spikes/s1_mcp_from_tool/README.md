# Closed spike — custom tool calls MCP (not the other way around)

Historical record. Intake is **agent → MCP → Python tool payload**; do not re-run this spike.

## What went wrong in the failed run

The agent used Studio’s **`call-mcp`** and sent `probe_inprocess_bridge` to **iceberg-mcp-server**.  
MCP only knows `execute_query` / `get_schema`, so it correctly rejected that.

`probe_inprocess_bridge` is **not** an MCP tool. It was an internal mode of this **custom tool** (now removed as a param to avoid confusion).

## Correct run

1. Attach custom tool `spike_s1_probe_mcp_bridge` (this folder’s `tool.py`).
2. Iceberg MCP may stay attached for registration/credentials, but the agent must **not** use `call-mcp` in this spike.
3. Prompt:

```text
Call the CUSTOM tool named spike_s1_probe_mcp_bridge
(or the exact catalog name of this tool.py).

Tool parameters:
{"sql": "SHOW DATABASES"}

FORBIDDEN in this run:
- call-mcp
- iceberg-mcp-server execute_query
- iceberg-mcp-server get_schema
- any coworker/file navigation tools

Return the custom tool’s pass, interpretation, attempts_ok, attempts_failed, artifact.
```

## Pass / fail

- **Pass** → custom `tool.py` can invoke MCP (target architecture).
- **Fail** → no bridge; MCP is agent/`call-mcp` only.
