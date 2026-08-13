# Agent Studio tools — Path A single-route demo

Thin tools: **`tool.py` + `requirements.txt` only**. Lake I/O is manager agent → MCP; Python builds/routes the graph.

### Paste / version check (required)

Every Studio `tool.py` and `requirements.txt` starts with version headers:

```text
CONTENT_ID: …
REPO_REF: …
UPDATED: YYYY-MM-DD
FILE: agent_studio/studio_tools/...
```

`requirements.txt` also has `# PACKAGE_PIN: …`. After paste, confirm those lines match the repo file. Tool results echo `tool_fingerprint` / `content_id` equal to `CONTENT_ID`. **Bump `CONTENT_ID` (and fingerprint) whenever the file contents change.**

**Manager agent (locked):** natural-language interface to the user — drives tools, returns friendly explanations, and may assign LLM subtasks for unstructured data. It does **not** invent SQL or routing rules (probes + playbook do).

| Tool | Input | Output (`SESSION_DIRECTORY`) |
|---|---|---|
| `build_claim_graph/` | `claim_id` + MCP `spine_json` / `signals_json` | `claim_{id}_graph.ttl` |
| `validate_claim_graph/` | `claim_id` | `claim_{id}_validation.json` |
| `route_claim/` | `claim_id` | `claim_{id}_route.json` |
| `pre_route_text/` | unstructured `text` (+ optional `claim_id`) | `pre_route_{id}.json` — cosine label/score; `needs_llm` if below threshold |

S1: tools cannot call MCP. S2: `ins-claims-agent` installs from git. See ADR 0001 **D0**.

**After route:** playbook `allowed_tools` map to MCP (views + audit aliases) — see [`POST_ROUTE_AGENTS.md`](POST_ROUTE_AGENTS.md).

**Unstructured NL (not Path A):** Studio `pre_route_text` + [`agents/routing_agent.md`](agents/routing_agent.md). Cosine is advisory when `claim_id` is set; Path A still wins.

## Manager agent prompt (suggested)

Paste into Studio **Role / Backstory / Goal**. Set **Role** to exactly `Manager agent` (CrewAI coworker matching uses the Role string).

```text
Role: Manager agent

Backstory: You coordinate car-insurance claim intake on Cloudera. Structured
facts come only from curated MCP helpers. Graph build/validate/route are
deterministic. You never invent SQL or routing rules. You never use
Delegate/coworker actions — you call tools yourself.

Goal:
1) If the user (or coworker) names a single MCP tool (e.g. get_litigation_view,
   get_server_info, write_audit_event): call that tool once with the given args,
   put the full tool JSON in Final Answer, and STOP. Do not run Path A.
2) Only when asked to intake/route a claim_id, run Path A in order:
   get_claim_spine → get_claim_routing_signals → build_claim_graph
   (pass FULL spine_json + signals_json unmodified) → validate_claim_graph
   → route_claim. Then explain next_step, lane, agent_role, reason_probe_ids.
3) Prefer curated MCP tools over execute_query. Never call validate/route
   before a successful build for that claim.
```

## Studio project setup

1. Register MCP `iceberg-mcp-server-claims` (see `mcp_forks/iceberg-mcp-server-claims/README.md`).
2. Put config under the project’s **workflow data** tree (mounted as `WORKFLOW_DATA_DIRECTORY` / `/workflow_data`):

```text
workflow_data/
  ontology/claims_mvt.ttl
  probes/*.rq
  playbook/playbook.yaml
```

Copy from this repo’s `ontology/`, `probes/`, `playbook/` (or `studio_tools/runtime_assets/`).

3. Register each tool by uploading **only** that folder’s `tool.py` + `requirements.txt` (no vendored trees).
4. **Push this repo to `main` before Studio runs** so the git pin resolves Path A package code (`studio_io`, etc.). Prefer pinning a commit SHA once stable.

## requirements.txt (each tool)

```text
pydantic>=2.0
ins-claims-agent @ git+https://github.com/jvprosser/ins-owl-rdf-atlas.git@main#subdirectory=agent_studio
```

## Local CLI smoke (no Studio)

```bash
cd /tmp/claim_demo_ws
export SESSION_DIRECTORY=/tmp/claim_demo_ws
export WORKFLOW_DATA_DIRECTORY=/path/to/ins-owl-rdf-atlas   # has ontology/ + playbook/
export PYTHONPATH=/path/to/ins-owl-rdf-atlas/agent_studio/src

python /path/to/.../build_claim_graph/tool.py --user-params '{}' --tool-params "$(python - <<'PY'
import json
spine = {
  "claim_id": 401, "database": "car_insurance_claims",
  "spine": {
    "claim_id": 401, "claim_number": "CLM-2025-000401", "claim_status_code": "OPEN",
    "litigation_indicator": False, "subrogation_indicator": True,
    "fraudulent_claim_indicator": False, "total_loss_indicator": False,
    "loss_event_id": 301, "loss_cause_code": "COLLISION",
    "policy_id": 1001, "policy_number": "PA-1001",
    "insurable_object_id": 201, "vin": "VIN", "policy_covers_vehicle": True,
    "policy_coverage_id": 3001, "coverage_type_code": "COLLISION",
    "claim_lifecycle_id": 7001,
  },
  "roles": [{"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4}],
}
signals = {
  "signals": {"has_subrogation_case": False, "has_police_report": True, "has_fault_determination": True},
  "injury_ids": [], "offers": [], "payment_ids": [], "recovery_ids": [],
}
print(json.dumps({"claim_id":"401","spine_json":json.dumps(spine),"signals_json":json.dumps(signals)}))
PY
)"

python /path/to/.../validate_claim_graph/tool.py --user-params '{}' --tool-params '{"claim_id":"401"}'
python /path/to/.../route_claim/tool.py --user-params '{}' --tool-params '{"claim_id":"401"}'
```

## Legacy

`prepare_bundles.sh` and vendored `ins_claims_agent/` / `runtime_assets/` under tool folders are **obsolete** for Path A (kept only as local reference). Do not upload them to Studio.
