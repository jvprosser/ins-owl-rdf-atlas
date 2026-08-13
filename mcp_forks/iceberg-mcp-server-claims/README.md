# iceberg-mcp-server-claims

Claims fork of Cloudera’s Impala Iceberg MCP for the car-insurance claims agent.

**V7 MCP surface is catalog-only.** Agents call `run_named_query` / `run_named_write` with an allow-listed label. Per-label tools and free-form `execute_query` are not registered. SQL still lives in Python handlers behind the catalog.

| Aspect | Detail |
|---|---|
| Upstream base | [cloudera/iceberg-mcp-server](https://github.com/cloudera/iceberg-mcp-server) (Impala / `impyla`) |
| Location | This repo: `mcp_forks/iceberg-mcp-server-claims/` |
| Transport | stdio (Agent Studio `uvx` / MCP registration) |
| Python | `>=3.10` |

## Tools

### Identity

| Tool | Notes |
|---|---|
| `get_server_info()` | One-shot identity. Expect **`INS_CLAIMS_MCP_V7`** / **`0.3.3`**. Prompt: “Call get_server_info once and stop.” |

### Named catalog (only lake I/O)

Studio Action Input is **flat**. Prefer top-level `claim_id` / `run_id` over nested `params_json`. No free-form SQL.

| Tool | Notes |
|---|---|
| `list_named_queries()` | Catalog of read/write labels + required params |
| `run_named_query(label, claim_id?, database?, params_json?)` | Curated **reads**. Example: `{"label":"get_litigation_view","claim_id":"402"}` |
| `run_named_write(label, run_id?, event_json?, …)` | Curated **writes**. Example: `{"label":"write_audit_event","run_id":"demo-402","event_json":"{...}"}` |

Read labels: `get_claim_spine`, `get_claim_routing_signals`, `get_litigation_view`, `get_bi_view`, `get_subrogation_view`, `get_schema`.

Write labels: `write_audit_event`, `append_agent_audit_event`, `append_agent_audit_evidence`, `begin_agent_audit_run`, `promote_audit_run`, `promote_agent_audit_run`, `abandon_agent_audit_run`.

Impala audit writes are table-append (no Iceberg WAP branch). `promote_audit_run` returns `mode=table_append`. Prerequisite: audit DDL from `ddl/hive_iceberg/` in the target database.

## Agent Studio registration

Replace the stock `iceberg-mcp-server` registration with this fork (same `IMPALA_*` env). Example:

```json
{
  "mcpServers": {
      "iceberg-mcp-server-claims": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git#subdirectory=mcp_forks/iceberg-mcp-server-claims",
  
        "run-server"
      ],
      "env": {
        "IMPALA_HOST": "<coordinator-host>",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "<user>",
        "IMPALA_PASSWORD": "<password>",
        "IMPALA_DATABASE": "car_insurance_claims"
      }
    }
  }
}
```

Local editable / path install for sandbox:

```bash
cd mcp_forks/iceberg-mcp-server-claims
uv sync
# or: pip install -e .
uv run run-server
```

**stdio:** do not print to stdout; this server logs to stderr only.

## Structured claim intake flow

```text
Agent
  → MCP run_named_query label get_claim_spine
  → MCP run_named_query label get_claim_routing_signals
  → custom tool (build graph / SPARQL route from payload + workflow_data)
  → MCP run_named_write label write_audit_event (optional)
```

Custom tools do not call MCP in-process. The agent must invoke MCP tools, then pass results into Python tools.

## Tests

```bash
cd mcp_forks/iceberg-mcp-server-claims
uv sync --extra dev
uv run pytest
```

## Sync notes

When rebasing from upstream Impala MCP:

1. Diff connection env vars. Do not re-register `execute_query` as an MCP tool.
2. Keep catalog handlers and `{columns, rows}` JSON shape internally.
3. Never add `print()` on the stdio path.
