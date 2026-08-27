# Retirement distributions (finserv demo)

Classification and exception handling for plan distributions. Deterministic probes — not an LLM policy engine.

Live lake + MCP: `ddl/hive_iceberg/retirement_distributions_*.sql` and [`mcp_forks/iceberg-mcp-server-finserv`](../../mcp_forks/iceberg-mcp-server-finserv/README.md). Fixture JSON in this pack stays golden for `agent_studio/tests/test_packs.py`.

| Case | Story | Route |
|---|---|---|
| **7001** | Termination, documents complete | `ProcessDistribution` / `DistributionOpsAgent` |
| **7002** | Hardship, substantiation missing | `RequestSubstantiation` / `ExceptionQueueAgent` |
| **7003** | RMD underpaid | `RmdReview` / `RmdOpsAgent` |
| **7011** | Hardship, invalid Safe Harbor category (`VACATION`) | `HardshipCategoryReview` / `ExceptionQueueAgent` |
| **7012** | Hardship amount exceeds documented need | `ExcessAmountAudit` / `ExceptionQueueAgent` |
| **7013** | Hardship missing self-certification | `RequestSelfCertification` / `ClientCommunicationsAgent` |
| **7014** | QJSA plan, married, no spousal consent | `SpousalConsentValidation` / `ComplianceOpsAgent` |
| **7015** | Plan mandates loan exhaustion; capacity remains | `PlanLoanPrecheck` / `ExceptionQueueAgent` |
| **7016** | SECURE 2.0 emergency over $1,000 | `EmergencyLimitCapReview` / `ExceptionQueueAgent` |
| **7017** | Termination with active QDRO + pending court order | `LegalQdroReview` / `ComplianceOpsAgent` |

## Agent Studio workflow + tests

Register **`iceberg-mcp-server-finserv`**, not the claims MCP. Identity: `INS_FINSERV_MCP_V3`. Do **not** set `PACK_ROOT`.

Setup (MCP `uvx`, crew, e2e prompts): [`mcp_forks/iceberg-mcp-server-finserv/README.md`](../../mcp_forks/iceberg-mcp-server-finserv/README.md).

## Upload workflow data (Studio)

Studio mounts this tree as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`. Upload the **contents** of `packs/retirement_distributions/`, not the folder name. After upload, `/workflow_data/pack.yaml` must exist (not `/workflow_data/retirement_distributions/pack.yaml`).

Do this in the **distributions** Agent Studio project (not the claims 402 project).

1. Open the project → open **Workflow Data** (the project file tree for this workflow).
2. If this project previously held claims files (`ontology/claims.json`, `claims_mvt.ttl`, `probes/*.rq`, claims `playbook/`), delete those first so the pack is the only tree. Do not upload Turtle or SPARQL.
3. At the **root** of Workflow Data, upload these two files from `packs/retirement_distributions/`:
   - `pack.yaml`
   - `exemplars.yaml`
4. Create folder `ontology` (or upload that directory). Inside it, upload:
   - `ontology/distributions.json`
5. Create folder `playbook` (or upload that directory). Inside it, upload:
   - `playbook/playbook.yaml`
6. Confirm the tree looks like this:

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/distributions.json
  playbook/playbook.yaml
```

That is the JSON+YAML runtime (same as claims 402). Do **not** upload `ontology/*.ttl` or `probes/*.rq` — those exist only on `rdf-sparql-runtime`.

**Do not** upload to Workflow Data: `agents/` (paste those into agent Name/Role/Backstory/Goal), `fixtures/`, `catalog_fixtures.json`, or `README.md`. Fixtures remain repo golden tests; the live catalog is compiled in the finserv MCP.

If Studio offers “upload folder”, select `ontology` and `playbook` individually. Do not upload the parent `retirement_distributions` folder as a single nest.

## MCP registration

In the **distributions** Agent Studio project, register **`iceberg-mcp-server-finserv`** only. Do not register `iceberg-mcp-server-claims`.

| Place | Set |
|---|---|
| Studio **MCP** → finserv server → **Environment variables** | `IMPALA_HOST`, `IMPALA_DATABASE=retirement_distributions`, user/password |
| `PACK_ROOT` | **Do not set** |
| Workflow Data (`/workflow_data`) | Ontology / playbook / `pack.yaml` only |
| Agent Name / Role / Backstory / Goal | No Impala env |

Paste this as the MCP registration (same `IMPALA_*` keys as claims, different database). Do **not** add `PACK_ROOT`.

```json
{
  "mcpServers": {
    "iceberg-mcp-server-finserv": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=mcp_forks/iceberg-mcp-server-finserv",
        "run-server"
      ],
      "env": {
        "IMPALA_HOST": "<coordinator-host>",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "<user>",
        "IMPALA_PASSWORD": "<password>",
        "IMPALA_DATABASE": "retirement_distributions"
      }
    }
  }
}
```

## Catalog labels

Read: `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`, `get_compliance_view`, `get_loan_summary_view`, `get_qdro_details_view`, `get_schema`.

Write: `write_audit_event`, `promote_audit_run`, `begin_agent_audit_run`, `append_agent_audit_event`, `append_agent_audit_evidence`, `abandon_agent_audit_run`, `send_client_notice`.

Studio `claim_id` is `distribution_request.distribution_request_id` (seed **7001**, **7002**, **7003**, **7011–7017**).

Check: Delegate Manager `get_server_info` → `content_id=INS_FINSERV_MCP_V3`. Then `list_named_queries` must include `get_distribution_spine` and must **not** include `get_claim_spine`.

## Studio prompt (lead with 7002)

Paste Orchestrator / Manager / Exception Queue / Client Communications / Compliance Ops from `agents/`. Then chat Orchestrator:

```text
Please process claim 7002.
```

Expect `next_step=RequestSubstantiation`, `lane=EXCEPTION`, `coworker=Exception Queue Agent`, `write=write_audit_event`, probe **R2.2**.

After a playbook or Goal change: re-upload `playbook.yaml`, re-upload Studio `route_claim` (`INS_CLAIMS_ROUTE_JSON_V6`), re-paste Orchestrator and Manager Goals. Do **not** mix claims MCP into this project.
