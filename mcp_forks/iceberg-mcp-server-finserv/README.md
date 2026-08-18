# Iceberg MCP — retirement distributions (finserv)

Compiled named-query catalog for **retirement distributions only**. Same V7 surface as claims (`get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`). No free SQL. No claim labels. No rollover labels. No `PACK_ROOT`.

Identity: **`INS_FINSERV_MCP_V1`**.

## Catalog labels

Read: `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`, `get_schema`.

Write: `write_audit_event`, `promote_audit_run`, `begin_agent_audit_run`, `append_agent_audit_event`, `append_agent_audit_evidence`, `abandon_agent_audit_run`.

Studio `claim_id` is `distribution_request.distribution_request_id` (seed **7001**, **7002**, **7003**).

## Lake

DDL + seed:

- `ddl/hive_iceberg/retirement_distributions_iceberg.sql`
- `ddl/hive_iceberg/retirement_distributions_seed_data.sql`

Database: `retirement_distributions`. Default env: `IMPALA_DATABASE=retirement_distributions`.

| Case | Type | Route |
|---|---|---|
| **7001** | TERMINATION | `ProcessDistribution` |
| **7002** | HARDSHIP missing substantiation | `RequestSubstantiation` (R2.2) |
| **7003** | RMD underpaid | `RmdReview` (R2.3) |

## Agent Studio

Separate project from claims **402**. Register **this** MCP, not `iceberg-mcp-server-claims`.

```text
uvx --from git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=mcp_forks/iceberg-mcp-server-finserv run-server
```

Environment (same keys as claims, different database):

| Name | Value |
|---|---|
| `IMPALA_HOST` | coordinator host |
| `IMPALA_DATABASE` | `retirement_distributions` |
| `IMPALA_USER` / `IMPALA_PASSWORD` | … |

Do **not** set `PACK_ROOT`. Workflow Data is still the distributions pack contents (`pack.yaml`, ontology, playbook, exemplars).

Check: Delegate Manager `get_server_info` → `content_id=INS_FINSERV_MCP_V1`. Then `list_named_queries` must include `get_distribution_spine` and must **not** include `get_claim_spine`.

## Tests

```bash
cd mcp_forks/iceberg-mcp-server-finserv
uv sync --extra dev
uv run pytest -q
```
