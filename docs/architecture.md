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
       └─ Specialist       MCP view label (if any) + playbook write
```

**Structured intake** (user supplies a case/claim id):

1. Orchestrator Delegates once to Manager.
2. Manager calls `run_named_query` for spine, then routing signals (catalog **labels**, not extra MCP tools).
3. Manager passes those JSON payloads, unmodified, into `build_claim_graph` → `validate_claim_graph` → `route_claim`.
4. Manager stops. Orchestrator maps `agent_role` → coworker **Role** and Delegates once.
5. Specialist may run one view label, then the playbook write (`create_litigation_task`, `create_pd_task`, `deny_claim`, or `write_audit_event`; Closeout and `DenyAudit` also `promote_audit_run`). `LitigationSupport`, `RequestPoliceReport`, and Deny steps mark a letter as recommended (`letter_on_request`); Studio `save_claim_letter` runs only when the user asks to write it.

Custom Studio tools **cannot** call MCP in-process. The agent is the only bridge: MCP result → tool argument → session artifact.

Unstructured notes go to Routing Agent (`pre_route_text`, TF-IDF cosine). If a `claim_id` is present, structured intake still wins. Cosine does not override YAML probes.

## Pattern: allow-listed lake access (not free SQL)

MCP V7 registers four tools: `get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`. `execute_query` is not registered.

The **catalog** is compiled into the MCP package (`READ_OPS` / `WRITE_OPS`). Each label has required/optional params and a Python handler that runs curated Impala. Agents discover labels via `list_named_queries` and via Goal text. Invented SQL or unknown labels fail closed.

Claims labels (live lake): `get_claim_spine`, `get_claim_routing_signals`, specialist views (`get_litigation_view`, `get_bi_view`, `get_subrogation_view`, `get_pd_view`, `get_deny_view`), `get_schema`, audit writes (`write_audit_event`, `promote_audit_run`, …), `create_litigation_task`, `create_pd_task`, and `deny_claim`.

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

The playbook can name specialists that have not been configured in Agent Studio yet (`SiuAgent`, `SettlementAgent`, `DataQualityAgent`). Orchestrator must Final Answer the route JSON rather than invent a Role. `DenyAgent` and `HumanCitationReview` are now configured in Agent Studio.

FNOL → payout is **not** one crew run. The claims platform (or BPA) writes Iceberg rows; this stack classifies the current snapshot. Re-chat the Orchestrator with the same claim id after the data changes (`Please process claim 401.`). Do not pass `run_id` or `next_step` in the chat.

### Typical PD path (separate calls)

Live Studio runbook (Impala reset + three Orchestrator chats on **401**): [pd-path-demo.md](pd-path-demo.md). DENIED runbook (impairment flip on **404** + two chats, restore after): [deny-path-demo.md](deny-path-demo.md).

Each row is a later snapshot. Earlier gaps are already filled so a higher probe does not preempt. Case JSON is what `route_claim` sees after `build_claim_graph` (spine + signals). CLOSED, DENIED, insured citation, and coded exclusions (R1.1 / R1.1d / R5.2 / R6.*) win before litigation, SIU, PD gaps, and money. If `subrogation_indicator` is true and `has_subrogation_case` is false, **R4.1** `OpenSubrogationCase` wins before offer, payment, or PD review.

| When the data looks like | Case JSON input (discriminating fields) | First hit | `next_step` |
|---|---|---|---|
| Claim missing / case not built | `{"claim_exists": false}` | R0.1 | `FixDataQuality` |
| Claim exists, triangle incomplete | `{"claim_exists": true, "triangle": false, "claim_status_code": "OPEN"}` | R0.4 | `FixDataQuality` |
| No ADJUSTER role | `{"claim_exists": true, "triangle": true, "claim_status_code": "OPEN", "has_adjuster": false, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false, "coverage_type_codes": ["COLLISION"]}` | R2.3 | `AssignAdjuster` |
| No police report, no incident number | `{"claim_status_code": "OPEN", "has_adjuster": true, "has_police_report": false, "has_incident_report_number": false, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false}` | R2.0 | `CollectIncidentReportNumber` |
| No police report, incident number on file | `{"claim_status_code": "OPEN", "has_adjuster": true, "has_police_report": false, "has_incident_report_number": true, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false}` | R2.1 | `RequestPoliceReport` |
| No fault determination | `{"claim_status_code": "OPEN", "has_adjuster": true, "has_police_report": true, "has_fault_determination": false, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false}` | R2.2 | `DetermineFault` |
| Offer EXTENDED | `{"claim_status_code": "OPEN", "has_adjuster": true, "has_police_report": true, "has_fault_determination": true, "has_extended_offer": true, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false}` | R3.2 | `FollowUpOffer` |
| Offer ACCEPTED, no loss payment | `{"claim_status_code": "OPEN", "has_adjuster": true, "has_police_report": true, "has_fault_determination": true, "has_extended_offer": false, "has_accepted_offer": true, "has_loss_payment": false, "litigation_indicator": false, "has_siu_suspected": false, "subrogation_indicator": false}` | R3.4 | `IssuePayment` |
| Status CLOSED | `{"claim_exists": true, "triangle": true, "claim_status_code": "CLOSED"}` | R1.1 | `CloseoutAudit` |
| Status DENIED | `{"claim_exists": true, "triangle": true, "claim_status_code": "DENIED"}` | R1.1d | `DenyAudit` |
| Insured operator cited | `{"claim_status_code": "OPEN", "insured_operator_cited": true}` | R5.2 | `HumanCitationReview` |
| Unlawful-operation exclusion | `{"claim_status_code": "OPEN", "unlawful_operation_exclusion": true}` | R6.1 | `DenyUnlawfulOperation` |
| Excluded/unlisted operator | `{"claim_status_code": "OPEN", "excluded_operator_exclusion": true}` | R6.2 | `DenyExcludedDriver` |
| Policy not in force on loss | `{"claim_status_code": "OPEN", "policy_not_in_force_on_loss": true}` | R6.3 | `DenyLapsedPolicy` |

PD steps (`CollectIncidentReportNumber`, `RequestPoliceReport`, `DetermineFault`, `PdClaimsReview`) use `get_pd_view` then `create_pd_task` (work item in `pd_task` plus an `agent_run_audit` receipt). `CollectIncidentReportNumber` also inserts `claim_outbound_message` (SMS; no carrier). `RequestPoliceReport` cites `incident_report_number` from `claim_police_intake`, not claim id. Both set `letter_on_request`; a session file via `save_claim_letter` is drafted only if the user asks. Settlement steps on this path still `write_audit_event`. `IssuePayment` means settlement work is due; the payment row still has to land in `claim_payment` from the claims platform. A later intake can then hit R1.1.

Denial: CLOSED stays **approved** (Closeout). DENIED is the other terminal status. R5.2 (`insured_operator_cited`) is Human Review — view + audit, no `deny_claim`. R6.* coded exclusions (`unlawful_operation_exclusion`, `excluded_operator_exclusion`, `policy_not_in_force_on_loss`) go to Deny Agent, which `UPDATE`s `claim_status_code` to `DENIED`. Live deny smokes flip **404** only (`PA-1003`) and restore afterward. Do not use **401** for deny. Repeatable runbook: [deny-path-demo.md](deny-path-demo.md).

## Pattern: two Studio filesystems

| | Workflow Data | Session / artifacts |
|---|---|---|
| Mount | `/workflow_data` (`WORKFLOW_DATA_DIRECTORY`) | `/workspace` (`SESSION_DIRECTORY`) |
| Access | Read-only | Read-write |
| Contents | Schema JSON, playbook, `pack.yaml`, exemplars | `claim_{id}_case.json`, validation JSON, route JSON, `claim_{id}_letter.txt` (R1.2 / R2.1), `claim_{id}_sms.txt` (R2.0) |
| Scope | All tools in the workflow | Same, per run |

Thin tools: each Studio tool is `tool.py` + `requirements.txt` only. Shared logic is `ins-claims-agent` pinned from git.

MCP is a **separate** `uvx` stdio process started by the workflow engine. It inherits engine env plus the MCP registration `env` block. It does **not** get the tool-sandbox `/workflow_data` mount. Lake credentials (`IMPALA_*`) live on that MCP env, not in tool `UserParameters`.

## Pattern: domain packs (same control plane)

A **pack** swaps schema JSON, playbook, cosine exemplars, and (for offline tests) fixture payloads. Studio tools stay `build_claim_graph` / `claim_id`. Claims MCP stays claims-only.

Claims today is the **default product**: walk-up to repo-root `ontology/` + `playbook/`. Do not move those trees until 402 has been proven from a pointer pack.

**Distributions (live):** Impala database `retirement_distributions` + MCP `iceberg-mcp-server-finserv` (`INS_FINSERV_MCP_V1`). Compiled labels only — no `PACK_ROOT`. Pack fixture JSON remains golden for `agent_studio/tests/test_packs.py`.

**Rollovers:** still fixture / `PACK_ROOT` on the claims MCP until distributions e2e is proven. Details: [finserv-pattern-pack-status.md](finserv-pattern-pack-status.md).

## Pattern: agents as a thin control plane

| Agent | Tools | Job |
|---|---|---|
| Orchestrator | None | Sequence and handoff; user cannot skip it |
| Manager | MCP + build/validate/route | Intake and one-shot catalog calls; stop after route |
| Routing | `pre_route_text` only | Coarse NL label; not authoritative when an id is present |
| Specialist | MCP (+ `save_claim_letter` when mapped) | One view (if mapped) + playbook write |

CrewAI `Delegate` matches **Role**, not Name. Manager Role must be exactly `Manager agent`.

The LLM is justified for NL ops and unstructured text. Hardship, RMD, ERISA, litigation, closeout, and coded denial are probe results.

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
| `routing_reason` | One-sentence why this `next_step` (playbook copy, not LLM). |
| `routing_summary` | Ready-to-paste block: next step, lane, why, checks. Studio Observation leads with this. |
| `checks` | Evaluated probes as title + status (`assigned` / `did_not_apply`) + detail. Later playbook checks are omitted with `later_checks_not_run`. |
| `reason_probe_ids` | Probe ids evaluated this snapshot (audit / tests). Do not lead the chat with these. |
| `allowed_tools` | Catalog labels or Studio tools the specialist may call. |
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
| `create_litigation_task` | Catalog write: `INSERT` one `litigation_task` row from `run_id` + `event_json`. |
| `create_pd_task` | Catalog write: `INSERT` one `pd_task` row (`COLLECT_INCIDENT_NUMBER` / `REQUEST_POLICE_REPORT` / `DETERMINE_FAULT` / `PD_REVIEW`) and one `agent_run_audit` receipt. `COLLECT_INCIDENT_NUMBER` also inserts `claim_outbound_message`. |
| `get_deny_view` | Catalog read: operator / policy / police business columns for deny and citation review (no PK/FK). |
| `deny_claim` | Catalog write: `UPDATE claim` to `DENIED` (refuses CLOSED and already-DENIED) plus an `agent_run_audit` receipt. Not used on `DenyAudit`. |
| `promote_audit_run` | No-op success on Impala (rows already on main). |
| Routing signals / `get_claim_routing_signals` | Named query for extra facts the graph and probes need (flags, related ids). |

**Studio / CrewAI**

| Term | Meaning |
|---|---|
| `Manager agent` | Exact CrewAI **Role** string required for Delegate to Manager. |
| Final Answer | CrewAI terminal reply. Orchestrator uses this when no coworker exists for a role. |
| Configured in Agent Studio | Name / Role / Backstory / Goal (and tools table) set on the agent in Agent Studio. |
| Workflow Data | Studio read-only tree: schema JSON, playbook, `pack.yaml`, exemplars. |
| `UserParameters` | Studio tool config fields. Do not put lake credentials here. |
| `WORKFLOW_DATA_DIRECTORY` | Env for the Workflow Data mount (`/workflow_data`). |
| `SESSION_DIRECTORY` | Env for per-run artifacts (`/workspace`). |
| Exemplars | Labeled NL snippets for cosine `pre_route_text`. |
| `save_claim_letter` | Studio tool: write `claim_{id}_letter.txt` to the session folder when the user asks. Does not send mail. Playbook `letter_on_request` marks the letter as recommended next work. |

**Packs / demo**

| Term | Meaning |
|---|---|
| Pack | Directory that swaps schema JSON, playbook, exemplars, and (for offline tests) fixtures. Studio tool names stay the same. |
| `PACK_ROOT` | Host path on the **claims** MCP for rollover (and legacy) fixtures. Do not set on `iceberg-mcp-server-finserv`. |
| `PACK_ID` | Rejected for the live distributions demo. Finserv MCP is a compiled catalog, not a fixture bake-in. |
| Fixture | Canned JSON for a named query. Lake-shaped payload, not a routing rule. |
| Pointer pack | `pack.yaml` that points at existing claims trees without moving them. |
| 401 | PD / subro live seed (collision). Do not use for deny. |
| 402 | Proven live auto-claims seed (Litigation e2e). Not a version number. |
| 403 | CLOSED live seed (Closeout). |
| 404 | Deny-path live seed (`PA-1003`). Impairment flip does not touch 401. |
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
| `ddl/hive_iceberg/` | Iceberg DDL (claims, audit, `litigation_task`, `pd_task`); claims seed includes **404** deny file (`car_insurance_claims_seed_404.sql` for already-loaded lakes) |
| `docs/pd-path-demo.md` | Repeatable PD demo on claim 401 (Impala + Orchestrator) |
| `docs/deny-path-demo.md` | Repeatable DENIED demo on claim 404 (impairment flip + Orchestrator) |
| `mcp_forks/iceberg-mcp-server-claims/` | Impala MCP V7 + named catalog |
| `agent_studio/src/ins_claims_agent/` | Shared build / validate / route / pack loader |
| `agent_studio/studio_tools/` | Thin Studio tools + claims agents to configure in Agent Studio |
| `packs/` | Finserv demo domains (same intake sequence) |
