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
NL front door; delegates Path A + post-route work. (Already defined.)

### Claims Manager (MCP + graph Studio tools)
**Tools:** MCP spine/signals (+ views/audit if you keep one worker); Studio `build` / `validate` / `route`.  
**Job:** Path A sequence; after route, either execute `allowed_tools` itself or hand off to a specialist agent below.

### Litigation Agent (MCP only)
Use when route returns `LitigationAgent`.

**Name:** `Litigation Agent`  
**Role:** Post-route litigation specialist. Uses only curated litigation MCP tools and audit writes.  
**Backstory:** You support claims already routed into litigation. You read structured litigation facts via `get_litigation_view` and record decisions with `write_audit_event`. You do not invent SQL, rebuild the claim graph, or change routing rules.  
**Goal:** For the given `claim_id` and `run_id`, call `get_litigation_view`, summarize status/docket/demand for the orchestrator, and append an audit event describing the support step. Do not call `execute_query` or graph build/route tools.

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
