# Architecture and patterns

High-level view for data engineers. This stack routes operational cases (auto claims today; retirement distributions/rollovers as the same control plane) on Cloudera: Iceberg via Impala, a Git-reviewed JSON case schema + YAML playbook, and Cloudera AI Agent Studio. The LLM is the NL front door. It is not the rules engine.

Related: [ADR 0001](adr/0001-agent-studio-mcp-and-tool-layout.md), [MCP fork charter](mcp-fork-charter.md), [Atlas/Ranger plan](atlas-ranger-integration-plan.md), [finserv packs](finserv-pattern-pack.md), [probe/action test prompts](probe-action-tests.md), [RDF/SPARQL restore](rdf-sparql-branch.md).

## Problem split

Three different jobs are easy to collapse. They are kept separate on purpose.

| Job | Question | Owner |
|---|---|---|
| Lake I/O | What rows exist for this id, and what may we write? | Iceberg + Impala + a **named-query catalog** on MCP |
| Instance meaning | What is this case, and is the spine intact? | Session case JSON + field checks |
| Next work | Which lane and specialist run next? | Git playbook + YAML probes |

Atlas (deferred) would answer “what *is* this table/column in the ontology?” Ranger (deferred) would answer “who may see or change it?” Neither stores the per-run graph or chooses `next_step`.

## Runtime topology

```text
User
  └─ Orchestrator          no tools; Delegate only
       ├─ Manager          MCP catalog + Studio build / validate / route
       ├─ Routing Agent    cosine pre_route_text (NL triage only)
       └─ Specialist       MCP view label (if any) + write_audit_event
```

**Structured intake** (user supplies a case/claim id):

1. Orchestrator Delegates once to Manager.
2. Manager calls `run_named_query` for spine, then routing signals (catalog **labels**, not extra MCP tools).
3. Manager passes those JSON payloads, unmodified, into `build_claim_graph` → `validate_claim_graph` → `route_claim`.
4. Manager stops. Orchestrator maps `agent_role` → coworker **Role** and Delegates once.
5. Specialist may run one view label, then `run_named_write` `write_audit_event` (Closeout also `promote_audit_run`).

Custom Studio tools **cannot** call MCP in-process. The agent is the only bridge: MCP result → tool argument → session artifact.

Unstructured notes go to Routing Agent (`pre_route_text`, TF-IDF cosine). If a `claim_id` is present, structured intake still wins. Cosine does not override YAML probes.

## Pattern: allow-listed lake access (not free SQL)

MCP V7 registers four tools: `get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`. `execute_query` is not registered.

The **catalog** is compiled into the MCP package (`READ_OPS` / `WRITE_OPS`). Each label has required/optional params and a Python handler that runs curated Impala. Agents discover labels via `list_named_queries` and via Goal text. Invented SQL or unknown labels fail closed.

Claims labels (live lake): `get_claim_spine`, `get_claim_routing_signals`, specialist views (`get_litigation_view`, `get_bi_view`, `get_subrogation_view`), `get_schema`, and audit writes (`write_audit_event`, `promote_audit_run`, …).

Audit lands in Iceberg (`agent_run_audit` / `agent_run_evidence`), partitioned by `run_id`. Impala mode is **table-append**; `promote_audit_run` is a no-op success (`mode=table_append`). Hive WAP branches are a later fork, not this path.

Think of the catalog as a **published data product API** over the same tables you would otherwise expose as views — except the consumer is an agent, and the contract is Git-reviewed Python rather than a BI semantic layer.

## Pattern: session case JSON, Git schema

The schema is JSON in Git (`ontology/claims.json`, or a pack `ontology/*.json`). It is not stored in Atlas and not queried as a lake table.

`build_claim_graph` materializes **this run’s** case document: claim/policy/vehicle triangle fields (auto) or mapped literals/booleans (packs). Output is `SESSION_DIRECTORY/claim_{id}_case.json` (`/workspace` in Studio). That file is the only instance document. It is not written back to Iceberg.

`validate_claim_graph` checks required fields on that JSON (auto: exists / policy / vehicle / triangle). It is instance quality for routing, not a table-level ODCS contract.

Mapping from lake JSON → case JSON is code (claims builder) or `pack.yaml` field maps (generic builder). There is no runtime join from Atlas IRIs into the builder today.

## Pattern: probes + playbook as the router

`route_claim` evaluates Git YAML probes in playbook priority order (`ASK` / `SELECT` on case JSON paths). The first matching action wins (`next_step`, `agent_role`, `lane`, `allowed_tools`, `terminal`). Default action is human-review/wait.

Probes bind field paths on the case document (`litigation_indicator`, `triangle`, …). Rules are reviewed as YAML, not as prompt text and not as Iceberg UI config.

The playbook can name specialists that have no Studio paste yet (`PdClaimsAgent`, `SiuAgent`, …). Orchestrator must Final Answer the route JSON rather than invent a Role.

## Pattern: two Studio filesystems

| | Workflow Data | Session / artifacts |
|---|---|---|
| Mount | `/workflow_data` (`WORKFLOW_DATA_DIRECTORY`) | `/workspace` (`SESSION_DIRECTORY`) |
| Access | Read-only | Read-write |
| Contents | Schema JSON, playbook, `pack.yaml`, exemplars | `claim_{id}_case.json`, validation JSON, route JSON |
| Scope | All tools in the workflow | Same, per run |

Thin tools: each Studio tool is `tool.py` + `requirements.txt` only. Shared logic is `ins-claims-agent` pinned from git.

MCP is a **separate** `uvx` stdio process started by the workflow engine. It inherits engine env plus the MCP registration `env` block. It does **not** get the tool-sandbox `/workflow_data` mount. Lake credentials (`IMPALA_*`) live on that MCP env, not in tool `UserParameters`.

## Pattern: domain packs (same control plane)

A **pack** swaps schema JSON, playbook, cosine exemplars, and (for demos) fixture payloads. It does not clone MCP and does not rename Studio tools. Tool param remains `claim_id`.

Claims today is the **default product**: walk-up to repo-root `ontology/` + `playbook/`. Do not move those trees until 402 has been proven from a pointer pack.

Finserv demo packs (`packs/retirement_distributions`, `packs/retirement_rollovers`) add a generic graph builder and JSON **fixtures** — canned `run_named_query` bodies so there is no distributions/rollovers Impala schema yet. Fixtures are lake-shaped payloads, not routing rules.

Studio tools can load a pack from Workflow Data (`pack.yaml`). MCP fixture merge was designed around a host path (`PACK_ROOT`). That path is not available on the Studio MCP host, and a live `list_named_queries` stayed on the claims catalog. Resume plan: ship fixtures inside the MCP package and select with `PACK_ID`. Details: [finserv-pattern-pack-status.md](finserv-pattern-pack-status.md).

## Pattern: agents as a thin control plane

| Agent | Tools | Job |
|---|---|---|
| Orchestrator | None | Sequence and handoff; user cannot skip it |
| Manager | MCP + build/validate/route | Intake and one-shot catalog calls; stop after route |
| Routing | `pre_route_text` only | Coarse NL label; not authoritative when an id is present |
| Specialist | MCP only | One view (if mapped) + audit write |

CrewAI `Delegate` matches **Role**, not Name. Manager Role must be exactly `Manager agent`.

The LLM is justified for NL ops and unstructured text. Hardship, RMD, ERISA, litigation, and closeout are probe results.

## Governance (not on the runtime path)

| Concern | Today | Later |
|---|---|---|
| Schema → ontology bind | Implicit (SQL handlers + builder maps + Git schema JSON) | Atlas business metadata `ontology.iri` on table/column GUIDs |
| Access / masking | Impala principal on MCP; catalog fail-closed for SQL | Ranger policies; prefer tags from Atlas classifications |
| Contract / quality | MCP catalog + per-run case JSON validate | ODCS / Atlas contracts for **table** drift; do not replace instance validate |

Atlas is complementary catalog glue. It is not a triple store and not a SPARQL endpoint. Ranger does not define Claim vs LitigationCase. Session case JSON and `event_json` are outside Impala masking.

## What is intentionally not here

- Persistent triple store or SPARQL-in-MCP
- Agent-authored SQL, Ranger policies, or playbook rules
- Per-label MCP tools (labels stay catalog keys)
- Dual Atlas servers
- Packing claims until a second live product must share one Studio/MCP install

## Terms

**Schema / case JSON**

| Term | Meaning |
|---|---|
| Schema JSON | Field list for the case document (`ontology/claims.json`). Not a lake table. |
| Case JSON | Instance document for **this run** (`claim_{id}_case.json`). |
| Triangle | Claims check that policy, vehicle, and `policy_covers_vehicle` are set. |
| Spine / `get_claim_spine` | Named query for the core claim row used to build the case JSON. |
| Session case | Per-run JSON in `SESSION_DIRECTORY`. Not written to Iceberg. |

**Playbook / route**

| Term | Meaning |
|---|---|
| Probe | YAML `ASK`/`SELECT` on case JSON paths. First playbook match wins. |
| Playbook | YAML that orders probes and names the action. Not an ops runbook. |
| `next_step` | Action id the specialist should perform. |
| `agent_role` | Specialist coworker to Delegate to. |
| `lane` | Routing bucket (litigation, BI, closeout, …). |
| `allowed_tools` | Catalog labels that specialist may call. |
| `terminal` | Router says this run is done (no further specialist). |
| Structured intake | User supplied a case/claim id. YAML probes win over cosine. |

**MCP / audit**

| Term | Meaning |
|---|---|
| Named-query catalog | Compiled allow-list: label → params → Impala handler. |
| Label | Catalog key (`get_claim_spine`). Not a registered MCP tool. |
| MCP V7 | Current four-tool surface: info, list, named read, named write. |
| `READ_OPS` / `WRITE_OPS` | The two dicts that implement that catalog. |
| `event_json` | JSON body on `write_audit_event`. Known keys become typed columns; the full object is stored in `payload_json`. |
| Table-append / `mode=table_append` | Impala writes audit rows to main tables. No Iceberg branch. |
| Hive WAP branches | Write-audit-publish on Iceberg branches. Later Hive fork; not this path. |
| `write_audit_event` | Catalog write: `INSERT` one `agent_run_audit` row. |
| `promote_audit_run` | No-op success on Impala (rows already on main). |
| Routing signals / `get_claim_routing_signals` | Named query for extra facts the graph and probes need (flags, related ids). |

**Studio / CrewAI**

| Term | Meaning |
|---|---|
| `Manager agent` | Exact CrewAI **Role** string required for Delegate to Manager. |
| Final Answer | CrewAI terminal reply. Orchestrator uses this when no coworker exists for a role. |
| Studio paste | Name / Role / Backstory / Goal (and tools table) copied into Agent Studio. |
| Workflow Data | Studio read-only tree: ontology, probes, playbook, `pack.yaml`, exemplars. |
| `UserParameters` | Studio tool config fields. Do not put lake credentials here. |
| `WORKFLOW_DATA_DIRECTORY` | Env for the Workflow Data mount (`/workflow_data`). |
| `SESSION_DIRECTORY` | Env for per-run artifacts (`/workspace`). |
| Exemplars | Labeled NL snippets for cosine `pre_route_text`. |
| `pre_route_text` | Studio tool that TF-IDF/cosine-labels unstructured notes. |

**Packs / demo**

| Term | Meaning |
|---|---|
| Pack | Directory that swaps schema JSON, playbook, exemplars, and (for demos) fixtures. Same MCP and Studio tool names. |
| `PACK_ROOT` | Host path on the MCP process to a pack with `catalog_fixtures.json`. Not the tool sandbox. |
| `PACK_ID` | Planned string to select fixtures baked into the MCP package (`unset` = live claims Impala). |
| Fixture | Canned JSON for a named query. Lake-shaped payload, not a routing rule. |
| Pointer pack | `pack.yaml` that points at existing claims trees without moving them. |
| 402 | Proven live auto-claims seed (Litigation e2e). Not a version number. |
| Finserv | Retirement distributions/rollovers demos on this control plane. |

**Governance**

| Term | Meaning |
|---|---|
| ODCS | Open Data Contract Standard. Table-level contract/quality. Does not replace per-run case JSON validate. |
| `ontology.iri` | Planned Atlas business-metadata key: table/column GUID → ontology IRI. |

## Repo map

| Path | Role |
|---|---|
| `ontology/`, `playbook/` | Live claims schema JSON and router (402) |
| `ddl/hive_iceberg/` | Audit table DDL |
| `mcp_forks/iceberg-mcp-server-claims/` | Impala MCP V7 + named catalog |
| `agent_studio/src/ins_claims_agent/` | Shared build / validate / route / pack loader |
| `agent_studio/studio_tools/` | Thin Studio tools + claims agent pastes |
| `packs/` | Finserv demo domains (same intake sequence) |
