# Iceberg MCP — underwriting submissions

Compiled named-query catalog for **underwriting submissions only**. Same surface as claims and finserv (`get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`). No free SQL. No claim labels. No distribution labels. No `PACK_ROOT`.

Identity: **`INS_UW_MCP_V1`**.

Studio `claim_id` is `submissions.submission_id` (`9100` … `9107`, and `9200`). `submission_number` (`SUB-9200`) is not the lookup id.

Party **14** (Riley Cho) is the current underwriter on **9100** through **9106**. `list_underwriter_open_submissions` returns those open files. **9107** has no role.

## Catalog labels

Read: `get_submission_spine`, `get_submission_routing_signals`, `get_senior_uw_referral_context`, `list_underwriter_open_submissions`, `get_schema`.

Write: `write_submission_decline`, `write_quote_issuance`, `write_data_enrichment_request`, `write_referral_queue`, `write_audit_event`, `promote_audit_run`, `begin_agent_audit_run`, `append_agent_audit_event`, `append_agent_audit_evidence`, `abandon_agent_audit_run`.

`write_quote_issuance` reads the lake snapshot and applies a fixed rate table. Do not pass `rating_tier` or `premium_cents`.

| Stability tier | Cents per $100 of TIV |
|---|---|
| A | 15 |
| B | 25 |
| C | 40 |
| other | 30 (`STANDARD`) |

`premium_cents = total_insured_value * rate // 100`. **9103** (tier B, TIV `1999999`) is `499999`.

Decline `reason_code` must be `OUT_OF_APPETITE`. Enrichment `provider_type` must be `INSPECTION`. Each domain write inserts `agent_run_audit` with playbook version `1.0.0`, the probe id, the playbook CEL text, and a snapshot re-read from Impala. The version string is the Git identifier. This process does not call `git rev-parse`.

## Lake

- `ddl/hive_iceberg/underwriting_iceberg.sql`
- `ddl/hive_iceberg/underwriting_seed_data.sql`

Database: `underwriting`. Default env: `IMPALA_DATABASE=underwriting`.

| Case | Route |
|---|---|
| **9100** | `DECLINE_UNINSURABLE` (P0, class `4812`) |
| **9101** | `TRIGGER_SURVEY` (P1, TIV `2000001`) |
| **9102** | `TRIGGER_SURVEY` until inspection is on file, then `REFER_TO_SENIOR_UW` |
| **9103** | `AUTO_RATE_AND_BIND` (P3) |
| **9104** | `REFER_TO_SENIOR_UW` (P2) |
| **9105** | `HUMAN_UW_REVIEW` |
| **9106** | `DECLINE_UNINSURABLE` (P0, TIV over $25M) |
| **9107** | `AssignUnderwriter` until party 14 is the current `UNDERWRITER`, then `AUTO_RATE_AND_BIND` |

## Agent Studio

Separate project from claims **402** and from distributions. Register **this** MCP.

```text
uvx --from git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=mcp_forks/iceberg-mcp-server-underwriting run-server
```

| Name | Value |
|---|---|
| `IMPALA_HOST` | coordinator host |
| `IMPALA_DATABASE` | `underwriting` |
| `IMPALA_USER` / `IMPALA_PASSWORD` | … |

Do **not** set `PACK_ROOT`. Workflow Data is the underwriting pack contents (`pack.yaml`, ontology, playbook, exemplars).

Check: Delegate Intake Agent `get_server_info` → `content_id=INS_UW_MCP_V1`. Then `list_named_queries` must include `get_submission_spine` and must **not** include `get_claim_spine`.

## Tests

```text
cd mcp_forks/iceberg-mcp-server-underwriting
uv sync --extra dev && uv run pytest -q
```
