# Iceberg MCP — retirement distributions (finserv)

Compiled named-query catalog for **retirement distributions only**. Same V7 surface as claims (`get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`). No free SQL. No claim labels. No rollover labels. No `PACK_ROOT`.

Identity: **`INS_FINSERV_MCP_V3`**.

## Catalog labels

Read: `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`, `get_compliance_view`, `get_loan_summary_view`, `get_qdro_details_view`, `get_schema`.

Write: `write_audit_event`, `promote_audit_run`, `begin_agent_audit_run`, `append_agent_audit_event`, `append_agent_audit_evidence`, `abandon_agent_audit_run`, `send_client_notice`.

Studio `claim_id` is `distribution_request.distribution_request_id` (seed **7001**, **7002**, **7003**, **7011–7017**).

Signals return CEL ingredients (category, amounts, flags, lists). Playbook CEL decides hardship / ERISA / emergency / QDRO. `send_client_notice` inserts one `distribution_outbound_notice` row plus an audit receipt (no carrier).

## Lake

DDL + seed:

- `ddl/hive_iceberg/retirement_distributions_iceberg.sql`
- `ddl/hive_iceberg/retirement_distributions_seed_data.sql`

Existing 7001–7003 lakes: additive `ddl/hive_iceberg/retirement_distributions_hardship_erisa.sql`.

Database: `retirement_distributions`. Default env: `IMPALA_DATABASE=retirement_distributions`.

| Case | Type | Route |
|---|---|---|
| **7001** | TERMINATION | `ProcessDistribution` |
| **7002** | HARDSHIP missing substantiation | `RequestSubstantiation` (R2.2) |
| **7003** | RMD underpaid | `RmdReview` (R2.3) |
| **7011** | HARDSHIP invalid Safe Harbor category | `HardshipCategoryReview` (R2.4) |
| **7012** | HARDSHIP amount exceeds need | `ExcessAmountAudit` (R2.5) |
| **7013** | HARDSHIP missing self-cert | `RequestSelfCertification` (R2.6) |
| **7014** | HARDSHIP QJSA / missing spousal consent | `SpousalConsentValidation` (R2.7) |
| **7015** | HARDSHIP loan capacity remains | `PlanLoanPrecheck` (R2.8) |
| **7016** | SECURE 2.0 emergency over $1,000 | `EmergencyLimitCapReview` (R2.9) |
| **7017** | TERMINATION with active QDRO | `LegalQdroReview` (R2.10) |

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

Check: Delegate Intake Agent `get_server_info` → `content_id=INS_FINSERV_MCP_V3`. Then `list_named_queries` must include `get_distribution_spine` and must **not** include `get_claim_spine`.

Restart MCP after this identity bump so Studio is not still on V2.

## Tests

```bash
cd mcp_forks/iceberg-mcp-server-finserv
uv sync --extra dev
uv run pytest -q
```
