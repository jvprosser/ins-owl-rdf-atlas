# ins-claims-agent (Agent Studio tool package)

Structured claim intake for Agent Studio:

- **Manager agent** — NL interface: drives tools, explains results, assigns unstructured LLM subtasks (ADR 0001 D0)
- **Python tools** — deterministic build / validate / route (YAML probes + playbook)
- **Git files** hold schema JSON and playbook (no custom steward UI)
- **MCP** — Iceberg claims fork; later Atlas data-contract + Ranger

Routing is in-process Python over case JSON. The manager agent is **not** the router.

## Layout

```text
agent_studio/
  src/ins_claims_agent/
    mcp_facade/       # thin wrappers over Iceberg (Atlas/Ranger stubs)
    graph/            # build / yaml probes / validate / route
  studio_tools/       # thin tool.py + requirements.txt + agents configured in Agent Studio
  ../ontology/        # case schema JSON
  ../playbook/        # step → agent → tools
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
2. `build_claim_graph` — spine/signals JSON → `SESSION_DIRECTORY/claim_{id}_case.json`
3. `validate_claim_graph` / `route_claim` — case artifact + `WORKFLOW_DATA_DIRECTORY` playbook
4. `pre_route_text` — unstructured NL cosine triage (litigation vs claims); LLM only if `needs_llm`

See [`studio_tools/README.md`](studio_tools/README.md) and [`../docs/mcp-fork-charter.md`](../docs/mcp-fork-charter.md).
