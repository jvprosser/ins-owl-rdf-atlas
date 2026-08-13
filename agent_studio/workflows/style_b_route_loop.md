# Style B route loop (Agent Studio)

## Roles

| Role | Responsibility |
|---|---|
| **Manager agent** | NL interface to the user; calls MCP + tools; explains outcomes; assigns LLM subtasks for **unstructured** data |
| **Deterministic tools** | Spine/signals → build → validate → route (SPARQL probes + playbook) |
| **Worker / LLM tasks** | Only when `needs_llm` or manager dispatches unstructured extraction |

The manager agent is **not** the router. Probes and `playbook.yaml` own next-step decisions.

## Loop

```text
# Manager (or host workflow) drives:
begin_audit_run(run_id)
MCP get_claim_spine / get_claim_routing_signals
build_claim_graph(claim_id, spine_json, signals_json)
validate_claim_graph(claim_id)          # optional hard gate
loop until terminal or max_route_passes:
    decision = route_claim(claim_id)
    write_audit_event(run_id, decision)
    manager explains decision to user (optional)
    if decision.terminal:
        break
    if decision.needs_llm or unstructured evidence required:
        manager assigns LLM / worker task (bounded tools + prompt)
    else:
        run worker for decision.agent_role with decision.allowed_tools
    write_audit_evidence(...)
    refresh build_claim_graph(claim_id)   # avoid stale routing
promote_audit_run(run_id) or abandon_audit_run(run_id)
```

## Stop conditions (from playbook)

- `terminal: true` on matched action (e.g. `CloseoutAudit`, `HumanReviewOrWait`)
- `loop.max_route_passes`
- same `next_step` repeated `loop.no_progress_limit` times

Implemented by `ins_claims_agent.workflow.run_style_b_loop` (promotes audit on terminal when WAP/table-append helpers are wired; abandons otherwise).

## MCP servers registered

1. Iceberg claims MCP (`iceberg-mcp-server-claims` — Impala fork)
2. Data-contract Atlas MCP (fork with BM bind when ready)
3. Ranger MCP (upstream)
