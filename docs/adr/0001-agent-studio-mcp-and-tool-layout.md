# ADR 0001: MCP forks, Agent Studio tool layout, and shared Python package

**Status:** Accepted  
**Date:** 2026-08-03  
**Deciders:** Semantic / agent team (with Platform / MCP for forks)

## Context

We are deploying a minimal claim-routing agent in Cloudera AI Agent Studio:

- RDF / SPARQL / playbook logic in Python tools
- Platform I/O only via MCP (Iceberg, Atlas/data-contract, Ranger)
- Ontology, probes, and playbook as Git-reviewed config (not Iceberg UI catalogs)

Temporary bridge code exists today (Iceberg SQL/branch fallbacks, vendored tool bundles, optional direct Hive/`impyla` in the build tool). That was to unblock offline tests and a demo before MCP forks landed. Studio custom tools effectively ship as **`tool.py` + `requirements.txt` only**; other support files belong in the Studio project’s **`workflow_data`** tree.

**Confirmed:** Agent Studio installs packages listed in a tool’s `requirements.txt` (including a shared library). Shared Python should not be vendored into tool folders or stuffed into `workflow_data`.

## Decisions

### D1 — Build MCP forks; eliminate placeholder I/O

Fork and register (additive tools only):

| MCP | Upstream | Phase 1 additions |
|---|---|---|
| `iceberg-mcp-server-hive-claims` | [frothkoetter/iceberg-mcp-server-hive](https://github.com/frothkoetter/iceberg-mcp-server-hive) | `get_claim_spine`, `get_claim_routing_signals`, audit begin/append/promote/abandon |
| `data-contract-mcp-server-claims` | [frothkoetter/data-contract-mcp-server](https://github.com/frothkoetter/data-contract-mcp-server) | BM typedef/get/set + `bind_ontology_iri_to_entity` |

Do **not** fork Ranger. Do **not** dual-register `ecole5/atlas-mcp` beside the data-contract fork.

After forks are contract-tested on seeded CDP data, **remove** from this repo:

- Iceberg facade SQL/branch composition fallbacks
- Studio tool direct Hive/`impyla` callers
- `prepare_bundles.sh` / vendored `ins_claims_agent` / in-tool `runtime_assets`

Facades remain as thin wrappers over real MCP tool names.

Details and ownership: [`docs/mcp-fork-charter.md`](../mcp-fork-charter.md).

### D2 — Tool layout: thin `tool.py` + `requirements.txt`

Each Agent Studio custom tool directory contains only:

- `tool.py` — `UserParameters`, `ToolParameters`, `run_tool`, `OUTPUT_KEY`, CLI entrypoint
- `requirements.txt` — runtime deps, including the shared package

No ontology/probes/playbook and no copied library trees inside the tool folder.

### D3 — Shared Python via `requirements.txt`

Publish/pin **`ins-claims-agent`** (git URL or internal index) from this repo’s `agent_studio` package.

Tools depend on it for graph build, validate, route, and (later) audit helpers. Tools call MCP through facades/adapters after Studio binds the MCP invoker (or equivalent host wiring).

### D4 — Config in `workflow_data` via `WORKFLOW_DATA_DIRECTORY`

**Confirmed (Agent Studio):** During workflow execution, tools read static files from the workflow data directory using:

```python
workflow_data_dir = os.environ.get("WORKFLOW_DATA_DIRECTORY", "/workflow_data")
```

Contract:

| Rule | Detail |
|---|---|
| Env var | `WORKFLOW_DATA_DIRECTORY` (default mount `/workflow_data`) |
| Access | **Read-only** inside the tool sandbox |
| Scope | Available to **all tools** in the workflow during execution |
| Use for | Static reference files (ontology, probes, playbook) |
| Do not use for | Dynamic / per-run outputs — use the **artifact / session directory** |

### D4b — Artifacts via `SESSION_DIRECTORY` (`/workspace`)

**Confirmed (Agent Studio):** Per-run outputs use the artifact file directory:

| Aspect | Artifact (session) directory | Workflow data directory |
|---|---|---|
| Purpose | Tool outputs, artifacts, temp files | Project files / input config |
| Mount | `/workspace` | `/workflow_data` |
| Access | Read-write | Read-only |
| Env var | `SESSION_DIRECTORY` | `WORKFLOW_DATA_DIRECTORY` |
| Working directory | Yes (cwd auto-configured) | No |
| UI visibility | Yes (outputs visible) | No |

Cross-tool sharing: all tools in the workflow see the same session artifact directory during execution (build writes `claim_{id}_graph.ttl`; validate/route read it).

Studio project layout:

```text
workflow_data/                    # RO config (WORKFLOW_DATA_DIRECTORY)
  ontology/claims_mvt.ttl
  probes/*.rq
  playbook/playbook.yaml

/workspace (SESSION_DIRECTORY)    # RW run artifacts (cwd)
  claim_{id}_graph.ttl
  claim_{id}_validation.json
  claim_{id}_route.json
```

Path resolution in shared code / tools:

- Config: `os.environ.get("WORKFLOW_DATA_DIRECTORY", "/workflow_data")`
- Artifacts: `os.environ.get("SESSION_DIRECTORY", os.getcwd())` (prefer env; cwd is `/workspace`)
- Replace ad hoc `INS_CLAIMS_REPO_ROOT` / vendored `runtime_assets` for Studio runs

### D5 — Single-route demo tool set (unchanged intent)

1. `build_claim_graph` — MCP spine/signals → **`SESSION_DIRECTORY`** graph artifact  
2. `validate_claim_graph` — read graph from session dir; ontology from `workflow_data` if needed  
3. `route_claim` — probes + playbook from `workflow_data`; write decision JSON to session dir  

Agent calls them in order; LLM does not invent SQL.

## Consequences

**Positive**

- One I/O path (fork MCP tools); no dual SQL/Hive implementations to maintain  
- Tools stay upload-small and Studio-native  
- Shared logic versioned once via the package  
- Config changes stay PR-reviewable without republishing Python for every probe tweak  
- Clear RO config vs RW run-state split matches Studio security model  

**Negative / costs**

- Platform must deliver and operate two forks (rebase cadence to upstream)  
- Demo is blocked on Iceberg P0 spine/signals until forks are live  
- Local unit tests must emulate both env vars (`WORKFLOW_DATA_DIRECTORY` + `SESSION_DIRECTORY`)

**Migration**

1. Run Studio spikes S1–S2 below (blockers for tool cutover)  
2. Implement and contract-test Iceberg fork P0 (spine + signals first; audit next)  
3. Point Studio tools at `ins-claims-agent` + `WORKFLOW_DATA_DIRECTORY` / `SESSION_DIRECTORY`  
4. Delete fallbacks and bundle machinery  
5. Add Atlas BM fork when governance binding is in scope  

## Open Studio questions

**Resolved**

1. ~~`workflow_data` path~~ — `WORKFLOW_DATA_DIRECTORY` → `/workflow_data`, RO, all tools  
2. ~~Artifact / cross-tool RW sharing~~ — `SESSION_DIRECTORY` → `/workspace`, RW, cwd, UI-visible; shared across tools in the run  
3. ~~Static vs dynamic~~ — config → workflow data; outputs → session/artifact directory  

**Must spike in Studio before cutover**

### S1 — MCP callable from `tool.py`

**Question:** Can a custom tool invoke a registered MCP tool in-process, or only the agent?

**Spike MCP (existing Impala Iceberg server)**

- Tools: `execute_query`, `get_schema`
- Workflow env: `IMPALA_HOST`, `IMPALA_PORT`, `IMPALA_USER`, `IMPALA_PASSWORD`, `IMPALA_DATABASE`
- Stub: `agent_studio/studio_tools/spikes/s1_mcp_from_tool/`

**Spike workflow**

1. Register that MCP on the workflow with `IMPALA_*` vars.  
2. Run the spike tool; default call is `execute_query` / `SHOW DATABASES` (or `get_schema`).  
3. Record *how* the call is made (Studio bridge, SDK, env gateway, unavailable, etc.).

| Result | Implication |
|---|---|
| Tool can call MCP | Keep facade-in-package design; `build_claim_graph` uses Iceberg fork from tool |
| Agent-only | Design break for thin tools — need Studio MCP bridge, or unacceptable agent-written SQL |

**Pass criteria:** Tool returns MCP result JSON without the LLM inventing SQL; failure mode documented if unsupported.

### S2 — Git install via `requirements.txt`

**Question:** Can a tool install `ins-claims-agent` from git (or only wheel/PyPI/internal index)?

**Spike workflow**

1. Minimal tool `requirements.txt` with e.g.  
   `ins-claims-agent @ git+https://<org>/<repo>.git@<ref>#subdirectory=agent_studio`  
   (adjust to real publish layout), **or** a tiny public git package first if private git is blocked.  
2. `run_tool` imports a symbol from that package and returns its version/`__file__`.  
3. If git fails, retry with a built wheel on an allowed index.

| Result | Implication |
|---|---|
| `git+https` works | Pin package from this repo; no vendoring |
| Wheel/index only | Add CI publish of `ins-claims-agent` wheel; tools pin version |
| Neither | Blocker — escalate to Studio platform |

**Pass criteria:** `import ins_claims_agent` succeeds inside the tool sandbox; document the exact `requirements.txt` line that worked.

## References

- [`docs/mcp-fork-charter.md`](../mcp-fork-charter.md)  
- Agent Studio: Accessing Files in Tools (`WORKFLOW_DATA_DIRECTORY`, `SESSION_DIRECTORY`)  
- Agent Studio custom tools: `tool.py` + `requirements.txt` pattern  
- Package: `agent_studio/` (`ins-claims-agent`)  
