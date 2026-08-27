# Finserv demo packs

Same control plane as car-insurance claims: Orchestrator (no tools) → Manager MCP catalog reads → Studio `build_claim_graph` → `validate_claim_graph` → `route_claim` → one specialist Delegate. CEL probes + playbook decide the lane. The LLM does not decide hardship, RMD, or ERISA.

Do **not** move `ontology/` / `playbook/` at the repo root. Claim **402** still uses those assets.

| Pack | Demo | Cases |
|---|---|---|
| [`retirement_distributions/`](retirement_distributions/) | Request classification + exception handling | **7001** clean termination → Distribution Ops; **7002** hardship missing substantiation → Exception Queue; **7003** RMD underpaid → RMD Ops |
| [`retirement_rollovers/`](retirement_rollovers/) | Document processing / ERISA | **8001** missing spousal consent → ERISA Review; **8002** complete direct rollover → Rollover Ops |

## Studio setup (one pack at a time)

Upload steps for Workflow Data are in each pack README (**Upload workflow data**).

- **Distributions (live):** register [`iceberg-mcp-server-finserv`](../mcp_forks/iceberg-mcp-server-finserv/README.md). Impala database `retirement_distributions`. No `PACK_ROOT`.
- **Rollovers (fixtures):** still the claims MCP + `PACK_ROOT` path in [`iceberg-mcp-server-claims/README.md`](../mcp_forks/iceberg-mcp-server-claims/README.md).

Primary customer prompt: intake **7002**. Probe/action chat prompts (claims + both packs): [`docs/probe-action-tests.md`](../docs/probe-action-tests.md).

## What each directory and file is for

Both packs use the same layout. Paths below are relative to `packs/<id>/` (for example `packs/retirement_distributions/`).

```text
packs/<id>/
  README.md                 # This pack’s demo script and Studio upload steps
  pack.yaml                 # Pack identity + schema/playbook paths (Studio tools)
  exemplars.yaml            # Cosine NL triage texts + dispatch
  catalog_fixtures.json     # MCP label list → fixture folders (not for tools)
  ontology/                 # Case field schema JSON
  playbook/                 # Probe order, CEL, next_step, coworker / write
  fixtures/                 # Canned MCP JSON (stand-in for Impala)
  agents/                   # Name / Role / Backstory / Goal / Tools — configure in Agent Studio
```

| Path | Purpose | Who reads it |
|---|---|---|
| `README.md` | Cases, expected routes, Workflow Data upload, Studio prompts | Humans |
| `pack.yaml` | Pack `id`, paths to schema/playbook/exemplars, `graph.builder: generic`, JSON field lists, optional catalog notes | Studio tools (`load_pack` / `build_case_graph` / `route_claim`) via Workflow Data |
| `exemplars.yaml` | Unstructured phrases, `labels`, `dispatch` (coworker / `agent_role` / `next_step`) | Studio `pre_route_text` (Routing Agent). Advisory only; a `claim_id` still goes through structured intake |
| `catalog_fixtures.json` | MCP allow-list for this pack: each `run_named_query` **label**, required params, and `fixture_dir` | MCP only (when it can load pack fixtures). Not used by graph tools |
| `ontology/*.json` | Case field schema (JSON, not Turtle) | `build_claim_graph` / humans |
| `playbook/playbook.yaml` | Probe CEL `cel` + actions (`step`, `agent`, `coworker`, `write`, `lane`, tools) | `route_claim` |
| `fixtures/<label>/<id>.json` | Fake lake payload for that named query and case (spine, signals, exception/ERISA/RMD view) | MCP `run_named_query` if fixtures are loaded. Same JSON shape Manager would pass into `build_claim_graph` |
| `agents/*.md` | Paste-ready Studio agents (Orchestrator, Manager, specialists) | Humans → Agent Studio fields. Not uploaded to Workflow Data |

**Workflow Data (Studio tools)** needs: `pack.yaml`, `exemplars.yaml`, `ontology/`, `playbook/`.  
**Do not** upload `agents/` (paste those).  
**MCP:** distributions labels are compiled in `iceberg-mcp-server-finserv` (live Impala). `catalog_fixtures.json` + `fixtures/` remain golden JSON for offline tests. Rollovers still use claims MCP `PACK_ROOT` fixtures. See [`docs/finserv-pattern-pack-status.md`](../docs/finserv-pattern-pack-status.md).

### `pack.yaml` fields (short)

| Field | Meaning |
|---|---|
| `id` | Pack name (`retirement_distributions`, `retirement_rollovers`) |
| `case_id_param` | Still `claim_id` so Studio tools stay unchanged |
| `graph.builder` | `generic` → `build_case_graph`; claims 402 uses the triangle builder instead |
| `graph.case_class` | Label on the case JSON (`DistributionRequest`, `RolloverRequest`) |
| `graph.literals` / `booleans` | Spine/signal JSON keys copied onto the case document |
| `catalog` | Label notes. Distributions: live MCP `iceberg-mcp-server-finserv`. Fixture dirs remain golden for tests. |

### Fixture folders

Each subdirectory matches one catalog **label**. The filename is the case id.

**Distributions**

| Folder | Label | Role |
|---|---|---|
| `fixtures/get_distribution_spine/` | `get_distribution_spine` | Request status, type, plan, participant (like `get_claim_spine`) |
| `fixtures/get_distribution_routing_signals/` | `get_distribution_routing_signals` | Hold flag, hardship reason codes, RMD shortfall (like `get_claim_routing_signals`) |
| `fixtures/get_distribution_exception_view/` | `get_distribution_exception_view` | Post-route view for Exception Queue (**7002**) |
| `fixtures/get_rmd_view/` | `get_rmd_view` | Post-route view for RMD Ops (**7003**) |

**Rollovers**

| Folder | Label | Role |
|---|---|---|
| `fixtures/get_rollover_spine/` | `get_rollover_spine` | Rollover request spine |
| `fixtures/get_rollover_routing_signals/` | `get_rollover_routing_signals` | Spousal consent / missing-docs flags |
| `fixtures/get_erisa_review_view/` | `get_erisa_review_view` | Post-route view for ERISA Review (**8001**) |

Writes (`write_audit_event`, `promote_audit_run`) have no fixture files; when pack fixtures load, MCP stubs those as `{ "ok": true, "fixture": true }` (no Impala INSERT).
