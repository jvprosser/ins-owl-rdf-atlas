# ins-claims-agent (Agent Studio tool package)

Phase 1 scaffold for Style B claim routing:

- **Python tools** build an in-memory RDF graph, run SPARQL probes, validate, and dispatch steps
- **Git files** hold ontology, probes, and playbook (no custom steward UI)
- **MCP facades** call only:
  - Iceberg Hive MCP (facts + WAP audit branches)
  - Data-contract Atlas MCP (catalog/contracts/tags; BM bind when fork lands)
  - Ranger MCP (access/masking/audit logs)

RDF/SPARQL is **not** an MCP — it runs in-process via `rdflib`.

## Layout

```text
agent_studio/
  src/ins_claims_agent/
    mcp_facade/       # thin wrappers over the three MCPs
    graph/            # build / sparql / validate / route
    specialists/      # domain worker tools
    audit/            # WAP audit orchestration
  ../ontology/        # TBox turtle
  ../probes/          # SPARQL probe files
  ../playbook/        # step → agent → tools
  workflows/          # Style B loop notes
```

## Install (local)

```bash
cd agent_studio
pip install -e ".[dev]"
pytest
```

## Agent Studio wiring (conceptual)

1. Register MCPs: Iceberg fork, data-contract Atlas fork, Ranger upstream.
2. Expose Python entrypoints as custom tools:
   - `build_claim_graph`
   - `route_claim`
   - `validate_claim_graph`
   - `write_audit_event` / `promote_audit_run`
   - specialist tools (`get_subrogation_view`, …)
3. Bind MCP: `bind_mcp_caller(caller)` or `bind_agent_studio_mcp(call_tool)`.
4. Workflow loop: `run_style_b_loop(...)` → Route → Worker → Refresh → Route … until terminal.

Iceberg facades prefer fork P0 tools (`get_claim_spine`, audit helpers) and fall back to
`execute_query` + Iceberg branch DML when those tools are missing.

See `workflows/style_b_route_loop.md` and `../docs/mcp-fork-charter.md`.
