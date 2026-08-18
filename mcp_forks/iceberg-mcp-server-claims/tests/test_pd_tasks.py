"""Unit tests for create_pd_task named write (no Impala)."""

from __future__ import annotations

import json

from iceberg_mcp_server_claims.tools import pd_tasks


def test_insert_pd_task_sql():
    sql = pd_tasks.insert_pd_task_sql(
        "car_insurance_claims",
        {
            "pd_task_id": 1,
            "claim_id": 401,
            "loss_event_id": 301,
            "task_type_code": "REQUEST_POLICE_REPORT",
            "task_status_code": "OPEN",
            "due_date": None,
            "run_id": "demo-401-pd",
        },
    )
    assert "INSERT INTO car_insurance_claims.pd_task" in sql
    assert "REQUEST_POLICE_REPORT" in sql
    assert "401" in sql
    assert "301" in sql


def test_create_pd_task_ok(monkeypatch):
    captured: list[str] = []

    def fake_dml(sql: str):
        captured.append(sql)
        return "OK"

    monkeypatch.setattr(
        "iceberg_mcp_server_claims.tools.impala_tools.execute_dml",
        fake_dml,
    )
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps(
            {
                "claim_id": "401",
                "task_type_code": "DETERMINE_FAULT",
                "loss_event_id": 301,
            }
        ),
        "car_insurance_claims",
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["task_type_code"] == "DETERMINE_FAULT"
    assert payload["claim_id"] == 401
    assert payload["table"] == "pd_task"
    assert "INSERT INTO car_insurance_claims.pd_task" in captured[0]


def test_create_pd_task_rejects_bad_type():
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"claim_id": "401", "task_type_code": "INVENT"}),
    )
    payload = json.loads(raw)
    assert "error" in payload
    assert "task_type_code" in payload["error"]


def test_create_pd_task_requires_claim_id():
    raw = pd_tasks.create_pd_task(
        "demo-401-pd",
        json.dumps({"task_type_code": "PD_REVIEW"}),
    )
    assert "claim_id" in json.loads(raw)["error"]
