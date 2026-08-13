# Post-route agents

After `route_claim`, the decision’s `agent_role` + `allowed_tools` name the next worker.
**All lake I/O stays on MCP** (Claims Manager or specialist agents that have MCP attached). No new Studio Python tools are required for audit/views.

## Playbook tool → MCP tool

| Playbook `allowed_tools` | MCP |
|---|---|
| `get_litigation_view` | `run_named_query` label `get_litigation_view` (legacy tool still registered) |
| `get_bi_view` | `run_named_query` label `get_bi_view` |
| `get_subrogation_view` | `run_named_query` label `get_subrogation_view` |
| `write_audit_event` | `run_named_write` label `write_audit_event` |
| `promote_audit_run` | `run_named_write` label `promote_audit_run` |
| `build_claim_graph` / `validate_claim_graph` | Existing Studio custom tools |

Optional lifecycle (not in playbook, useful for Style B): `begin_agent_audit_run`, `append_agent_audit_evidence`, `abandon_agent_audit_run`.

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
| Closeout | `Closeout Agent` | `CloseoutAgent` |
| SIU | `SIU Agent` | `SiuAgent` |
| PD | `PD Claims Agent` | `PdClaimsAgent` |
| Settlement | `Settlement Agent` | `SettlementAgent` |
| Data quality | `Data Quality Agent` | `DataQualityAgent` |
| Human review | `Human Review Agent` | `HumanReviewAgent` |

If Manager Role is still the long sentence Studio generated, Orchestrator must paste that **entire** Role as `coworker` — or rename Manager Role to `Manager agent` and retry.

On unstructured text: delegate to `Routing Agent`. If cosine `needs_llm` is false, hand off to the returned `coworker`. If `claim_id` is also present, still run Manager structured claim intake — cosine does not override SPARQL.

### Routing Agent (Studio `pre_route_text` only)
**Paste-ready definition:** [`agents/routing_agent.md`](agents/routing_agent.md)

NL first-touch triage. Cosine vs a small `LITIGATION` / `GENERAL_CLAIMS` catalog; `needs_llm` when the score is low. **Does not replace structured claim intake.** If `claim_id` is present, Manager structured claim intake is authoritative.

### Claims Manager (MCP + graph Studio tools)
**Paste-ready definition:** [`agents/manager_agent.md`](agents/manager_agent.md)

**Role (exact for CrewAI coworker):** `Manager agent`  
**Tools:** MCP spine/signals (and one-shot catalog tools); Studio `build` / `validate` / `route`.  
**Job:** Structured claim intake when asked to intake/route; **if asked for one MCP tool by name, call it once and stop**. After `route_claim`, STOP — Orchestrator hands off to the specialist named by `agent_role`.

### Litigation Agent (MCP only)
**Finished paste-ready definition:** [`agents/litigation_agent.md`](agents/litigation_agent.md)

Use when route returns `LitigationAgent` / `LitigationSupport`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Litigation Agent` |
| Tools | Prefer `run_named_query` / `run_named_write` (legacy view/audit names forbidden in Goal) |
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

### Closeout Agent (MCP only)
**Name:** `Closeout Agent`  
**Role:** Terminal closeout specialist for CLOSED claims.  
**Backstory:** You finalize routed closeout steps using audit MCP helpers only.  
**Goal:** Given `run_id` and route decision `CloseoutAudit`, call `write_audit_event` then `promote_audit_run`. Explain completion to the orchestrator. Impala promote may be a no-op (table-append mode).

### PD / Settlement / SIU / Human Review (MCP audit only)
For roles whose playbook tools are only `write_audit_event`: attach MCP audit tools; prompt to append an event and return a short summary. Defer richer views until needed.

## End-to-end demo (claim 402)

Paste Orchestrator Goal + user prompt from [`agents/orchestrator_agent.md`](agents/orchestrator_agent.md). Manager Goal must STOP after `route_claim`. Orchestrator maps `agent_role` → coworker Role (not litigation-only).

1. Orchestrator → Manager: structured claim intake (spine → signals → build → validate → route).
2. Route returns `agent_role` (402: `LitigationAgent` / `LitigationSupport`).
3. Orchestrator → mapped specialist: catalog read (if the map has a view) then `run_named_write` (`write_audit_event`). `run_id` `demo-<claim_id>-e2e`.
4. Orchestrator Final Answer: route decision + specialist summary + write JSON.

Specialists other than Litigation still need Studio pastes in the same Crew, or step 3 ends with coworker-not-found.

Direct specialist smokes (skip intake): Subrogation **401** (`subrogation_agent.md`), BI **402** (`bi_claims_agent.md`). Seed **403** is CLOSED → Closeout, not BI.

## Restart note

Restart `iceberg-mcp-server-claims` after pulling main so new MCP tool names appear (`get_*_view`, `write_audit_event`, `promote_audit_run`).
