"""Unit tests for create_litigation_task named write (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import litigation_tasks


def test_insert_litigation_task_sql():
    sql = litigation_tasks.insert_litigation_task_sql(
        "car_insurance_claims",
        {
            "litigation_task_id": 1,
            "litigation_case_id": 9101,
            "claim_id": 402,
            "task_type_code": "ESCALATE_DISCOVERY",
            "task_status_code": "OPEN",
            "due_date": None,
            "run_id": "demo-402-e2e",
        },
    )
    assert "INSERT INTO car_insurance_claims.litigation_task" in sql
    assert "ESCALATE_DISCOVERY" in sql
    assert "9101" in sql
    assert "402" in sql


def test_create_litigation_task_ok(monkeypatch):
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    monkeypatch.setattr(
        "iceberg_mcp_server_claims.tools.impala_tools.execute_dml",
        fake_dml,
    )
    raw = litigation_tasks.create_litigation_task(
        "demo-402-e2e",
        json.dumps(
            {
                "claim_id": "402",
                "task_type_code": "ESCALATE_DISCOVERY",
                "litigation_case_id": 9101,
            }
        ),
        "car_insurance_claims",
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["task_type_code"] == "ESCALATE_DISCOVERY"
    assert payload["claim_id"] == 402
    assert payload["table"] == "litigation_task"
    assert "INSERT INTO car_insurance_claims.litigation_task" in captured[0]


def test_create_litigation_task_rejects_bad_type():
    raw = litigation_tasks.create_litigation_task(
        "demo-402-e2e",
        json.dumps({"claim_id": "402", "task_type_code": "INVENT"}),
    )
    payload = json.loads(raw)
    assert "error" in payload
    assert "task_type_code" in payload["error"]


def test_create_litigation_task_requires_claim_id():
    raw = litigation_tasks.create_litigation_task(
        "demo-402-e2e",
        json.dumps({"task_type_code": "COMPLETE_FILE"}),
    )
    assert "claim_id" in json.loads(raw)["error"]
