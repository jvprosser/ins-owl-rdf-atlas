"""Quote write computes premium from the lake snapshot."""

from __future__ import annotations

import json

from iceberg_mcp_server_underwriting.tools import uw_writes
from iceberg_mcp_server_underwriting.tools.uw_writes import PROBE_CEL

_P3 = "P3_STRAIGHT_THROUGH_BIND"


def _snapshot_row():
    return {
        "submission_id": "SUB-9103",
        "line_of_business": "COMMERCIAL_PROPERTY",
        "class_code": "5411",
        "total_insured_value": 1999999,
        "submission_status_code": "OPEN",
        "is_in_flood_plain": False,
        "inspection_completed": False,
        "flood_zone": "NONE",
        "prior_claims_count": 0,
        "has_open_loss_past_36m": False,
        "financial_stability_tier": "B",
    }


def _event(**extra):
    body = {
        "claim_id": "SUB-9103",
        "playbook_version": "1.0.0",
        "probe_id": _P3,
        "cel": PROBE_CEL[_P3],
    }
    body.update(extra)
    return json.dumps(body)


def test_quote_rejects_caller_premium():
    calls: list[str] = []
    raw = uw_writes.write_quote_issuance(
        "demo-SUB-9103-e2e",
        _event(premium_cents=1, rating_tier="Z"),
        execute_dml=lambda sql: calls.append(sql) or "Query executed successfully.",
        query_rows=lambda sql: [_snapshot_row()],
    )
    payload = json.loads(raw)
    assert "computed by the catalog" in payload["error"]
    assert calls == []


def test_quote_computes_premium_from_snapshot():
    calls: list[str] = []
    raw = uw_writes.write_quote_issuance(
        "demo-SUB-9103-e2e",
        _event(),
        execute_dml=lambda sql: calls.append(sql) or "Query executed successfully.",
        query_rows=lambda sql: [_snapshot_row()],
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["rating_tier"] == "B"
    assert payload["premium_cents"] == 499999
    assert payload["table"] == "quote_issuance"
    assert payload["audit_table"] == "agent_run_audit"
    assert len(calls) == 2
    assert "499999" in calls[0]
    assert "1.0.0" in calls[1]
    assert PROBE_CEL[_P3] in calls[1]
    assert "1999999" in calls[1]


def test_decline_rejects_invented_reason():
    raw = uw_writes.write_submission_decline(
        "demo-SUB-9100-e2e",
        json.dumps(
            {
                "claim_id": "SUB-9100",
                "reason_code": "TOO_RISKY",
                "playbook_version": "1.0.0",
                "probe_id": "P0_OUT_OF_APPETITE",
                "cel": PROBE_CEL["P0_OUT_OF_APPETITE"],
            }
        ),
        execute_dml=lambda sql: "Query executed successfully.",
        query_rows=lambda sql: [_snapshot_row()],
    )
    payload = json.loads(raw)
    assert payload["error"] == "reason_code must be OUT_OF_APPETITE"


def test_enrichment_rejects_other_provider():
    raw = uw_writes.write_data_enrichment_request(
        "demo-SUB-9101-e2e",
        json.dumps(
            {
                "claim_id": "SUB-9101",
                "provider_type": "CREDIT",
                "playbook_version": "1.0.0",
                "probe_id": "P1_AWAITING_INSPECTION",
                "cel": PROBE_CEL["P1_AWAITING_INSPECTION"],
            }
        ),
        execute_dml=lambda sql: "Query executed successfully.",
        query_rows=lambda sql: [_snapshot_row()],
    )
    payload = json.loads(raw)
    assert payload["error"] == "provider_type must be INSPECTION"
