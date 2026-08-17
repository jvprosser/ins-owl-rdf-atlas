# iceberg-mcp-server-claims

Claims fork of Cloudera’s Impala Iceberg MCP for the car-insurance claims agent.

**V7 MCP surface is catalog-only.** Agents call `run_named_query` / `run_named_write` with an allow-listed label. Per-label tools and free-form `execute_query` are not registered. SQL still lives in Python handlers behind the catalog.

| Aspect | Detail |
|---|---|
| Upstream base | [cloudera/iceberg-mcp-server](https://github.com/cloudera/iceberg-mcp-server) (Impala / `impyla`) |
| Location | This repo: `mcp_forks/iceberg-mcp-server-claims/` |
| Transport | stdio (Agent Studio `uvx` / MCP registration) |
| Python | `>=3.10` |

## Tools

### Identity

| Tool | Notes |
|---|---|
| `get_server_info()` | One-shot identity. Expect **`INS_CLAIMS_MCP_V7`** / **`0.3.3`**. Prompt: “Call get_server_info once and stop.” |

### Named catalog (only lake I/O)

Studio Action Input is **flat**. Prefer top-level `claim_id` / `run_id` over nested `params_json`. No free-form SQL.

| Tool | Notes |
|---|---|
| `list_named_queries()` | Catalog of read/write labels + required params |
| `run_named_query(label, claim_id?, database?, params_json?)` | Curated **reads**. Example: `{"label":"get_litigation_view","claim_id":"402"}` |
| `run_named_write(label, run_id?, event_json?, …)` | Curated **writes**. Example: `{"label":"write_audit_event","run_id":"demo-402","event_json":"{...}"}` |

Read labels: `get_claim_spine`, `get_claim_routing_signals`, `get_litigation_view`, `get_bi_view`, `get_subrogation_view`, `get_schema`.

Write labels: `write_audit_event`, `append_agent_audit_event`, `append_agent_audit_evidence`, `begin_agent_audit_run`, `promote_audit_run`, `promote_agent_audit_run`, `abandon_agent_audit_run`.

Impala audit writes are table-append (no Iceberg WAP branch). `promote_audit_run` returns `mode=table_append`. Prerequisite: audit DDL from `ddl/hive_iceberg/` in the target database.

## Agent Studio registration

Replace the stock `iceberg-mcp-server` registration with this fork (same `IMPALA_*` env). Example:

```json
{
  "mcpServers": {
      "iceberg-mcp-server-claims": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git#subdirectory=mcp_forks/iceberg-mcp-server-claims",
  
        "run-server"
      ],
      "env": {
        "IMPALA_HOST": "<coordinator-host>",
        "IMPALA_PORT": "443",
        "IMPALA_USER": "<user>",
        "IMPALA_PASSWORD": "<password>",
        "IMPALA_DATABASE": "car_insurance_claims"
      }
    }
  }
}
```

Local editable / path install for sandbox:

```bash
cd mcp_forks/iceberg-mcp-server-claims
uv sync
# or: pip install -e .
uv run run-server
```

**stdio:** do not print to stdout; this server logs to stderr only.

## Structured claim intake flow

```text
Agent
  → MCP run_named_query label get_claim_spine
  → MCP run_named_query label get_claim_routing_signals
  → custom tool (build / validate / YAML route from payload + workflow_data)
  → MCP run_named_write label write_audit_event (optional)
```

Custom tools do not call MCP in-process. The agent must invoke MCP tools, then pass results into Python tools.

## Pack fixtures (finserv demo)

When `PACK_ROOT` (or `INS_CLAIMS_REPO_ROOT`) points at a directory with `catalog_fixtures.json`, those read labels are merged into the catalog and served from JSON files. `fixture_writes: true` stubs `write_audit_event` / `promote_audit_run` (no Impala). Unset `PACK_ROOT` for the live claims lake (claim **402**). See `packs/` and `docs/finserv-pattern-pack.md`.

**One pack = one Agent Studio workflow.** Do not put a finserv pack in the same project as claims 402. Do not set `PACK_ROOT` on the claims MCP. Restart MCP after changing `PACK_ROOT` (catalog merge runs at import).

Studio custom tools still take `claim_id`. Pack-aware graph/route code must be on the git pin in each tool `requirements.txt` (`ins_claims_agent/pack.py` + generic `build_case_graph`). The claims-only pin `87de0c5` will not load a pack.

`PACK_ROOT` is **only** an MCP server environment variable. Set it on the `iceberg-mcp-server-claims` registration in Agent Studio (**MCP → Environment variables**), same list as `IMPALA_HOST`. Do not put it in Workflow Data, an agent Goal, or a custom-tool parameter.

The value is an absolute path **on the host that runs `run-server`**, pointing at the pack directory that contains `catalog_fixtures.json`. `uvx` from git does not ship `packs/`; clone or copy that pack onto the MCP host first.

`WORKFLOW_DATA_DIRECTORY` is different: Studio sets it from the project **Workflow Data** tree (`/workflow_data`) for ontology/playbook/probes. That mount does not set `PACK_ROOT`.

---

### Shared: add a pack as a Cloudera Agent Studio workflow

Do this once per pack (new project, or a dedicated workflow in a new project).

1. **Workflow data** — Follow the per-pack **Upload workflow data** steps below (and in each `packs/<id>/README.md`). Upload pack *contents* so `/workflow_data/pack.yaml` exists. Do not nest `retirement_distributions/` or `retirement_rollovers/` as an extra folder. `fixtures/` and `catalog_fixtures.json` stay on MCP `PACK_ROOT` only.
2. **Custom tools** — Register the same thin tools as claims, each folder’s `tool.py` + `requirements.txt` only:
   - `agent_studio/studio_tools/build_claim_graph`
   - `agent_studio/studio_tools/validate_claim_graph`
   - `agent_studio/studio_tools/route_claim`
   - `agent_studio/studio_tools/pre_route_text` (optional; unstructured cosine)
3. **MCP `PACK_ROOT`** — Open **MCP** (or **Tools → MCP servers**), edit `iceberg-mcp-server-claims`, add Environment variable `PACK_ROOT` = absolute pack path on the MCP host (see each pack below). Save and restart MCP. Impala vars are optional for fixture packs.
4. **Crew** — Same-crew requirement. Orchestrator has **no** tools (user cannot skip it). Manager Role must be exactly `Manager agent`. Paste agents from `packs/<id>/agents/`. CrewAI `Delegate` matches **Role**, not Name.
5. **Chat the Orchestrator** — Do not start on Manager. Use the pack test prompts below.

Manager tools: MCP + `build_claim_graph` + `validate_claim_graph` + `route_claim`.  
Specialists: MCP only.  
Routing Agent (optional): `pre_route_text` only; Role exactly `Routing Agent`.

---

### Pack: `retirement_distributions`

Repo path: `packs/retirement_distributions/`  
Agent pastes: `packs/retirement_distributions/agents/`  
Lead demo case: **7002** (hardship substantiation missing).

#### Where to set `PACK_ROOT`

In Agent Studio: **MCP → `iceberg-mcp-server-claims` → Environment variables**. Add `PACK_ROOT` (not Workflow Data). Value = directory that contains `pack.yaml` and `catalog_fixtures.json` on the MCP host. Restart MCP after save.

```json
{
  "mcpServers": {
    "iceberg-mcp-server-claims": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git#subdirectory=mcp_forks/iceberg-mcp-server-claims",
        "run-server"
      ],
      "env": {
        "PACK_ROOT": "/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_distributions"
      }
    }
  }
}
```

Local MCP on a clone:

```bash
export PACK_ROOT=/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_distributions
cd mcp_forks/iceberg-mcp-server-claims
uv run run-server
```

#### Upload workflow data (Studio)

Studio mounts this tree as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`. Use the **distributions** project. Upload contents of `packs/retirement_distributions/` so `/workflow_data/pack.yaml` exists (not `/workflow_data/retirement_distributions/pack.yaml`).

1. Open the project → **Workflow Data**.
2. Remove any leftover claims files (`ontology/claims.json` or `claims_mvt.ttl`, claims playbook).
3. Upload to the **root**: `pack.yaml`, `exemplars.yaml`.
4. Create or upload folder `ontology/`, then upload `ontology/distributions.json`.
5. Create or upload folder `playbook/`, then upload `playbook/playbook.yaml`.
6. Confirm:

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/distributions.json
  playbook/playbook.yaml
```

Do **not** upload `agents/`, `fixtures/`, `catalog_fixtures.json`, or `README.md`. If Studio can upload a folder, upload `ontology` and `playbook` separately — not the parent `retirement_distributions` folder.

#### Crew

| Agent | Role (exact coworker) | Tools | Paste |
|---|---|---|---|
| Orchestrator | (no Delegate target) | none | `agents/orchestrator_agent.md` |
| Manager | `Manager agent` | MCP + build / validate / route | `agents/manager_agent.md` |
| Exception Queue | `Exception Queue Agent` | MCP | `agents/exception_queue_agent.md` |
| Distribution Ops | `Distribution Ops Agent` | MCP | `agents/distribution_ops_agent.md` |
| RMD Ops | `RMD Ops Agent` | MCP | `agents/rmd_ops_agent.md` |
| Routing (optional) | `Routing Agent` | `pre_route_text` | `agent_studio/studio_tools/agents/routing_agent.md` |

Catalog labels (fixture): `get_distribution_spine`, `get_distribution_routing_signals`, `get_distribution_exception_view`, `get_rmd_view`. Writes: `write_audit_event`, `promote_audit_run` (stubs).

#### Test — offline (before Studio)

```bash
cd agent_studio && python -m pytest tests/test_packs.py -q
cd ../mcp_forks/iceberg-mcp-server-claims && uv run pytest tests/test_pack_fixtures.py -q
```

Expect 7002 → `RequestSubstantiation` / `ExceptionQueueAgent`; 7001 → `ProcessDistribution`; 7003 → `RmdReview`.

#### Test — MCP in Studio (Manager, one-shot)

Chat Orchestrator. Do not run intake.

```text
Do not make a multi-step Plan.
Delegate ONCE to Manager (Role "Manager agent").
Task: Call get_server_info once. Return the exact JSON. Stop.
```

Expect `content_id` = `INS_CLAIMS_MCP_V7`. Then:

```text
Delegate ONCE to Manager.
Task: Call list_named_queries once. Return the exact JSON. Stop.
```

Expect read labels `get_distribution_spine` and `get_distribution_routing_signals`. Then:

```text
Delegate ONCE to Manager.
Task: Call run_named_query once:
{"label":"get_distribution_spine","claim_id":"7002"}
Return the exact JSON. Stop.
```

Expect `fixture: true` and `distribution_type_code` = `HARDSHIP`.

#### Test — structured intake e2e (chat Orchestrator)

**7002 (lead):**

```text
Intake and route claim_id 7002, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager (Role "Manager agent").
   Task: structured intake for 7002 —
   run_named_query label get_distribution_spine, then get_distribution_routing_signals,
   then build_claim_graph (FULL spine_json + signals_json), validate_claim_graph, route_claim.
   STOP after route. Return next_step, lane, agent_role, reason_probe_ids.
   Do not call specialist views or write audit.

2) Delegate ONCE to Exception Queue Agent.
   Task: claim_id=7002 run_id=demo-7002-exc.
   run_named_query label get_distribution_exception_view, then run_named_write write_audit_event.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

| Check | Expect |
|---|---|
| `next_step` | `RequestSubstantiation` |
| `lane` | `EXCEPTION` |
| `agent_role` | `ExceptionQueueAgent` |
| `reason_probe_ids` | includes `R2.2` |
| write | `fixture: true`, `run_id` = `demo-7002-exc` |

**7001** — same prompt with `claim_id` 7001 / `run_id=demo-7001-ops`. Step 2: Distribution Ops Agent, write only (no view). Expect `ProcessDistribution` / `DistributionOpsAgent`.

**7003** — `claim_id` 7003 / `run_id=demo-7003-rmd`. Step 2: RMD Ops Agent, view `get_rmd_view` then write. Expect `RmdReview` / `RmdOpsAgent`.

#### Test — unstructured (optional)

```text
Do not run structured intake. There is no claim_id.
Delegate ONCE to Routing Agent.
Task: Call pre_route_text once with text:
"Hardship withdrawal is missing medical bills and the hardship attestation."
Return the exact tool JSON. Then Final Answer label, score, coworker, needs_llm.
```

Expect `label` = `EXCEPTION`, `coworker` = `Exception Queue Agent`, `needs_llm` = false.

---

### Pack: `retirement_rollovers`

Repo path: `packs/retirement_rollovers/`  
Agent pastes: `packs/retirement_rollovers/agents/`  
Lead demo case: **8001** (missing spousal consent).

#### Where to set `PACK_ROOT`

In Agent Studio: **MCP → `iceberg-mcp-server-claims` → Environment variables**. Add `PACK_ROOT` (not Workflow Data). Value = directory that contains `pack.yaml` and `catalog_fixtures.json` on the MCP host. Restart MCP after save.

```json
{
  "mcpServers": {
    "iceberg-mcp-server-claims": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/jvprosser/ins-owl-rdf-atlas.git#subdirectory=mcp_forks/iceberg-mcp-server-claims",
        "run-server"
      ],
      "env": {
        "PACK_ROOT": "/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_rollovers"
      }
    }
  }
}
```

```bash
export PACK_ROOT=/ABS/PATH/ins-owl-rdf-atlas/packs/retirement_rollovers
cd mcp_forks/iceberg-mcp-server-claims
uv run run-server
```

#### Upload workflow data (Studio)

Studio mounts this tree as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`. Use the **rollovers** project (not claims 402, not distributions). Upload contents of `packs/retirement_rollovers/` so `/workflow_data/pack.yaml` exists (not `/workflow_data/retirement_rollovers/pack.yaml`).

1. Open the project → **Workflow Data**.
2. Remove any leftover claims or distributions files.
3. Upload to the **root**: `pack.yaml`, `exemplars.yaml`.
4. Create or upload folder `ontology/`, then upload `ontology/rollovers.json`.
5. Create or upload folder `playbook/`, then upload `playbook/playbook.yaml`.
6. Confirm:

```text
/workflow_data/
  pack.yaml
  exemplars.yaml
  ontology/rollovers.json
  playbook/playbook.yaml
```

Do **not** upload `agents/`, `fixtures/`, `catalog_fixtures.json`, or `README.md`. If Studio can upload a folder, upload `ontology` and `playbook` separately — not the parent `retirement_rollovers` folder.

#### Crew

| Agent | Role (exact coworker) | Tools | Paste |
|---|---|---|---|
| Orchestrator | (no Delegate target) | none | `agents/orchestrator_agent.md` |
| Manager | `Manager agent` | MCP + build / validate / route | `agents/manager_agent.md` |
| ERISA Review | `ERISA Review Agent` | MCP | `agents/erisa_review_agent.md` |
| Rollover Ops | `Rollover Ops Agent` | MCP | `agents/rollover_ops_agent.md` |
| Routing (optional) | `Routing Agent` | `pre_route_text` | `agent_studio/studio_tools/agents/routing_agent.md` |

Catalog labels (fixture): `get_rollover_spine`, `get_rollover_routing_signals`, `get_erisa_review_view`. Writes: `write_audit_event`, `promote_audit_run` (stubs).

#### Test — offline

Same pytest commands as distributions (`tests/test_packs.py` covers 8001 / 8002). Expect 8001 → `ErisaReview` / `ErisaReviewAgent`; 8002 → `ProcessRollover` / `RolloverOpsAgent`.

#### Test — MCP in Studio (Manager, one-shot)

`get_server_info` as above. Then `list_named_queries` must include `get_rollover_spine`. Then:

```text
Delegate ONCE to Manager.
Task: Call run_named_query once:
{"label":"get_rollover_spine","claim_id":"8001"}
Return the exact JSON. Stop.
```

Expect `fixture: true` and `rollover_type_code` = `DIRECT_ROLLOVER`.

#### Test — structured intake e2e (chat Orchestrator)

**8001 (lead):**

```text
Intake and route claim_id 8001, then complete the post-route specialist work.

You have no MCP tools. Do not skip the Orchestrator.

1) Delegate ONCE to Manager (Role "Manager agent").
   Task: structured intake for 8001 —
   run_named_query label get_rollover_spine, then get_rollover_routing_signals,
   then build_claim_graph (FULL spine_json + signals_json), validate_claim_graph, route_claim.
   STOP after route. Return next_step, lane, agent_role, reason_probe_ids.

2) Delegate ONCE to ERISA Review Agent.
   Task: claim_id=8001 run_id=demo-8001-erisa.
   run_named_query label get_erisa_review_view, then run_named_write write_audit_event.

3) Final Answer: route + specialist summary + exact write JSON. STOP.
```

| Check | Expect |
|---|---|
| `next_step` | `ErisaReview` |
| `lane` | `ERISA` |
| `agent_role` | `ErisaReviewAgent` |
| `reason_probe_ids` | includes `R2.1` |
| write | `fixture: true`, `run_id` = `demo-8001-erisa` |

**8002** — same prompt with `claim_id` 8002 / `run_id=demo-8002-ops`. Step 2: Rollover Ops Agent, write only. Expect `ProcessRollover` / `RolloverOpsAgent`.

#### Test — unstructured (optional)

```text
Do not run structured intake. There is no claim_id.
Delegate ONCE to Routing Agent.
Task: Call pre_route_text once with text:
"Direct rollover is missing spousal consent; QDRO not on file for the married participant."
Return the exact tool JSON. Then Final Answer label, score, coworker, needs_llm.
```

Expect `label` = `ERISA`, `coworker` = `ERISA Review Agent`, `needs_llm` = false.

## Tests

```bash
cd mcp_forks/iceberg-mcp-server-claims
uv sync --extra dev
uv run pytest
```

## Sync notes

When rebasing from upstream Impala MCP:

1. Diff connection env vars. Do not re-register `execute_query` as an MCP tool.
2. Keep catalog handlers and `{columns, rows}` JSON shape internally.
3. Never add `print()` on the stdio path.
