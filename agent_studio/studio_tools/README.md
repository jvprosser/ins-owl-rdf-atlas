# Agent Studio tools — single-route demo

Three custom tools following the Agent Studio `UserParameters` / `ToolParameters` / `run_tool` pattern.

| Tool | Purpose | Needs Hive? |
|---|---|---|
| `build_claim_graph/` | Load spine+signals from Hive, write `claim_{id}_graph.ttl` | Yes |
| `validate_claim_graph/` | SPARQL integrity checks on the graph artifact | No |
| `route_claim/` | SPARQL probes + playbook → next step | No |

## Agent prompt (suggested)

Given `claim_id`, call tools in order: **build → validate → route**. Return `next_step`, `lane`, `agent_role`, `reason_probe_ids`. Do not invent SQL.

## User parameters (build)

| Field | Example |
|---|---|
| `hive_host` | HS2 / Knox host |
| `hive_user` / `hive_password` | LDAP creds |
| `hive_port` | `443` |
| `claims_database` | `car_insurance_claims` |

Validate/route only need optional `assets_root` (usually leave empty).

## Local CLI test (same as Agent Studio)

```bash
# Offline: synthesize a graph, then validate + route
cd /tmp/claim_demo_ws
python <<'PY'
from pathlib import Path
import sys
sys.path[:0] = [
  "…/agent_studio/src",
  "…/agent_studio/studio_tools",
]
import os
os.environ["INS_CLAIMS_REPO_ROOT"] = "…/agent_studio/studio_tools/runtime_assets"
from ins_claims_agent.graph.build_claim_graph import build_claim_graph
spine = {
  "claim_id": 401, "claim_number": "CLM-2025-000401", "claim_status_code": "OPEN",
  "litigation_indicator": False, "subrogation_indicator": True,
  "fraudulent_claim_indicator": False, "total_loss_indicator": False,
  "loss_event_id": 301, "loss_cause_code": "COLLISION",
  "policy_id": 1001, "policy_number": "PA-1001",
  "insurable_object_id": 201, "vin": "VIN", "policy_covers_vehicle": True,
  "policy_coverage_id": 3001, "coverage_type_code": "COLLISION",
  "claim_lifecycle_id": 7001,
  "roles": [{"claim_party_role_id": 6002, "role_type_code": "ADJUSTER", "party_id": 4}],
}
signals = {"has_subrogation_case": False, "has_police_report": True, "has_fault_determination": True}
g = build_claim_graph(401, spine=spine, signals=signals)
g.serialize("claim_401_graph.ttl", format="turtle")
PY

python …/validate_claim_graph/tool.py --user-params '{}' --tool-params '{"claim_id":"401"}'
python …/route_claim/tool.py --user-params '{}' --tool-params '{"claim_id":"401"}'
```

## Bundle for Agent Studio upload

```bash
cd agent_studio/studio_tools
./prepare_bundles.sh
```

Then register each of `build_claim_graph/`, `validate_claim_graph/`, `route_claim/` as a custom tool (entrypoint `tool.py`).
