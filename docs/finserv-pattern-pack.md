# Finserv pattern packs

Reuse the claims **control plane** for retirement operations. Do not clone the MCP server per product.

Control-plane architecture (Iceberg, session case JSON, playbook, Studio): [`architecture.md`](architecture.md).

**Parked 2026-08-14.** Full status, Studio blocker, and resume plan: [`finserv-pattern-pack-status.md`](finserv-pattern-pack-status.md).

## What stays the same

- Orchestrator has no tools; the user cannot skip it.
- Manager runs catalog reads, then Studio `build_claim_graph` → `validate_claim_graph` → `route_claim`.
- After route, Manager stops. Orchestrator maps `agent_role` → coworker Role and Delegates once.
- YAML probes + Git-reviewed playbook are authoritative. Cosine is NL triage only.
- Platform I/O is MCP `run_named_query` / `run_named_write`. Custom tools do not call MCP in-process.

## What a pack replaces

A pack is a directory with `pack.yaml` (and `catalog_fixtures.json` for MCP). File-by-file legend: [`packs/README.md`](../packs/README.md#what-each-directory-and-file-is-for).

- Schema JSON (`ontology/`, `pack.yaml`)
- Playbook with inlined YAML probes (`playbook/`)
- Fixture JSON for named reads (`fixtures/`, `catalog_fixtures.json`) — canned lake payloads, not routing rules
- Cosine `exemplars.yaml`
- Agent Studio pastes (`agents/`)

Studio tool names stay `build_claim_graph` / `validate_claim_graph` / `route_claim` and still take `claim_id`.

## Demo packs

See [`packs/README.md`](../packs/README.md). Agent Studio workflow + test steps per pack: [`mcp_forks/iceberg-mcp-server-claims/README.md`](../mcp_forks/iceberg-mcp-server-claims/README.md).

- **Distributions** — classification and exceptions (hardship substantiation, RMD, hold/AML).
- **Rollovers** — ERISA / document completeness (spousal consent).

Car-insurance claim **402** remains on repo-root `ontology/` + `playbook/`. Do not move those trees.

## Runtime env

| Variable | Role |
|---|---|
| `PACK_ROOT` | MCP server **Environment variables** only (Studio **MCP → iceberg-mcp-server-claims**). Path on the MCP host to the pack dir with `catalog_fixtures.json`. |
| `WORKFLOW_DATA_DIRECTORY` | Set by Studio from **Workflow Data** (`/workflow_data`). Not where you type `PACK_ROOT`. |
| `INS_CLAIMS_REPO_ROOT` | Set automatically by `configure_workflow_assets` |

Unset `PACK_ROOT` for the live claims lake catalog (Impala).
