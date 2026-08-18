# Retirement rollovers (finserv demo)

Thinner ERISA / document-processing pack. Same intake sequence as claims and distributions.

| Case | Story | Route |
|---|---|---|
| **8001** | Direct rollover, missing spousal consent | `ErisaReview` / `ErisaReviewAgent` |
| **8002** | Complete direct rollover | `ProcessRollover` / `RolloverOpsAgent` |

## Agent Studio workflow + tests

Full Cloudera Agent Studio setup (MCP `PACK_ROOT`, crew, e2e prompts): [`mcp_forks/iceberg-mcp-server-claims/README.md`](../../mcp_forks/iceberg-mcp-server-claims/README.md#pack-retirement_rollovers).

## Upload workflow data (Studio)

Studio mounts this tree as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`. Upload the **contents** of `packs/retirement_rollovers/`, not the folder name. After upload, `/workflow_data/pack.yaml` must exist (not `/workflow_data/retirement_rollovers/pack.yaml`).

Do this in the **rollovers** Agent Studio project (not the claims 402 project, and not the distributions project).

1. Open the project → open **Workflow Data** (the project file tree for this workflow).
2. If this project previously held claims or distributions files (`*.ttl`, `probes/*.rq`, leftover `pack.yaml`), delete those first so the pack is the only tree. Do not upload Turtle or SPARQL.
3. At the **root** of Workflow Data, upload these two files from `packs/retirement_rollovers/`:
   - `pack.yaml`
   - `exemplars.yaml`
4. Create folder `ontology` (or upload that directory). Inside it, upload:
   - `ontology/rollovers.json`
5. Create folder `playbook` (or upload that directory). Inside it, upload:
   - `playbook/playbook.yaml`
6. Confirm the tree looks like this:

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/rollovers.json
  playbook/playbook.yaml
```

That is the JSON+YAML runtime. Do **not** upload `ontology/*.ttl` or `probes/*.rq`.

**Do not** upload to Workflow Data: `agents/` (paste those into agent Name/Role/Backstory/Goal), `fixtures/`, `catalog_fixtures.json`, or `README.md`. Those last two are for MCP `PACK_ROOT` only.

If Studio offers “upload folder”, select `ontology` and `playbook` individually. Do not upload the parent `retirement_rollovers` folder as a single nest.

## Where to set `PACK_ROOT`

**Only on the MCP server.** In Cloudera Agent Studio that is the **Environment variables** list on the `iceberg-mcp-server-claims` registration — the same place claims uses `IMPALA_HOST`. It is not Workflow Data, not an agent Goal, and not a custom-tool parameter.

| Place | Set `PACK_ROOT`? |
|---|---|
| Studio **MCP** → this server → **Environment variables** | **Yes** |
| Workflow Data (`/workflow_data`) | No — that is `WORKFLOW_DATA_DIRECTORY` for graph/playbook only |
| Agent Name / Role / Backstory / Goal | No |
| Custom tool `UserParameters` | No |

Steps:

1. Open the **rollovers** Agent Studio project (not claims 402, not distributions).
2. Open **MCP** (sometimes **Tools → MCP servers**). Do not open Workflow Data.
3. Select **`iceberg-mcp-server-claims`** (the V7 server with `get_server_info` / `run_named_query`).
4. Under **Environment variables**, add one row:
   - **Name:** `PACK_ROOT`
   - **Value:** absolute path **on the machine that runs MCP** to the pack directory that contains `catalog_fixtures.json` and `fixtures/`. Example if that host has this repo cloned:

```text
/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_rollovers
```

5. Save. Restart or reconnect the MCP server (catalog merge runs at process start).
6. Check: Delegate Manager to call `list_named_queries`. The reads list must include `get_rollover_spine`. If you only see `get_claim_spine`, `PACK_ROOT` is unset, the path is wrong, or MCP was not restarted.

`uvx` from git does **not** include `packs/`. Clone or copy `packs/retirement_rollovers` onto the MCP host, then point `PACK_ROOT` at that copy. Impala variables are optional for this fixture demo.

Do **not** set `PACK_ROOT` on the claims 402 MCP.

Labels: `get_rollover_spine`, `get_rollover_routing_signals`, `get_erisa_review_view`.

## Studio prompt (lead with 8001)

```text
Intake and route claim_id 8001, then complete the post-route specialist work.

1) Delegate ONCE to Manager. Task: get_rollover_spine, get_rollover_routing_signals,
   build, validate, route. STOP after route_claim.

2) Delegate ONCE to ERISA Review Agent.
   Task: claim_id=8001 run_id=demo-8001-erisa.
   run_named_query label get_erisa_review_view, then run_named_write write_audit_event.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

Expect `next_step=ErisaReview`, `lane=ERISA`, probe **R2.1**.
