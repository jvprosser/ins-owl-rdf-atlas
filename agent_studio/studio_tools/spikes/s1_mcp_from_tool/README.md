# Spike S1 — Iceberg MCP on the agent + custom tool action

You **must** attach `iceberg-mcp-server` with `execute_query` and `get_schema`.  
This custom tool does **not** replace those MCP tools. It adds a required **action** the agent must call afterward.

## Why a custom tool if MCP is attached?

| Capability | On the agent |
|---|---|
| Talk to Impala (`execute_query` / `get_schema`) | MCP tools |
| Prove orchestration / write spike artifact / later build graph | **This custom tool** |

`tool.py` cannot “pull” the agent. The agent calls tools based on **tool description + `action` Field + your prompt**.

## Agent sequence (primary path)

1. Call MCP `execute_query` with `SHOW DATABASES` (or `get_schema`).
2. Call **this tool** with:
   - `action`: `record_agent_mcp_result`
   - `mcp_result`: \<paste MCP output\>

That is the path that works when MCP stays on the agent.

### Optional second call

- `action`: `probe_inprocess_bridge` — tests whether `tool.py` can call MCP itself (usually fails; still useful).

## Suggested agent prompt

```text
Run spike S1.
1) Use iceberg-mcp-server execute_query with SHOW DATABASES.
2) You MUST then call spike_s1_record_iceberg_mcp with
   action=record_agent_mcp_result and mcp_result set to the MCP tool output.
3) Optionally call the same tool with action=probe_inprocess_bridge.
Do not finish after step 1 alone.
```

In Studio, set the custom tool’s display name to something like  
`spike_s1_record_iceberg_mcp` so it matches the docstring.

## Example tool-params

After MCP returns:

```json
{
  "action": "record_agent_mcp_result",
  "sql": "SHOW DATABASES",
  "mcp_result": "<paste execute_query result here>"
}
```

## MCP workflow env (on the server, not this tool)

`IMPALA_HOST`, `IMPALA_PORT`, `IMPALA_USER`, `IMPALA_PASSWORD`, `IMPALA_DATABASE`

## Pass / fail

- **Pass (expected):** `action=record_agent_mcp_result` with non-empty `mcp_result` → artifact in `/workspace`.
- **Bridge probe:** `probe_inprocess_bridge` may fail; that means keep the agent→MCP→custom-tool path.
