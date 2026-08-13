# Post-route agents (Path A)

After `route_claim`, the decision’s `agent_role` + `allowed_tools` name the next worker.
Under S1, **all lake I/O stays on MCP** (Claims Manager or specialist agents that have MCP attached). No new Studio Python tools are required for audit/views.

## Playbook tool → MCP tool

| Playbook `allowed_tools` | MCP tool (`iceberg-mcp-server-claims`) |
|---|---|
| `get_litigation_view` | `get_litigation_view` |
| `get_bi_view` | `get_bi_view` |
| `get_subrogation_view` | `get_subrogation_view` |
| `write_audit_event` | `write_audit_event` (alias of `append_agent_audit_event`) |
| `promote_audit_run` | `promote_audit_run` (alias of `promote_agent_audit_run`) |
| `build_claim_graph` / `validate_claim_graph` | Existing Studio custom tools |

Optional lifecycle (not in playbook, useful for Style B): `begin_agent_audit_run`, `append_agent_audit_evidence`, `abandon_agent_audit_run`.

## Recommended Studio agents

### Claims Orchestrator (no tools)
NL front door; delegates Path A, unstructured pre-route, and post-route work.

**CrewAI coworker names:** `Delegate work to coworker` requires the coworker string to match the agent’s **Role** exactly (see Studio’s “must be one of” error). Prefer short Roles:

| Agent | Role (exact coworker string) |
|---|---|
| Manager | `Manager agent` |
| Routing | `Routing Agent` |
| Litigation | `Litigation Agent` |
| Subrogation | `Subrogation Agent` |
| BI | `BI Claims Agent` |
| Closeout | `Closeout Agent` |

If Manager Role is still the long sentence Studio generated, Orchestrator must paste that **entire** Role as `coworker` — or rename Manager Role to `Manager agent` and retry.

On unstructured text: delegate to `Routing Agent`. If cosine `needs_llm` is false, hand off to the returned `coworker`. If `claim_id` is also present, still run Manager Path A — cosine does not override SPARQL.

### Routing Agent (Studio `pre_route_text` only)
**Paste-ready definition:** [`agents/routing_agent.md`](agents/routing_agent.md)

NL first-touch triage. Cosine vs a small `LITIGATION` / `GENERAL_CLAIMS` catalog; `needs_llm` when the score is low. **Does not replace Path A.** If `claim_id` is present, Manager Path A is authoritative.

### Claims Manager (MCP + graph Studio tools)
**Role (exact for CrewAI coworker):** `Manager agent`  
**Tools:** MCP spine/signals/views/audit; Studio `build` / `validate` / `route`.  
**Job:** Path A when asked to intake/route; **if asked for one MCP tool by name, call it once and stop** (do not force Path A). After route, run `allowed_tools` or hand off to a specialist below.

### Litigation Agent (MCP only)
**Finished paste-ready definition:** [`agents/litigation_agent.md`](agents/litigation_agent.md)

Use when route returns `LitigationAgent` / `LitigationSupport`.

| Field | Value |
|---|---|
| Name / Role (exact coworker) | `Litigation Agent` |
| Tools | MCP `get_litigation_view`, `write_audit_event` only |
| Backstory / Goal | Copy from `agents/litigation_agent.md` |

### Subrogation Agent (MCP only)
**Name:** `Subrogation Agent`  
**Role:** Post-route subrogation specialist.  
**Backstory:** You act when the router assigns SubrogationAgent. You use `get_subrogation_view` and `write_audit_event` only.  
**Goal:** Load subrogation case facts for `claim_id`, explain demand/recovered/status, write an audit event. No free-form SQL.

### BI Claims Agent (MCP only)
**Name:** `BI Claims Agent`  
**Role:** Post-route bodily-injury specialist.  
**Backstory:** You act when the router assigns BiClaimsAgent. You use `get_bi_view` and `write_audit_event` only.  
**Goal:** Load injury rows for `claim_id`, summarize severity/regions, write an audit event. No free-form SQL.

### Closeout Agent (MCP only)
**Name:** `Closeout Agent`  
**Role:** Terminal closeout specialist for CLOSED claims.  
**Backstory:** You finalize routed closeout steps using audit MCP helpers only.  
**Goal:** Given `run_id` and route decision `CloseoutAudit`, call `write_audit_event` then `promote_audit_run`. Explain completion to the orchestrator. Impala promote may be a no-op (table-append mode).

### PD / Settlement / SIU / Human Review (MCP audit only)
For roles whose playbook tools are only `write_audit_event`: attach MCP audit tools; prompt to append an event and return a short summary. Defer richer views until needed.

## Minimal demo after Path A route (claim 402)

1. Orchestrator sees `LitigationSupport` / `LitigationAgent`.
2. Delegates to Litigation Agent with `claim_id=402` and a `run_id` (e.g. `demo-402`).
3. Litigation Agent: `get_litigation_view` → `write_audit_event` with a JSON event (`event_type`, `claim_id`, `next_step`, …).
4. Orchestrator reports results to the user.

## Restart note

Restart `iceberg-mcp-server-claims` after pulling main so new MCP tool names appear (`get_*_view`, `write_audit_event`, `promote_audit_run`).
