# Finserv pattern packs

Reuse the claims **control plane** for retirement operations. Same Orchestrator → Manager → YAML route → specialist flow. Studio tools stay `build_claim_graph` / `claim_id`.

**Locked (2026-08-18):** live distributions demo uses a **separate** MCP, `iceberg-mcp-server-finserv`, with a compiled catalog for **distributions only**. Claims MCP stays claims-only (**402** unchanged). Rollovers stay parked on fixtures until distributions is proven on Impala.

Control-plane architecture: [`architecture.md`](architecture.md). Resume / status: [`finserv-pattern-pack-status.md`](finserv-pattern-pack-status.md).

## What stays the same

- Orchestrator has no tools; the user cannot skip it.
- Manager runs catalog reads, then Studio `build_claim_graph` → `validate_claim_graph` → `route_claim`.
- After route, Manager stops. Orchestrator Delegates once to Observation `coworker` (playbook YAML). If `coworker` is omitted, Final Answer the route JSON.
- CEL probes + Git-reviewed playbook are authoritative. Cosine is NL triage only.
- Platform I/O is MCP `run_named_query` / `run_named_write`. Custom tools do not call MCP in-process.

## What a pack replaces

A pack is a directory with `pack.yaml` (and `catalog_fixtures.json` for MCP). File-by-file legend: [`packs/README.md`](../packs/README.md#what-each-directory-and-file-is-for).

- Schema JSON (`ontology/`, `pack.yaml`)
- YAML playbook with CEL probes (`playbook/`)
- Fixture JSON for named reads (`fixtures/`, `catalog_fixtures.json`) — canned lake payloads, not routing rules
- Cosine `exemplars.yaml`
- Agents to configure in Agent Studio (`agents/`)

Studio tool names stay `build_claim_graph` / `validate_claim_graph` / `route_claim` and still take `claim_id`.

## Demo packs

See [`packs/README.md`](../packs/README.md). Live distributions MCP: [`mcp_forks/iceberg-mcp-server-finserv/README.md`](../mcp_forks/iceberg-mcp-server-finserv/README.md). Rollover fixture steps remain in [`mcp_forks/iceberg-mcp-server-claims/README.md`](../mcp_forks/iceberg-mcp-server-claims/README.md).

- **Distributions** — classification and exceptions (hardship substantiation, RMD, hold/AML).
- **Rollovers** — ERISA / document completeness (spousal consent).

Car-insurance claim **402** remains on repo-root `ontology/` + `playbook/`. Do not move those trees.

## Runtime env

| Variable | Role |
|---|---|
| Claims MCP `IMPALA_*` | Live `car_insurance_claims` catalog. Do **not** set `PACK_ROOT` on this server. |
| Finserv MCP `IMPALA_*` | Live distributions catalog (`iceberg-mcp-server-finserv`). Distributions labels only. |
| `WORKFLOW_DATA_DIRECTORY` | Set by Studio from **Workflow Data** (`/workflow_data`). Pack ontology / playbook / `pack.yaml`. |
| `INS_CLAIMS_REPO_ROOT` | Set automatically by `configure_workflow_assets` |

Rollovers may still use `PACK_ROOT` fixtures until that pack is promoted. Do not load rollover labels into the finserv MCP.
