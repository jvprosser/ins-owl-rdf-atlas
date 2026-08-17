# MCP Fork Charter

**Status:** Draft for Phase 1  
**Date:** 2026-08-03  
**Program:** Car insurance claims semantic layer (Cloudera Agent Studio) — manager agent as NL interface; deterministic SPARQL/playbook routing

## Purpose

Fork two MCP servers to close platform gaps for claim-graph agents, while keeping:

- **RDF / SPARQL / OWL** in Agent Studio Python tools (not MCP)
- **Ranger** on the existing server (no fork unless later needed)
- **Probes / playbook / ontology** as Git files in this repo

## Upstream servers

| Fork working name | Upstream | Owns | Status |
|---|---|---|---|
| `iceberg-mcp-server-claims` | [cloudera/iceberg-mcp-server](https://github.com/cloudera/iceberg-mcp-server) (Impala) | Iceberg read + claim spine/signals + audit helpers | **In-repo** — `mcp_forks/iceberg-mcp-server-claims/` |
| `iceberg-mcp-server-hive-claims` | [frothkoetter/iceberg-mcp-server-hive](https://github.com/frothkoetter/iceberg-mcp-server-hive) | Same claim helpers + true WAP branches | Optional later if Hive branch API is required |
| `data-contract-mcp-server-claims` | [frothkoetter/data-contract-mcp-server](https://github.com/frothkoetter/data-contract-mcp-server) | Atlas catalog + ODCS contracts + ontology-binding helpers | Deferred |

**Not forked now**

- [frothkoetter/ranger-mcp-server](https://github.com/frothkoetter/ranger-mcp-server) — access, masking, audit logs as-is
- [ecole5/atlas-mcp](https://github.com/ecole5/atlas-mcp) — reference baseline only; do **not** register beside the data-contract fork (duplicate tools)

## Design principles

1. **Additive forks** — keep upstream tools; add helpers; avoid breaking signatures.
2. **One Atlas MCP** — data-contract fork is the only Atlas interface in Agent Studio.
3. **WAP when available** — Hive fork: audit writes to Iceberg branches. Impala claims fork: `table_append` keyed by `run_id` (no branch API).
4. **Thin MCP, thin Python** — MCP = platform I/O; Python = graph build, SPARQL route, validate, specialist logic.
5. **No SPARQL-in-MCP** — graph querying stays in-process (`rdflib` et al.).
6. **Allow-listed power** — no open-ended DDL/write-on-main helpers in Phase 1.

## Phase 1 (P0) scope

### A) Iceberg fork — P0 tools

Implemented for Impala in `mcp_forks/iceberg-mcp-server-claims/`. **V7 MCP tools:** `get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`. Playbook names (`get_claim_spine`, `get_litigation_view`, `write_audit_event`, …) are catalog **labels**, not registered MCP tools. `execute_query` is not registered.

| Tool | Responsibility | Impala claims fork |
|---|---|---|
| `get_claim_spine(claim_id, database?)` | Claim + loss + policy + vehicle + current roles + lifecycle | Curated SQL |
| `get_claim_routing_signals(claim_id, database?)` | Flags + existence signals | Curated SQL |
| `get_litigation_view` / `get_bi_view` / `get_subrogation_view` | Playbook specialist views | Curated SQL |
| `write_audit_event` / `promote_audit_run` | Playbook name aliases | → append / promote helpers |
| `create_litigation_task` | Insert `litigation_task` (COMPLETE_FILE / ESCALATE_DISCOVERY / DRAFT_HOLD) | Curated INSERT; `run_id` + `event_json` |
| `begin_agent_audit_run(run_id, database, source_branch?)` | Start audit run | Validate; `mode=table_append` (no branch) |
| `append_agent_audit_event(run_id, event_json)` | Router/tool/decision events | `INSERT` main `agent_run_audit` |
| `append_agent_audit_evidence(run_id, evidence_json)` | SPARQL/validation/graph excerpts | `INSERT` main `agent_run_evidence` |
| `promote_agent_audit_run(run_id)` | Accept audit run | No-op success on Impala |
| `abandon_agent_audit_run(run_id)` | Drop/mark abandoned | `DELETE` rows for `run_id` |

**Depends on:** audit table DDL existing in `car_insurance_claims` (see `ddl/hive_iceberg/`).  
**Runtime:** agent calls these MCP tools, then passes JSON into custom Python tools (tools cannot call MCP in-process).

### B) Data-contract / Atlas fork — P0 tools

| Tool | Responsibility |
|---|---|
| `ensure_business_metadata_typedef(bm_name, attributes[])` | Create/upgrade BM def (e.g. `ontology_binding`) |
| `set_entity_business_metadata(guid, bm_name, attributes)` | Write ontology IRIs / mapping fields onto entities |
| `get_entity_business_metadata(guid, bm_name?)` | Read BM for agents / sync checks |
| `bind_ontology_iri_to_entity(guid, ontology_iri, mapping_type, version_iri?)` | Convenience wrapper over BM conventions |

**Phase 1 Atlas projection:** contracts (upstream) + classifications/labels (upstream) + ontology BM binding (new).  
**Deferred:** glossary term CRUD/assign; general classification typedef authoring; custom relationship upsert.

## Out of scope (Phase 1)

- Persistent triple-store MCP
- Object-storage MCP for audits (Iceberg branches instead)
- Glossary write APIs
- Ranger fork
- Registering both `ecole5/atlas-mcp` and the data-contract fork
- Open `execute_ddl` / write SQL against `main`
- Embedding OWL reasoners inside MCP servers

## Runtime topology

```text
User (natural language)
  └─ Manager agent                    # NL interface + unstructured task dispatch
       ├─ MCP Iceberg claims fork     → get_claim_spine / signals / audit helpers
       ├─ Custom tools (deterministic)
       │    ├─ build_claim_graph
       │    ├─ validate_claim_graph
       │    └─ route_claim            → rdflib + probes/*.rq + playbook.yaml
       ├─ LLM subtasks (when needed)  → unstructured notes/docs/extraction only
       ├─ governance helpers (later)  → Atlas fork: BM bind + contracts/tags
       └─ access/masking/audit        → Ranger MCP (unchanged)
```

**Manager agent (locked):** conversational front door and explainer; assigns LLM work for unstructured data. **Not** the business-rules engine — routing stays in Git-reviewed probes/playbook + Python tools.

## Success criteria

1. `build_claim_graph(claim_id)` needs no free-form multi-join SQL from the LLM.
2. Every routed run can write auditable Iceberg audit rows (branch WAP on Hive fork; `run_id` table-append on Impala fork) and optionally promote/abandon.
3. Selected lake tables/columns can carry `ontology.iri` via Atlas BM without labels hacks.
4. Agent Studio registers the Iceberg claims fork (+ later Atlas/data-contract fork + Ranger upstream).
5. Router probes/playbook remain Git-reviewed files (no custom steward UI).

## Phase 2 candidates (not committed)

**Iceberg fork:** `diff_iceberg_branch`, `list_agent_audit_runs`, allow-listed DDL applicator, snapshot tags.  
**Atlas fork:** glossary create/assign, `ensure_classification_typedef`, `export_entity_semantic_projection`, contract↔classification sync helpers.

Parked integration plan (phases A–C, crew, risks): [`atlas-ranger-integration-plan.md`](atlas-ranger-integration-plan.md).

## Ownership & process

| Item | Owner |
|---|---|
| Fork repos + P0 tools | Platform / MCP maintainers |
| Claim spine SQL correctness | Claims data engineering |
| Probe/playbook/ontology files | Semantic / agent team |
| Audit table DDL | Data platform + agent team |
| Ranger policies for PII/health | Security / Ranger admins |

**Process**

1. Fork upstream; add P0 tools behind clear names.
2. Keep upstream sync cadence documented (rebase/cherry-pick notes in each fork README).
3. Contract-test P0 tools against CDP sandbox before Agent Studio wiring.
4. Wire Agent Studio facades only to P0 + unchanged upstream tools.

## Decision log

| Decision | Choice |
|---|---|
| Manager agent role | NL interface + user-friendly results + unstructured LLM task dispatch |
| Business rules / routing | Deterministic tools + SPARQL probes + playbook (not the LLM) |
| RDF/SPARQL location | Python Agent Studio tools |
| Audit destination | Iceberg via Iceberg MCP (WAP branch on Hive; table-append on Impala claims fork) |
| Iceberg MCP base | Impala `cloudera/iceberg-mcp-server` fork in this repo |
| Atlas primary MCP | Data-contract fork (not ecole5 alone; not both) |
| Probe/playbook source | Repo files |
| Custom routing UI | Not in Phase 1 |

## Approval

- [ ] Platform / MCP
- [ ] Claims data engineering
- [ ] Semantic / agent team
- [ ] Security (Ranger impact acknowledged)
