# iceberg-mcp-server-claims

**Path A fork** of Cloudera’s Impala Iceberg MCP for the car-insurance claims agent.

Keeps upstream-style tools (`execute_query`, `get_schema`) and adds curated claim + audit helpers so the LLM does not free-form multi-join SQL.

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
| `get_server_info()` | Returns `content_id`, `version`, `registered_tools`. Expect **`INS_CLAIMS_MCP_V2`** / **`0.2.0`** after restart from current main |

### Upstream-compatible

| Tool | Notes |
|---|---|
| `execute_query(query)` | Read-only. Returns JSON `{columns, rows}` (normalized vs upstream row-list) |
| `get_schema(database?)` | List tables; optional database override |

### Claims P0

| Tool | Responsibility |
|---|---|
| `get_claim_spine(claim_id, database?)` | Claim + loss + policy + vehicle + current roles + lifecycle |
| `get_claim_routing_signals(claim_id, database?)` | Existence / routing flags + related ids |

### Specialist views (playbook `allowed_tools`)

| Tool | Responsibility |
|---|---|
| `get_litigation_view(claim_id, database?)` | Litigation case rows |
| `get_bi_view(claim_id, database?)` | Injury rows |
| `get_subrogation_view(claim_id, database?)` | Subrogation case rows |

### Audit (Impala table-append)

Impala via this server does **not** expose Hive-style Iceberg WAP branches. Audit tools write to main tables keyed by `run_id`:

| Tool | Behavior |
|---|---|
| `begin_agent_audit_run` | Validate + return `mode=table_append` |
| `append_agent_audit_event` | `INSERT` into `agent_run_audit` |
| `write_audit_event` | Playbook alias → `append_agent_audit_event` |
| `append_agent_audit_evidence` | `INSERT` into `agent_run_evidence` |
| `promote_agent_audit_run` | No-op success (already on main) |
| `promote_audit_run` | Playbook alias → `promote_agent_audit_run` |
| `abandon_agent_audit_run` | `DELETE` rows for `run_id` |

Prerequisite: audit DDL from `ddl/hive_iceberg/` applied in the target database.

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

## Path A agent flow

```text
Agent
  → MCP get_claim_spine / get_claim_routing_signals
  → custom tool (build graph / SPARQL route from payload + workflow_data)
  → MCP append_agent_audit_* (optional)
```

Custom tools still cannot call MCP in-process (S1). The agent must invoke MCP tools, then pass results into Python tools.

## Tests

```bash
cd mcp_forks/iceberg-mcp-server-claims
uv sync --extra dev
uv run pytest
```

## Sync notes

When rebasing from upstream Impala MCP:

1. Diff `execute_query` / connection env vars.
2. Keep `{columns, rows}` JSON shape and claim/audit tools.
3. Never add `print()` on the stdio path.
