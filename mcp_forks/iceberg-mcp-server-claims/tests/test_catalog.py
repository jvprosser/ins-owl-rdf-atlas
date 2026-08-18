"""Named query/write catalog (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims import catalog


def test_unknown_read_label():
    payload = json.loads(catalog.run_named_query("invent_sql", "{}"))
    assert payload["error"] is True
    assert "get_litigation_view" in payload["known_labels"]


def test_write_label_rejected_on_query():
    payload = json.loads(catalog.run_named_query("write_audit_event", "{}"))
    assert payload["error"] is True
    assert "run_named_write" in payload["message"]


def test_missing_required_param():
    payload = json.loads(catalog.run_named_query("get_litigation_view", "{}"))
    assert payload["missing"] == ["claim_id"]


def test_bad_params_json():
    payload = json.loads(catalog.run_named_query("get_litigation_view", "not-json"))
    assert payload["error"] is True
    assert "JSON object" in payload["message"]


def test_extra_param_rejected():
    payload = json.loads(
        catalog.run_named_query(
            "get_litigation_view",
            json.dumps({"claim_id": "402", "select": "*"}),
        )
    )
    assert payload["extra"] == ["select"]


def test_read_dispatches_to_view(monkeypatch):
    monkeypatch.setattr(
        catalog.view_tools,
        "get_litigation_view",
        lambda claim_id, database=None: json.dumps(
            {"claim_id": int(claim_id), "litigation_cases": [{"litigation_case_id": 9101}]}
        ),
    )
    payload = json.loads(
        catalog.run_named_query("get_litigation_view", '{"claim_id":"402"}')
    )
    assert payload["named_op"] == "get_litigation_view"
    assert payload["named_op_kind"] == "read"
    assert payload["catalog_version"] == 1
    assert payload["litigation_cases"][0]["litigation_case_id"] == 9101


def test_flat_claim_id_without_params_json(monkeypatch):
    monkeypatch.setattr(
        catalog.view_tools,
        "get_litigation_view",
        lambda claim_id, database=None: json.dumps(
            {"claim_id": int(claim_id), "litigation_cases": [{"litigation_case_id": 9101}]}
        ),
    )
    payload = json.loads(catalog.run_named_query("get_litigation_view", claim_id="402"))
    assert payload["named_op"] == "get_litigation_view"
    assert payload["claim_id"] == 402


def test_write_dispatches(monkeypatch):
    monkeypatch.setattr(
        catalog.audit_tools,
        "append_agent_audit_event",
        lambda run_id, event_json, database=None: json.dumps(
            {"ok": True, "run_id": run_id, "table": "agent_run_audit"}
        ),
    )
    payload = json.loads(
        catalog.run_named_write(
            "write_audit_event",
            json.dumps(
                {
                    "run_id": "demo-402",
                    "event_json": {"event_type": "LitigationSupport", "claim_id": "402"},
                }
            ),
        )
    )
    assert payload["ok"] is True
    assert payload["named_op"] == "write_audit_event"
    assert payload["named_op_kind"] == "write"


def test_write_dispatches_litigation_task(monkeypatch):
    monkeypatch.setattr(
        catalog.litigation_tasks,
        "create_litigation_task",
        lambda run_id, event_json, database=None: json.dumps(
            {"ok": True, "run_id": run_id, "table": "litigation_task"}
        ),
    )
    payload = json.loads(
        catalog.run_named_write(
            "create_litigation_task",
            json.dumps(
                {
                    "run_id": "demo-402-e2e",
                    "event_json": {
                        "claim_id": "402",
                        "task_type_code": "ESCALATE_DISCOVERY",
                        "litigation_case_id": 9101,
                    },
                }
            ),
        )
    )
    assert payload["ok"] is True
    assert payload["named_op"] == "create_litigation_task"
    assert payload["named_op_kind"] == "write"
    listing = catalog.list_catalog()
    reads = {row["label"] for row in listing["reads"]}
    writes = {row["label"] for row in listing["writes"]}
    assert {"get_claim_spine", "get_litigation_view", "get_pd_view", "get_schema"} <= reads
    assert {"write_audit_event", "promote_audit_run", "create_litigation_task", "create_pd_task"} <= writes


def test_write_dispatches_pd_task(monkeypatch):
    monkeypatch.setattr(
        catalog.pd_tasks,
        "create_pd_task",
        lambda run_id, event_json, database=None: json.dumps(
            {"ok": True, "run_id": run_id, "table": "pd_task"}
        ),
    )
    payload = json.loads(
        catalog.run_named_write(
            "create_pd_task",
            json.dumps(
                {
                    "run_id": "demo-401-pd",
                    "event_json": {
                        "claim_id": "401",
                        "task_type_code": "PD_REVIEW",
                    },
                }
            ),
        )
    )
    assert payload["ok"] is True
    assert payload["named_op"] == "create_pd_task"
    assert payload["named_op_kind"] == "write"
