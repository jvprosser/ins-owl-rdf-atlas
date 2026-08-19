# Post-route agents

After `route_claim`, the decision’s `agent_role` + `allowed_tools` name the next worker.
**Lake I/O stays on MCP.** Letters are Studio file writes (`save_claim_letter`), not mail send. Playbook `letter_on_request` marks a letter as recommended next work; agents draft it only when the user asks.

## Playbook tool → MCP tool

| Playbook `allowed_tools` | MCP |
|---|---|
| `get_litigation_view` | `run_named_query` label `get_litigation_view` |
| `create_litigation_task` | `run_named_write` label `create_litigation_task` |
| `get_bi_view` | `run_named_query` label `get_bi_view` |
| `get_subrogation_view` | `run_named_query` label `get_subrogation_view` |
| `get_pd_view` | `run_named_query` label `get_pd_view` |
| `create_pd_task` | `run_named_write` label `create_pd_task` |
| `get_deny_view` | `run_named_query` label `get_deny_view` |
| `deny_claim` | `run_named_write` label `deny_claim` |
| `write_audit_event` | `run_named_write` label `write_audit_event` |
| `promote_audit_run` | `run_named_write` label `promote_audit_run` |
| `save_claim_letter` | Studio custom tool: writes `SESSION_DIRECTORY/claim_{id}_letter.txt` |
| `build_claim_graph` / `validate_claim_graph` | Existing Studio custom tools |

V7 MCP registers only `get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`. Playbook names are catalog **labels**, not MCP tool names.

Optional catalog lifecycle labels (not used on the one-shot intake path): `begin_agent_audit_run`, `append_agent_audit_evidence`, `abandon_agent_audit_run`.

## Recommended Studio agents

### Claims Orchestrator (no tools)
**Paste-ready definition:** [`agents/orchestrator_agent.md`](agents/orchestrator_agent.md)

NL front door; delegates structured claim intake, unstructured pre-route, and post-route work.

**CrewAI coworker names:** `Delegate work to coworker` requires the coworker string to match the agent’s **Role** exactly (see Studio’s “must be one of” error). Prefer short Roles:

| Agent | Role (exact coworker string) | Playbook `agent_role` |
|---|---|---|
| Manager | `Manager agent` | (intake; not a route worker) |
| Routing | `Routing Agent` | (unstructured cosine only) |
| Litigation | `Litigation Agent` | `LitigationAgent` |
| Subrogation | `Subrogation Agent` | `SubrogationAgent` |
| BI | `BI Claims Agent` | `BiClaimsAgent` |
| PD | `PD Claims Agent` | `PdClaimsAgent` |
| Closeout | `Closeout Agent` | `CloseoutAgent` |
| Deny | `Deny Agent` | `DenyAgent` |
| Human review | `Human Review Agent` | `HumanReviewAgent` |
| SIU | `SIU Agent` | `SiuAgent` |
| Settlement | `Settlement Agent` | `SettlementAgent` |
| Data quality | `Data Quality Agent` | `DataQualityAgent` |

If Manager Role is still the long sentence Studio generated, Orchestrator must paste that **entire** Role as `coworker` — or rename Manager Role to `Manager agent` and retry.

On unstructured text: delegate to `Routing Agent`. If cosine `needs_llm` is false, hand off to the returned `coworker`. If `claim_id` is also present, still run Manager structured claim intake — cosine does not override YAML probes.

### Routing Agent (Studio `pre_route_text` only)
**Paste-ready definition:** [`agents/routing_agent.md`](agents/routing_agent.md)

NL first-touch triage. Cosine vs a small `LITIGATION` / `GENERAL_CLAIMS` catalog; `needs_llm` when the score is low. **Does not replace structured claim intake.** If `claim_id` is present, Manager structured claim intake is authoritative.

### Claims Manager (MCP + build / validate / route Studio tools)
**Paste-ready definition:** [`agents/manager_agent.md`](agents/manager_agent.md)

**Role (exact for CrewAI coworker):** `Manager agent`  
**Tools:** MCP `get_server_info` / `run_named_query` / `run_named_write`; Studio `build` / `validate` / `route`.  
**Job:** Structured claim intake when asked to intake/route; **if asked for one MCP tool by name, call it once and stop**. After `route_claim`, STOP — Orchestrator hands off to the specialist named by `agent_role`.

### Litigation Agent (MCP + `save_claim_letter` on request)
**Finished paste-ready definition:** [`agents/litigation_agent.md`](agents/litigation_agent.md)

Use when route returns `LitigationAgent` / `CompleteLitigationFile` / `EscalateDiscovery` / `LitigationSupport`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Litigation Agent` |
| Tools | MCP `run_named_query` / `run_named_write`; Studio `save_claim_letter` (LitigationSupport letter only when the user asks) |
| Backstory / Goal | Copy from `agents/litigation_agent.md` |

### Subrogation Agent (MCP only)
**Paste-ready definition:** [`agents/subrogation_agent.md`](agents/subrogation_agent.md)

Use when route returns `SubrogationAgent` / `OpenSubrogationCase` / `PursueSubrogationRecovery`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Subrogation Agent` |
| Tools | `run_named_query` label `get_subrogation_view`; `run_named_write` `write_audit_event` |
| Lake smoke | claim **401**, case **8801** (direct specialist; e2e 401 may route PD instead) |

### BI Claims Agent (MCP only)
**Paste-ready definition:** [`agents/bi_claims_agent.md`](agents/bi_claims_agent.md)

Use when route returns `BiClaimsAgent` / `BiClaimsReview` / `CaptureInjuryDetails`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `BI Claims Agent` |
| Tools | `run_named_query` label `get_bi_view`; `run_named_write` `write_audit_event` |
| Lake smoke | claim **402**, injuries **5501** / **5502** (direct specialist; e2e 402 is litigation-first) |

### PD Claims Agent (MCP + `save_claim_letter` on request)
**Paste-ready definition:** [`agents/pd_claims_agent.md`](agents/pd_claims_agent.md)

Use when route returns `PdClaimsAgent` / `RequestPoliceReport` / `DetermineFault` / `PdClaimsReview`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `PD Claims Agent` |
| Tools | `run_named_query` label `get_pd_view`; `run_named_write` `create_pd_task`; Studio `save_claim_letter` (`RequestPoliceReport` letter only when the user asks) |
| Lake smoke | claim **401** `PdClaimsReview` (direct specialist). Apply `pd_task` DDL before the write. Full three-snapshot runbook: [`docs/pd-path-demo.md`](../../docs/pd-path-demo.md). |

### Closeout Agent (MCP only)
**Paste-ready definition:** [`agents/closeout_agent.md`](agents/closeout_agent.md)

Use when route returns `CloseoutAgent` / `CloseoutAudit` (seed **403** is CLOSED).

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Closeout Agent` |
| Tools | `run_named_write` `write_audit_event` then `run_named_write` `promote_audit_run` |
| Lake smoke | claim **403**, `run_id` `demo-403-close` (Impala promote is `mode=table_append`) |

### Deny Agent (MCP + `save_claim_letter` on request)
**Paste-ready definition:** [`agents/deny_agent.md`](agents/deny_agent.md)

Use when route returns `DenyAgent` / `DenyUnlawfulOperation` / `DenyExcludedDriver` / `DenyLapsedPolicy` / `DenyAudit`. Closeout stays CLOSED-only.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Deny Agent` |
| Tools | `run_named_query` label `get_deny_view`; R6.* `run_named_write` `deny_claim`; `DenyAudit` `write_audit_event` then `promote_audit_run`. Studio `save_claim_letter` only when the user asks |
| Lake smoke | Flip **401** only (impairment / excluded / lapsed). Restore afterward. Re-intake after deny → `DenyAudit`. |

### Human Review Agent (citation analysis; MCP audit only)
**Paste-ready definition:** [`agents/human_review_agent.md`](agents/human_review_agent.md)

Use when route returns `HumanReviewAgent` / `HumanCitationReview` (insured operator cited). Orchestrator still Final Answers the route JSON for `HumanReviewOrWait`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Human Review Agent` |
| Tools | `run_named_query` label `get_deny_view`; `run_named_write` `write_audit_event`. Never `deny_claim`. No letter |
| Lake smoke | Flip **401** insured `was_cited_indicator` true. Status stays OPEN. Restore afterward. |

### Settlement / SIU / Data Quality (MCP audit only)
For roles whose playbook tools are still only `write_audit_event`: attach MCP audit tools; prompt to append an event and return a short summary. Defer richer views until needed.

## End-to-end demo (claim 402)

Paste Orchestrator Goal + user prompt from [`agents/orchestrator_agent.md`](agents/orchestrator_agent.md). Manager Goal must STOP after `route_claim`. Orchestrator maps `agent_role` → coworker Role (not litigation-only).

1. Orchestrator → Manager: structured claim intake (`run_named_query` spine then signals → build → validate → route).
2. Route returns `agent_role` (402: `LitigationAgent` / `EscalateDiscovery`).
3. Orchestrator → mapped specialist: catalog read (if the map has a view) then the write label for that `next_step` (`create_litigation_task` on 402; Closeout also `promote_audit_run`). `run_id` `demo-<claim_id>-e2e`.
4. Orchestrator Final Answer: route decision + specialist summary + write JSON.

Specialists other than Litigation still need Studio pastes in the same Crew, or step 3 ends with coworker-not-found.

Direct specialist smokes (skip intake): Subrogation **401** (`subrogation_agent.md`), BI **402** (`bi_claims_agent.md`), Closeout **403** (`closeout_agent.md`), PD **401** (`pd_claims_agent.md`), Deny **401** (`deny_agent.md`), Human Review **401** (`human_review_agent.md`).

## Unstructured front door

Paste Orchestrator Goal from [`agents/orchestrator_agent.md`](agents/orchestrator_agent.md). Routing paste: [`agents/routing_agent.md`](agents/routing_agent.md).

1. Orchestrator → Routing Agent: `pre_route_text` once (no MCP).
2. If `needs_llm` is true: Final Answer the Routing classify. STOP.
3. If `claim_id` is set: structured claim intake is authoritative (cosine is advisory).
4. If no `claim_id` and `needs_llm` is false: Final Answer `label` / `score` / `coworker`. Do not run lake tools unless the user also gave a claim_id.

## Restart note

Restart `iceberg-mcp-server-claims` after pulling main so identity is **`INS_CLAIMS_MCP_V7`** / **`0.3.7`** (catalog includes `get_deny_view` / `deny_claim`).
