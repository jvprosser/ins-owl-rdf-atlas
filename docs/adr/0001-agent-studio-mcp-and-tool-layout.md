# ADR 0001: MCP forks, Agent Studio tool layout, and shared Python package

**Status:** Accepted  
**Date:** 2026-08-03  
**Deciders:** Semantic / agent team (with Platform / MCP for forks)

## Context

We are deploying a minimal claim-routing stack in Cloudera AI Agent Studio:

- RDF / SPARQL / playbook logic in Python tools (deterministic automation)
- Platform I/O only via MCP (Iceberg, Atlas/data-contract, Ranger)
- Ontology, probes, and playbook as Git-reviewed config (not Iceberg UI catalogs)
- A **manager agent** as the natural-language interface — not as the business-rules engine

Temporary bridge code exists today (Iceberg SQL/branch fallbacks). Studio custom tools effectively ship as **`tool.py` + `requirements.txt` only**; other support files belong in the Studio project’s **`workflow_data`** tree.

**Confirmed:** Agent Studio installs packages listed in a tool’s `requirements.txt` (including a shared library). Shared Python should not be vendored into tool folders or stuffed into `workflow_data`.

## Decisions

### D0 — Manager agent is the NL interface (not the router)

The **manager agent** is the conversational control plane between the user and tools:

| Does | Does not |
|---|---|
| Interpret user intent and call MCP + custom tools in the structured claim intake / Style B sequence | Invent claim SQL, joins, or routing rules |
| Return user-friendly summaries of validate/route outcomes (`next_step`, `lane`, `reason_probe_ids`, …) | Replace SPARQL probes or `playbook.yaml` |
| Assign / invoke LLM-friendly subtasks that touch **unstructured** data (notes, documents, free text) when the playbook or user asks | Free-form lake exploration via `execute_query` for claim spine |

**Split of responsibility**

```text
User (natural language)
  └─ Manager agent          → NL I/O, explanations, unstructured task dispatch
       ├─ MCP (structured)  → get_claim_spine / get_claim_routing_signals / audit…
       ├─ Custom tools      → build / validate / route (deterministic)
       └─ LLM subtasks      → only for unstructured extraction / language work
```

Routing and graph integrity remain **business automation** (tools + Git-reviewed probes/playbook). The agent layer is justified for NL ops and unstructured side-quests on the same Studio surface — not because the router must be agentic.

### D1 — Build MCP forks; eliminate placeholder I/O

Fork and register (additive tools only):

| MCP | Upstream | Phase 1 additions |
|---|---|---|
| `iceberg-mcp-server-claims` (**in-repo**) | [cloudera/iceberg-mcp-server](https://github.com/cloudera/iceberg-mcp-server) (Impala) | `get_claim_spine`, `get_claim_routing_signals`, audit begin/append/promote/abandon (`table_append` mode) — see `mcp_forks/iceberg-mcp-server-claims/` |
| `iceberg-mcp-server-hive-claims` (optional later) | [frothkoetter/iceberg-mcp-server-hive](https://github.com/frothkoetter/iceberg-mcp-server-hive) | Same claim helpers + true WAP branches |
| `data-contract-mcp-server-claims` | [frothkoetter/data-contract-mcp-server](https://github.com/frothkoetter/data-contract-mcp-server) | BM typedef/get/set + `bind_ontology_iri_to_entity` (deferred) |

Do **not** fork Ranger. Do **not** dual-register `ecole5/atlas-mcp` beside the data-contract fork.

**Structured claim intake:** Manager agent → MCP claim helpers → custom tool with payload. Register the Impala claims fork in Studio in place of stock `iceberg-mcp-server`. Custom tools do not call MCP in-process.

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

Publish/pin **`ins-claims-agent`** from this repo’s `agent_studio` package via git:

```text
ins-claims-agent @ git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=agent_studio
```

Tools depend on it for graph build, validate, route, and (later) audit helpers.

**MCP note:** custom tools cannot call registered MCP in-process. Facades-in-tool assume a bridge that does not exist; use agent→MCP then tool, or Impala/`impyla` inside the tool.

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

Manager agent calls MCP then these tools in order; explains results to the user; may assign unstructured LLM subtasks afterward. It does not invent SQL or routing.

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

1. ~~MCP-from-tool spike~~ done — no in-process MCP; **structured claim intake** (agent → MCP → tool payload)  
2. ~~Iceberg Impala claims fork scaffolded~~ — `mcp_forks/iceberg-mcp-server-claims/`  
3. ~~Studio structured-intake smoke~~ — claims `401`/`402`/`403` build → validate → route OK  
4. ~~Git install via requirements.txt~~ done — Studio installs `ins-claims-agent` from `git+https` + `#subdirectory=agent_studio`  
5. Prefer MCP P0 spine/signals/views (not free-form `execute_query`) in agent prompts  
6. ~~Intake demo tools~~ — thin `build`/`validate`/`route` + git pin; config via `WORKFLOW_DATA_DIRECTORY`  
7. ~~Post-route MCP~~ — playbook views + audit aliases on claims fork; see `studio_tools/POST_ROUTE_AGENTS.md`  
8. Wire Style B loop + unstructured worker when ready  
9. Delete fallbacks and legacy `prepare_bundles` trees once structured intake is live in CDP  
10. Add Atlas BM fork when governance binding is in scope — plan: [`docs/atlas-ranger-integration-plan.md`](../atlas-ranger-integration-plan.md)

## Open Studio questions

**Resolved**

1. ~~`workflow_data` path~~ — `WORKFLOW_DATA_DIRECTORY` → `/workflow_data`, RO, all tools  
2. ~~Artifact / cross-tool RW sharing~~ — `SESSION_DIRECTORY` → `/workspace`, RW, cwd, UI-visible; shared across tools in the run  
3. ~~Static vs dynamic~~ — config → workflow data; outputs → session/artifact directory  

**Studio spikes**

### Closed spike — MCP callable from `tool.py` (FAIL)

**Question:** Can a custom tool invoke a registered MCP tool in-process?

**Result (2026-08-03):** Custom tool ran (`tool_fingerprint: INS_CLAIMS_S1_TOOL_PY_V3`) but **no in-process bridge**:

- Failed probes: `globals_bridge`, `env_http_gateway`, `studio_sdk_import`, `mcp_sdk_stdio_opt_in`
- Artifact: `/workspace/spike_s1_mcp_from_tool.json`
- Stub: `agent_studio/studio_tools/spikes/s1_mcp_from_tool/`

**Implication:** Agent Studio exposes Iceberg MCP to the **agent** (e.g. via MCP tools / `call-mcp`), **not** to custom `tool.py`. The preferred path `agent → custom tool → MCP` is **not available** without a platform bridge.

**I/O for claim tools (locked)**

| Option | Pattern | Notes |
|---|---|---|
| Structured claim intake (default) | Agent calls MCP (`get_claim_spine` / `get_claim_routing_signals`), then custom tool with payload | Fork at `mcp_forks/iceberg-mcp-server-claims/`; avoid free-form SQL |
| Direct Impala | Custom tool talks to Impala/Hive via `UserParameters` + driver (`impyla`) | Bypasses MCP for reads; duplicates connection config |
| Future bridge | Platform adds MCP-from-tool later | Revisit facade-in-tool design if/when Studio ships it |

Do **not** design `build_claim_graph` assuming in-process MCP from `tool.py`.

### Git install via `requirements.txt` — RESOLVED (PASS)

**Question:** Can a tool install `ins-claims-agent` from git (or only wheel/PyPI/internal index)?

**Result (2026-08-04):** Studio installed from git and imported successfully.

| Field | Value |
|---|---|
| Fingerprint | `INS_CLAIMS_S2_TOOL_PY_V1` |
| Version | `0.1.0` |
| Installed from git | `true` |
| URL | `https://github.com/jvprosser/ins-owl-rdf-atlas.git` |
| Commit | `8018ae30ed4997b545403add36339e4a33bda49d` |
| Revision | `main` |
| Subdirectory | `agent_studio` |
| Artifact | `/workspace/spike_s2_git_requirements.json` |
| Stub | `agent_studio/studio_tools/spikes/s2_git_requirements/` |

**Working `requirements.txt` line**

```text
ins-claims-agent @ git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=agent_studio
```

**Implication:** No vendoring / wheel publish required for Phase 1. Real Studio tools should pin `ins-claims-agent` this way (prefer a commit SHA over `@main` for demos that need reproducibility).

## References

- [`docs/mcp-fork-charter.md`](../mcp-fork-charter.md)  
- Agent Studio: Accessing Files in Tools (`WORKFLOW_DATA_DIRECTORY`, `SESSION_DIRECTORY`)  
- Agent Studio custom tools: `tool.py` + `requirements.txt` pattern  
- Package: `agent_studio/` (`ins-claims-agent`)  
