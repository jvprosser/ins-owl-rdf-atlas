# Spike S1 — MCP callable from `tool.py`

## Setup in Agent Studio

1. Register Iceberg Hive MCP; attach it to the test workflow/agent.
2. Register this folder as a custom tool (`tool.py` + `requirements.txt` only).
3. Run the tool (agent or manual) with e.g. tool-params `{"sql": "SHOW DATABASES"}`.

## Pass / fail

- **Pass:** `pass: true` and an attempt pattern returns MCP output.
- **Fail:** `pass: false` — read `spike_s1_mcp_from_tool.json` in `/workspace` for env/import probes.

## Note

This spike does **not** spawn `uvx` itself (that bypasses Studio MCP registration). It only looks for a Studio-provided bridge.
