# Spike S1 — MCP callable from `tool.py`

Uses the **existing Impala Iceberg MCP** (not the Hive fork).

## MCP registration (workflow)

Server tools: `execute_query`, `get_schema`

Environment variables (set when attaching MCP to the workflow):

| Variable | Purpose |
|---|---|
| `IMPALA_HOST` | Impala host |
| `IMPALA_PORT` | Impala port |
| `IMPALA_USER` | User |
| `IMPALA_PASSWORD` | Password |
| `IMPALA_DATABASE` | Default database |

Register name in Studio as `iceberg-mcp-server` (or match whatever name you used; pass it as user-param `mcp_server_name`).

## Setup

1. Register / attach the Impala Iceberg MCP with the `IMPALA_*` vars above.
2. Register this folder as a custom tool (`tool.py` + `requirements.txt` only).
3. Run the tool.

### Example tool params

`execute_query` (default):

```json
{"sql": "SHOW DATABASES"}
```

`get_schema`:

```json
{"database": "car_insurance_claims"}
```

with user-params:

```json
{"mcp_server_name": "iceberg-mcp-server", "mcp_tool_name": "get_schema"}
```

## Pass / fail

- **Pass:** `pass: true` and an attempt pattern returns MCP output.
- **Fail:** `pass: false` — read `spike_s1_mcp_from_tool.json` in `/workspace` (`SESSION_DIRECTORY`).

## Note

This spike does **not** spawn the MCP process or use `IMPALA_*` from the tool sandbox. Those vars belong on the **MCP server** registration. The spike only looks for a Studio-provided bridge so `tool.py` can call the already-registered MCP.
