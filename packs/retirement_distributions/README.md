# Retirement distributions (finserv demo)

Classification and exception handling for plan distributions. Deterministic probes — not an LLM policy engine.

| Case | Story | Route |
|---|---|---|
| **7001** | Termination, documents complete | `ProcessDistribution` / `DistributionOpsAgent` |
| **7002** | Hardship, substantiation missing | `RequestSubstantiation` / `ExceptionQueueAgent` |
| **7003** | RMD underpaid | `RmdReview` / `RmdOpsAgent` |

## Agent Studio workflow + tests

Full Cloudera Agent Studio setup (MCP `PACK_ROOT`, crew, e2e prompts): [`mcp_forks/iceberg-mcp-server-claims/README.md`](../../mcp_forks/iceberg-mcp-server-claims/README.md#pack-retirement_distributions).

## Upload workflow data (Studio)

Studio mounts this tree as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`. Upload the **contents** of `packs/retirement_distributions/`, not the folder name. After upload, `/workflow_data/pack.yaml` must exist (not `/workflow_data/retirement_distributions/pack.yaml`).

Do this in the **distributions** Agent Studio project (not the claims 402 project).

1. Open the project → open **Workflow Data** (the project file tree for this workflow).
2. If this project previously held claims files (`ontology/claims_mvt.ttl`, claims `playbook/`, claims `probes/`), delete those first so the pack is the only tree.
3. At the **root** of Workflow Data, upload these two files from `packs/retirement_distributions/`:
   - `pack.yaml`
   - `exemplars.yaml`
4. Create folder `ontology` (or upload that directory). Inside it, upload:
   - `ontology/distributions.ttl`
5. Create folder `playbook` (or upload that directory). Inside it, upload:
   - `playbook/playbook.yaml`
6. Create folder `probes` (or upload that directory). Inside it, upload all five:
   - `probes/R0_1_request_exists.rq`
   - `probes/R1_1_request_status.rq`
   - `probes/R2_1_hold_or_aml.rq`
   - `probes/R2_2_hardship_substantiation_missing.rq`
   - `probes/R2_3_rmd_underpaid.rq`
7. Confirm the tree looks like this:

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/distributions.ttl
  playbook/playbook.yaml
  probes/R0_1_request_exists.rq
  probes/R1_1_request_status.rq
  probes/R2_1_hold_or_aml.rq
  probes/R2_2_hardship_substantiation_missing.rq
  probes/R2_3_rmd_underpaid.rq
```

**Do not** upload to Workflow Data: `agents/` (paste those into agent Name/Role/Backstory/Goal), `fixtures/`, `catalog_fixtures.json`, or `README.md`. Those last two are for MCP `PACK_ROOT` only.

If Studio offers “upload folder”, select `ontology`, `playbook`, and `probes` individually. Do not upload the parent `retirement_distributions` folder as a single nest.

## Where to set `PACK_ROOT`

**Only on the MCP server.** In Cloudera Agent Studio that is the **Environment variables** list on the `iceberg-mcp-server-claims` registration — the same place claims uses `IMPALA_HOST`. It is not Workflow Data, not an agent Goal, and not a custom-tool parameter.

| Place | Set `PACK_ROOT`? |
|---|---|
| Studio **MCP** → this server → **Environment variables** | **Yes** |
| Workflow Data (`/workflow_data`) | No — that is `WORKFLOW_DATA_DIRECTORY` for graph/playbook only |
| Agent Name / Role / Backstory / Goal | No |
| Custom tool `UserParameters` | No |

Steps:

1. Open the **distributions** Agent Studio project.
2. Open **MCP** (sometimes **Tools → MCP servers**). Do not open Workflow Data.
3. Select **`iceberg-mcp-server-claims`** (the V7 server with `get_server_info` / `run_named_query`).
4. Under **Environment variables**, add one row:
   - **Name:** `PACK_ROOT`
   - **Value:** absolute path **on the machine that runs MCP** to the pack directory that contains `catalog_fixtures.json` and `fixtures/`. Example if that host has this repo cloned:

```text
/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_distributions
```

5. Save. Restart or reconnect the MCP server (catalog merge runs at process start).
6. Check: Delegate Manager to call `list_named_queries`. The reads list must include `get_distribution_spine`. If you only see `get_claim_spine`, `PACK_ROOT` is unset, the path is wrong, or MCP was not restarted.

`uvx` from git does **not** include `packs/`. Clone or copy `packs/retirement_distributions` onto the MCP host, then point `PACK_ROOT` at that copy. Impala variables are optional for this fixture demo.

Do **not** set `PACK_ROOT` on the claims 402 MCP.

`run_named_query` labels: `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`. Writes are fixture stubs (`write_audit_event`, `promote_audit_run`).

## Studio prompt (lead with 7002)

Paste Orchestrator / Manager / Exception Queue from `agents/`. Then chat Orchestrator:

```text
Intake and route claim_id 7002, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager (Role "Manager agent").
   Task: structured intake for 7002 —
   run_named_query label get_distribution_spine, then get_distribution_routing_signals,
   then build, validate, route. STOP after route_claim.

2) Delegate ONCE to Exception Queue Agent.
   Task: claim_id=7002 run_id=demo-7002-exc.
   run_named_query label get_distribution_exception_view, then run_named_write write_audit_event.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

Expect `next_step=RequestSubstantiation`, `lane=EXCEPTION`, probe **R2.2**.
