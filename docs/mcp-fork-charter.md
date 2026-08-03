# MCP Fork Charter

**Status:** Draft for Phase 1  
**Date:** 2026-08-03  
**Program:** Car insurance claims agentic semantic layer (Cloudera Agent Studio)

## Purpose

Fork two MCP servers to close platform gaps for claim-graph agents, while keeping:

- **RDF / SPARQL / OWL** in Agent Studio Python tools (not MCP)
- **Ranger** on the existing server (no fork unless later needed)
- **Probes / playbook / ontology** as Git files in this repo

## Upstream servers

| Fork working name | Upstream | Owns |
|---|---|---|
| `iceberg-mcp-server-hive-claims` | [frothkoetter/iceberg-mcp-server-hive](https://github.com/frothkoetter/iceberg-mcp-server-hive) | Iceberg read + WAP branches + claim/audit helpers |
| `data-contract-mcp-server-claims` | [frothkoetter/data-contract-mcp-server](https://github.com/frothkoetter/data-contract-mcp-server) | Atlas catalog + ODCS contracts + ontology-binding helpers |

**Not forked now**

- [frothkoetter/ranger-mcp-server](https://github.com/frothkoetter/ranger-mcp-server) — access, masking, audit logs as-is
- [ecole5/atlas-mcp](https://github.com/ecole5/atlas-mcp) — reference baseline only; do **not** register beside the data-contract fork (duplicate tools)

## Design principles

1. **Additive forks** — keep upstream tools; add helpers; avoid breaking signatures.
2. **One Atlas MCP** — data-contract fork is the only Atlas interface in Agent Studio.
3. **WAP by default** — agent audit writes go to Iceberg branches, not silent main-table edits.
4. **Thin MCP, thin Python** — MCP = platform I/O; Python = graph build, SPARQL route, validate, specialist logic.
5. **No SPARQL-in-MCP** — graph querying stays in-process (`rdflib` et al.).
6. **Allow-listed power** — no open-ended DDL/write-on-main helpers in Phase 1.

## Phase 1 (P0) scope

### A) Iceberg fork — P0 tools

| Tool | Responsibility |
|---|---|
| `get_claim_spine(claim_id, database?)` | Return claim + loss + policy + vehicle + current roles + lifecycle for graph build |
| `get_claim_routing_signals(claim_id, database?)` | Return flags + existence signals (subrogation/litigation/injury/offer/reserve/docs) |
| `begin_agent_audit_run(run_id, database, source_branch?)` | Create standardized audit branch(es), e.g. `branch_agent_run_<run_id>` |
| `append_agent_audit_event(run_id, event_json)` | Insert router/tool/decision events on audit branch |
| `append_agent_audit_evidence(run_id, evidence_json)` | Insert SPARQL/validation/graph excerpts on audit branch |
| `promote_agent_audit_run(run_id)` | Fast-forward accepted audit branch(es) |
| `abandon_agent_audit_run(run_id)` | Drop/mark abandoned audit branch(es) |

**Depends on:** audit table DDL existing (or documented prerequisite) in `car_insurance_claims` (or agent audit database).

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
Agent Studio tools
  ├─ build_claim_graph      → Iceberg: get_claim_spine (+ signals)
  ├─ sparql_route/validate  → local rdflib + probes/*.rq + playbook.yaml
  ├─ write_audit            → Iceberg: begin/append/promote audit run
  ├─ governance helpers     → Atlas fork: BM bind + upstream contract/tag tools
  └─ access/masking/audit   → Ranger MCP (unchanged)
```

## Success criteria

1. `build_claim_graph(claim_id)` needs no free-form multi-join SQL from the LLM.
2. Every routed run can write an auditable Iceberg branch and optionally promote it.
3. Selected lake tables/columns can carry `ontology.iri` via Atlas BM without labels hacks.
4. Agent Studio registers exactly three platform MCPs: Iceberg fork, Atlas/data-contract fork, Ranger upstream.
5. Router probes/playbook remain Git-reviewed files (no custom steward UI).

## Phase 2 candidates (not committed)

**Iceberg fork:** `diff_iceberg_branch`, `list_agent_audit_runs`, allow-listed DDL applicator, snapshot tags.  
**Atlas fork:** glossary create/assign, `ensure_classification_typedef`, `export_entity_semantic_projection`, contract↔classification sync helpers.

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
| RDF/SPARQL location | Python Agent Studio tools |
| Audit destination | Iceberg branch via Iceberg MCP |
| Atlas primary MCP | Data-contract fork (not ecole5 alone; not both) |
| Probe/playbook source | Repo files |
| Custom routing UI | Not in Phase 1 |

## Approval

- [ ] Platform / MCP
- [ ] Claims data engineering
- [ ] Semantic / agent team
- [ ] Security (Ranger impact acknowledged)
