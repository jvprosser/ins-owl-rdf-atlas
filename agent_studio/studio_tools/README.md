# Agent Studio tools — Path A single-route demo

Thin tools: **`tool.py` + `requirements.txt` only**. Lake I/O is agent → MCP; Python builds/routes the graph.

| Tool | Input | Output (`SESSION_DIRECTORY`) |
|---|---|---|
| `build_claim_graph/` | `claim_id` + MCP `spine_json` / `signals_json` | `claim_{id}_graph.ttl` |
| `validate_claim_graph/` | `claim_id` | `claim_{id}_validation.json` |
| `route_claim/` | `claim_id` | `claim_{id}_route.json` |

S1: tools cannot call MCP. S2: `ins-claims-agent` installs from git.

## Agent prompt (suggested)

```text
For claim_id (e.g. 401):
1) Call MCP get_claim_spine(claim_id) on iceberg-mcp-server-claims.
2) Call MCP get_claim_routing_signals(claim_id).
3) Call build_claim_graph with claim_id, spine_json=<spine result>, signals_json=<signals result>.
4) Call validate_claim_graph(claim_id).
5) Call route_claim(claim_id).
Return next_step, lane, agent_role, reason_probe_ids.
Do NOT invent SQL or call execute_query for claim joins.
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
