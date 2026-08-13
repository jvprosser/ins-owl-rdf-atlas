# ins-claims-agent (Agent Studio tool package)

Phase 1 scaffold for Style B claim routing:

- **Manager agent** — NL interface: drives tools, explains results, assigns unstructured LLM subtasks (ADR 0001 D0)
- **Python tools** — deterministic build / validate / route (SPARQL probes + playbook)
- **Git files** hold ontology, probes, and playbook (no custom steward UI)
- **MCP** — Iceberg claims fork; later Atlas data-contract + Ranger

RDF/SPARQL is **not** an MCP — it runs in-process via `rdflib`. The manager agent is **not** the router.

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

## Agent Studio structured claim intake tools

Thin tools in `studio_tools/` (`tool.py` + `requirements.txt` only; git-pin `ins-claims-agent`):

1. Agent calls MCP `get_claim_spine` / `get_claim_routing_signals`
2. `build_claim_graph` — spine/signals JSON → `SESSION_DIRECTORY/claim_{id}_graph.ttl`
3. `validate_claim_graph` / `route_claim` — graph artifact + `WORKFLOW_DATA_DIRECTORY` probes/playbook
4. `pre_route_text` — unstructured NL cosine triage (litigation vs claims); LLM only if `needs_llm`

See [`studio_tools/README.md`](studio_tools/README.md).

## Full Style B wiring (later)

1. Register MCPs: Iceberg fork, data-contract Atlas fork, Ranger upstream.
2. Bind MCP: `bind_mcp_caller(caller)` or `bind_agent_studio_mcp(call_tool)`.
3. Workflow loop: `run_style_b_loop(...)` → Route → Worker → Refresh → Route … until terminal.

See `workflows/style_b_route_loop.md` and `../docs/mcp-fork-charter.md`.
