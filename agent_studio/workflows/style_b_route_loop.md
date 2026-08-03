# Style B route loop (Agent Studio)

## Loop

```text
begin_audit_run(run_id)
build_claim_graph(claim_id)
validate_claim_graph(claim_id)          # optional hard gate
loop until terminal or max_route_passes:
    decision = route_claim(claim_id)
    write_audit_event(run_id, decision)
    if decision.terminal:
        break
    run worker agent for decision.agent_role
        with decision.allowed_tools only
        needs_llm = decision.needs_llm
    worker may call specialist tools
    write_audit_evidence(...)
    rebuild/refresh build_claim_graph(claim_id)   # avoid stale routing
promote_audit_run(run_id) or abandon_audit_run(run_id)
```

## Stop conditions (from playbook)

- `terminal: true` on matched action (e.g. `CloseoutAudit`, `HumanReviewOrWait`)
- `loop.max_route_passes`
- same `next_step` repeated `loop.no_progress_limit` times

Implemented by `ins_claims_agent.workflow.run_style_b_loop` (promotes audit branch on terminal; abandons otherwise).

## MCP servers registered

1. Iceberg Hive MCP (fork with P0 claim/audit helpers when ready)
2. Data-contract Atlas MCP (fork with BM bind when ready)
3. Ranger MCP (upstream)
