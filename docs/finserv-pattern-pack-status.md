# Finserv pattern-pack — status

**Parked:** 2026-08-14 (fixture / `PACK_ROOT` path)  
**Locked 2026-08-18:** full distributions demo = Impala DDL/seed + **`iceberg-mcp-server-finserv`** with a compiled catalog for **distributions only**.  
**Do not** move repo-root `ontology/` / `playbook/`. Claim **402** stays on that tree and on `iceberg-mcp-server-claims`.

## Why this exists

Reuse the car-insurance **control plane** for a finserv customer demo:

1. **Retirement distributions** — request classification and exception handling (lead case **7002**). **DDL + compiled MCP in repo.** Studio e2e on Impala is next.
2. **Retirement rollovers** — document / ERISA completeness (lead case **8001**). **Still parked** (fixtures). Not on the finserv MCP.

Same locked flow as claims: Orchestrator (no tools) → Manager catalog reads → Studio `build_claim_graph` → `validate_claim_graph` → `route_claim` → one specialist Delegate. YAML probes + playbook decide the lane. The LLM does not decide hardship, RMD, or ERISA.

Studio tools still take `claim_id`.

## What is done in the repo

Offline tests were green when parked (`agent_studio` 35 passed; MCP catalog/fixture tests 13 passed via `uv run pytest`).

### Runtime (pack-aware, claims default unchanged)

| Piece | Location | Behavior |
|---|---|---|
| Pack loader | `agent_studio/src/ins_claims_agent/pack.py` | `pack.yaml` → schema JSON, playbook, graph field lists |
| Path discovery | `agent_studio/src/ins_claims_agent/paths.py` | `PACK_ROOT` / `INS_CLAIMS_REPO_ROOT` / `WORKFLOW_DATA_DIRECTORY`, else walk-up to **legacy** `ontology/claims.json` + `playbook/` |
| Generic graph | `agent_studio/src/ins_claims_agent/graph/build_case_graph.py` | Used when `pack.graph.builder == "generic"` |
| Claims graph | `build_claim_graph.py` | Still used when no pack / builder ≠ generic (triangle / 402) |
| Validate | `validate_graph.py` | Generic packs: `case_exists`; claims: triangle |
| Route | `route_claim.py` | YAML `match` / `path` on case JSON |
| Cosine | `pre_router/route_text.py` | Pack `exemplars.yaml` `labels` + `dispatch`; claims exemplars unchanged if no pack env |
| Studio I/O | `studio_io.configure_workflow_assets` | Accepts pack.yaml **or** legacy claims tree |
| Build tool | `studio_tools/build_claim_graph/tool.py` | Generic vs claims builder |

Claims is **not** a pack. It becomes one only when you need two live products in one Studio/MCP install and 402 has been proven from a pointer pack. Sequence if/when: `packs/auto_pc_claims/pack.yaml` pointing at current trees → e2e 402 → then move files.

### Demo packs

`packs/retirement_distributions/` and `packs/retirement_rollovers/`.

Each has: `pack.yaml`, schema JSON (`ontology/*.json`), YAML playbook with inlined path probes, `exemplars.yaml`, `catalog_fixtures.json`, `fixtures/**/*.json`, agent pastes, README. Turtle TBox + `probes/*.rq` live only on branch/tag `rdf-sparql-runtime`.

| Case | Expected route |
|---|---|
| **7001** | `ProcessDistribution` / `DistributionOpsAgent` |
| **7002** | `RequestSubstantiation` / `ExceptionQueueAgent` (R2.2) |
| **7003** | `RmdReview` / `RmdOpsAgent` |
| **8001** | `ErisaReview` / `ErisaReviewAgent` (R2.1) |
| **8002** | `ProcessRollover` / `RolloverOpsAgent` |

Agent Roles: Orchestrator is `Distributions Orchestrator` / `Rollovers Orchestrator`. Manager Role stays exactly `Manager agent`. Specialists: `Exception Queue Agent`, `Distribution Ops Agent`, `RMD Ops Agent`, `ERISA Review Agent`, `Rollover Ops Agent`. Orchestrator tools: MCP NONE, Studio NONE. Manager: V7 MCP + build/validate/route. Specialists: V7 MCP, Studio NONE.

Studio Workflow Data (tools only): upload pack **contents** so `/workflow_data/pack.yaml` exists. Do not nest `retirement_*` as an extra folder. Do not upload `agents/` (paste into Studio fields). `fixtures/` + `catalog_fixtures.json` were intended for MCP, not tools.

### MCP fixture merge (written, not usable in Studio as designed)

`mcp_forks/iceberg-mcp-server-claims/src/iceberg_mcp_server_claims/pack_fixtures.py` merges labels from `catalog_fixtures.json` when `PACK_ROOT` or `INS_CLAIMS_REPO_ROOT` points at a pack directory. `fixture_writes: true` stubs `write_audit_event` / `promote_audit_run` (no Impala). Merge runs at catalog import. `case_id` ↔ `claim_id` aliases are allowed so claims tests still pass.

Claims catalog itself is **compiled into the MCP package** (`catalog.py` `READ_OPS` / `WRITE_OPS`). V7 tools: `get_server_info`, `list_named_queries`, `run_named_query`, `run_named_write`. Agents learn labels from **Goal text** and/or `list_named_queries`. There is no per-label MCP tool.

Do **not** bump to V8 unless the surface changes. Do **not** register per-label MCP tools.

## What blocked the Studio demo

MCP runs as `uvx` stdio from the **workflow engine**, not inside the tool sandbox.

1. **No host checkout for `PACK_ROOT`.** The MCP machine cannot be given a git clone path. `uvx` `#subdirectory=mcp_forks/iceberg-mcp-server-claims` does not ship `packs/`.
2. **Workflow Data is for tools only.** Cloudera [tool execution](https://docs.cloudera.com/machine-learning/cloud/use-ai-studios/topics/ml-tool-execution.html) mounts `/workflow_data` + `WORKFLOW_DATA_DIRECTORY` in the **tool** sandbox. Agent Studio source (`CAI_STUDIO_AGENT` `studio/workflow_engine/src/engine/crewai/mcp.py`) starts MCP with `os.environ.copy()` plus the MCP registration `env` block. That source has **no** `WORKFLOW_DATA_DIRECTORY`.
3. **Live probe (2026-08-14):** `list_named_queries` returned **only claims labels** (`get_claim_spine` … `get_schema`). No `get_distribution_spine`. Pack merge did not run. Treat Workflow Data as **not** a delivery path for MCP fixtures. Do not add an “install pack” Studio tool that writes to `/workflow_data` for MCP — MCP cannot read that mount.

`PACK_ROOT` belongs only on **MCP → iceberg-mcp-server-claims → Environment variables** (same list as `IMPALA_HOST`). It is not Workflow Data, not an agent Goal, not a tool parameter. That assignment is useless here without a path the MCP process can read.

## Landed 2026-08-18 (distributions live catalog)

**Not** `PACK_ID` fixture bake-in. **Not** rollover labels on this server.

- Clone: `mcp_forks/iceberg-mcp-server-finserv` (`INS_FINSERV_MCP_V1`).
- Compiled `READ_OPS` / `WRITE_OPS`: `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`, `get_schema`, live `write_audit_event` / `promote_audit_run`.
- `list_named_queries` does not list `get_claim_spine` or `get_rollover_*`.
- Impala DDL + seed: `ddl/hive_iceberg/retirement_distributions_iceberg.sql` and `retirement_distributions_seed_data.sql` (**7001** / **7002** / **7003**). Fixture JSON remains golden for offline `test_packs.py`.
- Separate Agent Studio project. Register the finserv MCP only. `IMPALA_*` on that server; no `PACK_ROOT`.
- Still no per-label MCP tools. Still no LLM as the hardship/RMD decision.
- Workflow Data remains ontology / playbook / `pack.yaml` / `exemplars.yaml`.

**Still to do:** apply DDL/seed on the lake; register finserv MCP in a distributions Studio project; prove e2e **7002**. Pin `ins-claims-agent` to a SHA that includes the generic pack builder if the Studio project is still on an older pin.

Rollovers stay on the old fixture path until this e2e is proven. Do not add `get_rollover_*` to the finserv catalog.

Fallback (do not use): Manager reads spine from Workflow Data and skips `run_named_query`. That breaks parity with 402.

## Studio / MCP notes for resume

- One pack = one Agent Studio project. Do not mix with 402. Do not register the claims MCP in the distributions project.
- Manager Role exactly `Manager agent`. CrewAI Delegate matches **Role**.
- Custom tools: `build_claim_graph`, `validate_claim_graph`, `route_claim`, optional `pre_route_text`.
- Identity: claims `get_server_info` → `INS_CLAIMS_MCP_V7`. Finserv `get_server_info` → `INS_FINSERV_MCP_V1`.
- Lead customer prompt: intake **7002**.

## Tests to re-run on resume

```bash
cd agent_studio && python -m pytest -q
cd ../mcp_forks/iceberg-mcp-server-claims && uv run pytest -q
cd ../iceberg-mcp-server-finserv && uv sync --extra dev && uv run pytest -q
```

Pack route tests: `agent_studio/tests/test_packs.py`. Claims fixture merge (legacy): `mcp_forks/iceberg-mcp-server-claims/tests/test_pack_fixtures.py`. Finserv catalog: `mcp_forks/iceberg-mcp-server-finserv/tests/`.

## Related docs

- [`docs/finserv-pattern-pack.md`](finserv-pattern-pack.md) — pattern (short)
- [`docs/adr/0001-agent-studio-mcp-and-tool-layout.md`](adr/0001-agent-studio-mcp-and-tool-layout.md) — D0/D4; tools vs MCP
- [`mcp_forks/iceberg-mcp-server-finserv/README.md`](../mcp_forks/iceberg-mcp-server-finserv/README.md) — live distributions MCP
- [`mcp_forks/iceberg-mcp-server-claims/README.md`](../mcp_forks/iceberg-mcp-server-claims/README.md) — claims V7; rollover fixtures; distributions PACK_ROOT is legacy
- Claims agents: `agent_studio/studio_tools/agents/`
- Atlas/Ranger: parked separately in [`docs/atlas-ranger-integration-plan.md`](atlas-ranger-integration-plan.md) (`f5a5a2f`); not required for this demo
